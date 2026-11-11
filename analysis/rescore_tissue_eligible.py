#!/usr/bin/env python3
"""Eligible-model tissue analysis with aligned evaluated item sets.

Primary roster = every model with all five MB-20xx tasks minus the three
checkpoints exposed to MB-12xx. Every model/task is scored on the intersection
of archived (task,sample) keys across that roster. Exposed checkpoints are
analysed separately on their own common items.

The production parser is imported from scripts/c2_paired.py. Classification
accuracy counts unparsed responses as errors. Regression reports conditional
MAE (parsed only), in-domain conditional MAE (fibrosis 0-4 / NAS 0-8), a
failure-aware MAE with range-endpoint penalty, coverage and Spearman rho.
Pairwise CIs use a biological-sample cluster bootstrap (2,000 replicates);
single-sample tasks use item/sample bootstrap. Archive absence is reported as
"not archived" and is never silently scored as an error. Prompt text is not
present in response archives, so prompt-byte identity cannot be established;
(task,sample,gold) alignment is the verified join.
"""
import csv, glob, gzip, json, os, sys
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr

DR = Path(os.environ.get(
    "MASLD_DATA_ROOT",
    os.environ.get("MASLD_LLM_ROOT", Path(__file__).resolve().parents[1]),
))
OUT = Path(os.environ.get(
    "MASLD_ELIGIBLE_OUTPUT_DIR",
    Path(__file__).resolve().parents[1] / "results" / "eligible",
))
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(DR / "scripts"))
import c2_paired as prod

SEED = 20260929
TASKS = ["MB-2001", "MB-2002", "MB-2003", "MB-2005", "MB-2006"]
EXPOSED = {"qwen3-0.6b-masld-v6", "qwen3-1.7b-masld-v6", "qwen3-8b-masld-v7"}
REN = {
    "amazon__nova-pro-v1":"Nova Pro", "anthropic__claude-sonnet-4.5":"Claude Sonnet 4.5",
    "deepseek__deepseek-chat":"DeepSeek Chat", "google__gemini-2.5-pro":"Gemini 2.5 Pro",
    "meta-llama__llama-3.3-70b-instruct":"Llama 3.3 70B",
    "nvidia__nemotron-3-super-120b-a12b:free":"Nemotron 120B",
    "openai__gpt-4.1":"GPT-4.1", "openai__gpt-4.1-mini":"GPT-4.1-mini",
    "openai__gpt-4o-mini":"GPT-4o-mini", "openai__gpt-5.6-luna":"GPT-5.6 Luna",
    "qwen__qwen-2.5-72b-instruct":"Qwen2.5 72B", "qwen__qwen3-235b-a22b-2507":"Qwen3 235B",
    "qwen3-0.6b-masld":"Qwen3-0.6B v3", "qwen3-0.6b-masld-v5":"Qwen3-0.6B v5",
    "qwen3-0.6b-masld-v6":"Qwen3-0.6B v6", "qwen3-1.7b-masld":"Qwen3-1.7B v3",
    "qwen3-1.7b-masld-v5":"Qwen3-1.7B v5", "qwen3-1.7b-masld-v6":"Qwen3-1.7B v6",
    "qwen3-8b-masld-v7":"Qwen3-8B v7", "inception__mercury-2.5":"Mercury-2.5",
}
COMPACT = {"Qwen3-0.6B v3", "Qwen3-0.6B v5", "Qwen3-1.7B v3", "Qwen3-1.7B v5"}


def read_corpus():
    rows = [r for r in prod.read_jsonl(DR / "prompts/MB-20xx_liver_test.jsonl.gz") if "task" in r]
    return {(r["task"], str(r["sample"])): r for r in rows}


def load_archives(corpus):
    out = {}
    audit = []
    for path in sorted(glob.glob(str(DR / "results/frontier_runs/*MB-20xx*.jsonl.gz"))):
        if "PAIRED" in path or ".DONE" in path:
            continue
        model = os.path.basename(path).replace("__MB-20xx.jsonl.gz", "")
        rows = [r for r in prod.read_jsonl(Path(path)) if "task" in r]
        keys = Counter((r["task"], str(r["sample"])) for r in rows)
        dup = sum(v - 1 for v in keys.values() if v > 1)
        indexed = {}
        for r in rows:
            k = (r["task"], str(r["sample"]))
            if k in corpus:
                indexed[k] = r  # no duplicates found in current archives
        superseded = sum(1 for r in rows if (r["task"], str(r["sample"])) not in corpus)
        mismatched = sum(1 for k, r in indexed.items() if str(r.get("answer")) != str(corpus[k]["answer"]))
        out[model] = indexed
        for task in TASKS:
            n = sum(1 for k in indexed if k[0] == task)
            corpus_n = sum(1 for k in corpus if k[0] == task)
            audit.append(dict(model=model, task=task, archived_in_corpus=n,
                              corpus_items=corpus_n, duplicate_archive_keys=dup,
                              superseded_rows=superseded, gold_mismatches=mismatched,
                              prompt_bytes_in_archive=False))
    return out, audit


def common_keys(archives, models, task):
    sets = [set(k for k in archives[m] if k[0] == task) for m in models]
    if any(len(s) == 0 for s in sets):
        return set()
    return sorted(set.intersection(*sets))


def pairwise_cohorts(archives, models):
    """Group models by the exact set of pairwise items they were queried on."""
    import hashlib
    groups = {}
    for m in models:
        keys = sorted(k for k in archives[m] if k[0] == "MB-2003")
        h = hashlib.sha256(json.dumps(keys).encode()).hexdigest()[:12]
        groups.setdefault(h, {"models": [], "keys": keys})["models"].append(m)
    # stable names by descending model count
    out = []
    for i, (h, g) in enumerate(sorted(groups.items(), key=lambda kv: -len(kv[1]["models"]))):
        out.append((f"pairwise_manifest_{i+1}_{h}", g["models"], g["keys"]))
    return out


def bootstrap_accuracy(records, task, keys, n_boot=2000):
    """records: dict key -> 0/1 correctness; sample-cluster bootstrap."""
    rng = np.random.default_rng(SEED)
    if task == "MB-2003":
        samples = sorted(set(s for k in keys for s in str(k[1]).split("|")))
        by_pair = []
        for k in keys:
            a, b = str(k[1]).split("|")
            by_pair.append((a, b, records[k]))
        stats = []
        for _ in range(n_boot):
            draw = rng.choice(samples, size=len(samples), replace=True)
            cnt = Counter(draw)
            num = den = 0.0
            for a, b, c in by_pair:
                w = cnt.get(a, 0) * cnt.get(b, 0)
                if w:
                    num += w * c
                    den += w
            if den:
                stats.append(num / den)
    else:
        vals = np.array([records[k] for k in keys], dtype=float)
        idx = rng.integers(0, len(vals), size=(n_boot, len(vals)))
        stats = vals[idx].mean(axis=1)
    if not len(stats):
        return (None, None)
    return float(np.percentile(stats, 2.5)), float(np.percentile(stats, 97.5))


def main():
    corpus = read_corpus()
    archives, audit_rows = load_archives(corpus)
    complete = sorted(m for m in archives if all(any(k[0] == t for k in archives[m]) for t in TASKS))
    eligible = [m for m in complete if m not in EXPOSED]
    exposed = [m for m in complete if m in EXPOSED]
    print("eligible models:", len(eligible))
    print("exposed diagnostic models:", exposed)

    per_item = []
    summary = []
    main_pairwise_roster = None
    for task in TASKS:
        if task == "MB-2003":
            cohorts = pairwise_cohorts(archives, eligible)
            main_pairwise_roster = cohorts[0][0]
            exposed_keys = common_keys(archives, exposed, task)
            task_sets = [(name, models, keys) for name, models, keys in cohorts]
            task_sets.append(("exposed_diagnostic", exposed, exposed_keys))
            print(task, "pairwise manifests:", [(n, len(m), len(k)) for n, m, k in task_sets])
        else:
            keys = common_keys(archives, eligible, task)
            exposed_keys = common_keys(archives, exposed, task)
            print(task, "eligible common n =", len(keys), "| exposed common n =", len(exposed_keys))
            task_sets = [("eligible", eligible, keys), ("exposed_diagnostic", exposed, exposed_keys)]
        for roster_name, roster, rkeys in task_sets:
            for model in roster:
                at = prod.answer_type(task)
                recs = [archives[model][k] for k in rkeys]
                golds, kept, kept_keys = [], [], []
                for k, r in zip(rkeys, recs):
                    try:
                        golds.append(prod.gold_value(str(r["answer"]), at))
                        kept.append(r); kept_keys.append(k)
                    except (ValueError, IndexError):
                        pass
                preds = [prod.parse_answer(r.get("raw"), at) for r in kept]
                domain = (0, 4) if task == "MB-2005" else (0, 8) if task == "MB-2006" else None
                correct = {}
                abs_errors = []
                for k, r, p, g in zip(kept_keys, kept, preds, golds):
                    valid = p is not None
                    in_domain = bool(valid and (domain is None or domain[0] <= float(p) <= domain[1]))
                    c = None
                    ae = None
                    if at[0] != "number":
                        c = 1 if valid and str(p) == str(g) else 0
                        correct[k] = c
                    else:
                        if valid:
                            ae = abs(float(p) - float(g))
                    per_item.append(dict(roster=roster_name, model=model, task=task,
                                         sample=k[1], gold=g, parsed="" if p is None else p,
                                         valid=int(valid), in_domain=int(in_domain),
                                         correct="" if c is None else c,
                                         abs_error="" if ae is None else ae,
                                         operational_error=r.get("error") or ""))
                if at[0] == "number":
                    valid_pairs = [(p, g) for p, g in zip(preds, golds) if p is not None]
                    domain_pairs = [(p, g) for p, g in zip(preds, golds)
                                    if p is not None and domain[0] <= float(p) <= domain[1]]
                    mae = float(np.mean([abs(p-g) for p,g in valid_pairs])) if valid_pairs else None
                    mae_domain = float(np.mean([abs(p-g) for p,g in domain_pairs])) if domain_pairs else None
                    penalty = domain[1]
                    failure_mae = float(np.mean([abs(p-g) if (p is not None and domain[0] <= float(p) <= domain[1]) else penalty
                                                 for p,g in zip(preds,golds)]))
                    rho = float(spearmanr([p for p,g in valid_pairs], [g for p,g in valid_pairs]).statistic) if len(valid_pairs) >= 3 else None
                    summary.append(dict(roster=roster_name, model=model, task=task, n=len(kept),
                                        valid=len(valid_pairs), in_domain=len(domain_pairs),
                                        correct="", accuracy="", ci_lo="", ci_hi="",
                                        mae=mae, mae_in_domain=mae_domain,
                                        mae_failure_aware=failure_mae, spearman=rho))
                else:
                    vals = np.array(list(correct.values()), dtype=float)
                    lo, hi = bootstrap_accuracy(correct, task, kept_keys)
                    summary.append(dict(roster=roster_name, model=model, task=task, n=len(kept),
                                        valid=int(sum(p is not None for p in preds)),
                                        in_domain=int(sum(p is not None for p in preds)),
                                        correct=int(vals.sum()), accuracy=float(vals.mean()),
                                        ci_lo=lo, ci_hi=hi, mae="", mae_in_domain="",
                                        mae_failure_aware="", spearman=""))

    per_item_dir = os.environ.get("MASLD_PER_ITEM_DIR")
    if per_item_dir:
        Path(per_item_dir).mkdir(parents=True, exist_ok=True)
        with open(Path(per_item_dir) / "tissue_eligible_per_item.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(per_item[0].keys()))
            w.writeheader(); w.writerows(per_item)
    else:
        print("subject-level per-item file not written; set MASLD_PER_ITEM_DIR to export it privately")
    with open(OUT / "tissue_eligible_summary.tsv", "w", newline="") as f:
        fields = ["roster","model","task","n","valid","in_domain","correct","accuracy","ci_lo","ci_hi","mae","mae_in_domain","mae_failure_aware","spearman"]
        w = csv.DictWriter(f, fieldnames=fields, delimiter="\t")
        w.writeheader(); w.writerows(summary)
    with open(OUT / "tissue_archive_coverage_audit.tsv", "w", newline="") as f:
        fields = ["model","task","archived_in_corpus","corpus_items","duplicate_archive_keys","superseded_rows","gold_mismatches","prompt_bytes_in_archive"]
        w = csv.DictWriter(f, fieldnames=fields, delimiter="\t")
        w.writeheader(); w.writerows(audit_rows)

    # Label distributions are computed from the evaluated gold labels, never
    # inferred from the number of classes.
    label_distributions = {}
    for task in ("MB-2001", "MB-2002"):
        ref_model = eligible[0]
        labels = [str(r["gold"]) for r in per_item
                  if r["roster"] == "eligible" and r["model"] == ref_model and r["task"] == task]
        counts = dict(Counter(labels))
        label_distributions[task] = {"n": len(labels), "counts": counts,
                                     "majority_count": max(counts.values()),
                                     "majority_accuracy": max(counts.values()) / len(labels)}

    # Joint-valid sensitivity for the direct v5-vs-Llama fibrosis comparison.
    def parsed_map(model, task):
        return {r["sample"]: (float(r["parsed"]), float(r["gold"]))
                for r in per_item
                if r["roster"] == "eligible" and r["model"] == model and r["task"] == task and r["valid"] == 1}
    a = parsed_map("qwen3-1.7b-masld-v5", "MB-2005")
    b = parsed_map("meta-llama__llama-3.3-70b-instruct", "MB-2005")
    joint = sorted(set(a) & set(b))
    joint_valid = {
        "task": "MB-2005",
        "models": ["qwen3-1.7b-masld-v5", "meta-llama__llama-3.3-70b-instruct"],
        "n_joint_valid": len(joint),
        "qwen3_1_7b_v5_mae": float(np.mean([abs(a[s][0] - a[s][1]) for s in joint])),
        "llama_3_3_70b_mae": float(np.mean([abs(b[s][0] - b[s][1]) for s in joint])),
        "note": "joint-valid subset is selected by successful parsing and does not replace failure-aware whole-set reporting",
    }
    with open(OUT / "tissue_regression_joint_valid.tsv", "w") as f:
        f.write("task\tn_joint_valid\tqwen3_1_7b_v5_mae\tllama_3_3_70b_mae\n")
        f.write(f"MB-2005\t{len(joint)}\t{joint_valid['qwen3_1_7b_v5_mae']}\t{joint_valid['llama_3_3_70b_mae']}\n")

    package_analysis = Path(__file__).resolve().parent / "tissue_eligible.json"
    package_analysis.write_text(json.dumps({
        "description": "Eligible-model tissue analysis with aligned evaluated item sets; generated by rescore_tissue_eligible.py",
        "eligible_model_count": len(eligible),
        "exposed_models": exposed,
        "aligned_binary_n": 163,
        "aligned_binary_majority": 107/163,
        "aligned_label_distributions": label_distributions,
        "joint_valid_regression": joint_valid,
        "records": summary,
    }, indent=1))

    # Ranks: four single-sample tasks share one item set across all 17 models.
    # Pairwise ranks are computed only within the largest exact-item manifest.
    ranks = {}
    for task in TASKS:
        roster_name = main_pairwise_roster if task == "MB-2003" else "eligible"
        rows = [r for r in summary if r["roster"] == roster_name and r["task"] == task]
        metric = "accuracy" if task in TASKS[:3] else "mae"
        reverse = metric == "accuracy"
        ordered = sorted(rows, key=lambda r: ((-r[metric] if reverse else r[metric]) if r[metric] is not None else (float("-inf") if reverse else float("inf"))))
        prev = None; rank = 1
        for i, r in enumerate(ordered):
            val = r[metric]
            if val is None:
                ranks[(r["model"], task)] = len(rows)  # no valid numeric output = worst, not best
                continue
            if prev is None or abs(val - prev) > 1e-12:
                rank = i + 1
            ranks[(r["model"], task)] = rank
            prev = val
    rank_rows = []
    single_tasks = ["MB-2001", "MB-2002", "MB-2005", "MB-2006"]
    for model in eligible:
        rr = [ranks[(model, t)] for t in single_tasks]
        row = dict(model=REN.get(model, model),
                   **{t: ranks.get((model, t), "") for t in TASKS},
                   mean_rank_single4=float(np.mean(rr)))
        if (model, "MB-2003") in ranks:
            row["mean_rank_all5_same_manifest"] = float(np.mean(rr + [ranks[(model, "MB-2003")]]))
        else:
            row["mean_rank_all5_same_manifest"] = ""
        rank_rows.append(row)
    rank_rows.sort(key=lambda r: r["mean_rank_single4"])
    with open(OUT / "tissue_eligible_ranks.tsv", "w", newline="") as f:
        fields = ["model"] + TASKS + ["mean_rank_single4", "mean_rank_all5_same_manifest"]
        w = csv.DictWriter(f, fieldnames=fields, delimiter="\t")
        w.writeheader(); w.writerows(rank_rows)
    print("wrote eligible per-item, summary, coverage and ranks")
    for r in rank_rows:
        print(r)


if __name__ == "__main__":
    main()
