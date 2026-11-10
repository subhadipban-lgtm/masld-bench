#!/usr/bin/env python3
"""
Corrected analysis for the MB-89xx (plasma cfRNA) family and related claims.

Design rules
------------
* Frozen prompt/response archives are READ-ONLY. Nothing is regenerated.
* Every corrected quantity is written next to the legacy value with the cause.
* The existing frozen feature representation was built gene-wise (each gene
  standardised across samples). That is a defect in the METHODS description,
  not something to silently repair inside the freeze. We therefore report:
    (a) the frozen/transductive representation, described accurately, and
    (b) a clearly labelled inductive sensitivity analysis that refits panel
        selection and scaling inside training folds.
* No new model inference is performed.
"""
from __future__ import annotations

import gzip
import json
import os
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import binomtest, spearmanr
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold

ROOT = Path(os.environ.get(
    "MASLD_DATA_ROOT",
    os.environ.get("MASLD_LLM_ROOT", Path(__file__).resolve().parents[1]),
))
OUT = Path(__file__).resolve().parent
PROMPTS = ROOT / "prompts"
RUNS = ROOT / "results" / "frontier_runs"
DATA = ROOT / "data" / "sbsst1614"
SEED = 20260929
N_BOOT = 2000

sys.path.insert(0, str(ROOT / "scripts"))
from c2_paired import parse_yes_no, parse_number  # noqa: E402
from build_mb89xx import (  # noqa: E402
    F_STAGES, NAFLD_ETIOLOGIES, load_matrix as _proj_load_matrix,
    read_ann as _proj_read_ann,
)


def _amc_stage(v):
    """Parse a reader-2 fibrosis stage; non-numeric/absent -> -1."""
    try:
        t = str(v).strip()
        if t in {"", "NA", "na", "nan", "None"}:
            return -1
        return int(float(t))
    except (TypeError, ValueError):
        return -1


def bootstrap_ci(vals, n=N_BOOT, seed=SEED):
    rng = np.random.default_rng(seed)
    vals = np.asarray(vals, dtype=float)
    idx = rng.integers(0, len(vals), size=(n, len(vals)))
    means = vals[idx].mean(axis=1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def read_jsonl_gz(p):
    with gzip.open(p, "rt") as f:
        return [json.loads(line) for line in f]


def load_matrix_legacy_unused(path: Path):
    """Return (samples, genes, genes x samples matrix) as in build_mb89xx."""
    with open(path) as f:
        header = f.readline().rstrip("\n").split("\t")
    genes, cols = [], []
    with open(path) as f:
        f.readline()
        for line in f:
            parts = line.rstrip("\n").split("\t")
            genes.append(parts[0])
            cols.append([float(x) for x in parts[1:]])
    mat = np.array(cols, dtype=float)
    return header[1:], genes, mat


def read_ann(path: Path):
    return _proj_read_ann(path)


def cpm_log1p(mat):
    cpm = mat / np.maximum(mat.sum(axis=0, keepdims=True), 1.0) * 1e6
    return np.log1p(cpm)


def top_mad(t, n=200):
    mad = np.median(np.abs(t - np.median(t, axis=1, keepdims=True)), axis=1)
    return np.argsort(mad)[::-1][:n]


def z_gene_wise(t, idx, mu=None, sd=None):
    """Frozen representation: standardise each GENE across samples."""
    sub = t[idx]
    if mu is None:
        mu = sub.mean(axis=1, keepdims=True)
    if sd is None:
        sd = np.maximum(sub.std(axis=1, keepdims=True), 1e-12)
    return (sub - mu) / sd


def z_sample_wise(t, idx, mu=None, sd=None):
    """Methods-as-written representation: standardise each SAMPLE across genes."""
    sub = t[idx]
    if mu is None:
        mu = sub.mean(axis=0, keepdims=True)
    if sd is None:
        sd = np.maximum(sub.std(axis=0, keepdims=True), 1e-12)
    return (sub - mu) / sd


def oof(X, y, factory, n_splits=5):
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=SEED)
    preds = np.empty(len(y), dtype=float)
    for tr, te in skf.split(X, y):
        m = factory()
        m.fit(X[tr], y[tr])
        preds[te] = m.predict(X[te])
    return preds


def cohen_kappa(a, b):
    a, b = list(a), list(b)
    labels = sorted(set(a) | set(b))
    n = len(a)
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    pe = sum((a.count(l) / n) * (b.count(l) / n) for l in labels)
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


def weighted_kappa(a, b, w="quadratic"):
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    labels = np.unique(np.concatenate([a, b]))
    k = len(labels)
    O = np.zeros((k, k))
    index = {v: i for i, v in enumerate(labels)}
    for x, y in zip(a, b):
        O[index[x], index[y]] += 1
    O /= O.sum()
    r = O.sum(axis=1)
    c = O.sum(axis=0)
    E = np.outer(r, c)
    if w == "quadratic":
        W = np.array([[(i - j) ** 2 for j in range(k)] for i in range(k)]) / max(1, (k - 1) ** 2)
    else:
        W = np.array([[abs(i - j) for j in range(k)] for i in range(k)]) / max(1, k - 1)
    num = (W * O).sum()
    den = (W * E).sum()
    return 1 - num / den if den else float("nan")


def binary_metrics(gold, pred):
    """gold/pred are 0/1; pred None = invalid (counted as error)."""
    gold = np.asarray(gold, dtype=int)
    valid = np.array([p is not None and not (isinstance(p, float) and np.isnan(p)) for p in pred])
    p = np.array([int(x) if v else 0 for x, v in zip(pred, valid)])
    tp = int(((gold == 1) & (p == 1) & valid).sum())
    fn = int(((gold == 1) & ((p == 0) | ~valid)).sum())
    tn = int(((gold == 0) & (p == 0) & valid).sum())
    fp = int(((gold == 0) & (p == 1) & valid).sum())
    n = len(gold)
    # invalid-as-error: the denominator for each class is ALL gold items of that
    # class, so a non-answer on a gold-negative counts against specificity too.
    n_pos = int((gold == 1).sum())
    n_neg = int((gold == 0).sum())
    sens = tp / n_pos if n_pos else float("nan")
    spec = tn / n_neg if n_neg else float("nan")
    return dict(n=n, valid=int(valid.sum()), invalid=int(n - valid.sum()),
                tp=tp, fn=fn, tn=tn, fp=fp, accuracy=(tp + tn) / n,
                sensitivity=float(sens), specificity=float(spec),
                balanced_accuracy=float(np.nanmean([sens, spec])),
                validity=float(valid.mean()),
                n_yes_predicted=int((p == 1).sum()))


def holm(pvals):
    m = len(pvals)
    order = np.argsort(pvals)
    adj = np.empty(m)
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * pvals[i]))
        adj[i] = running
    return adj


def cohort2():
    s2, g2, m2 = _proj_load_matrix(DATA / "htseq_cohort2.txt")
    ann2 = read_ann(DATA / "annotation_cohort2.csv")
    from build_mb89xx import NAFLD_ETIOLOGIES, F_STAGES
    sub = [r for r in ann2 if r.get("Etiology") in NAFLD_ETIOLOGIES]
    by_subj = {}
    for r in sub:
        by_subj.setdefault(r["Subject_ID"], []).append(r)
    kept2 = []
    for sid, rs in by_subj.items():
        base = [r for r in rs if r.get("Visit_Type") == "Baseline"]
        kept2.append((base or rs)[0])
    kept2 = [r for r in kept2 if r.get("Fibrosis") in F_STAGES]
    s2sel = [r["SMAPLE_RNA"] for r in kept2]
    t2 = cpm_log1p(m2[:, [s2.index(s) for s in s2sel]])
    X2 = z_gene_wise(t2, top_mad(t2)).T
    y2 = np.array([F_STAGES[r["Fibrosis"]] for r in kept2])
    return X2, y2


def cohort1():
    s1, g1, m1 = _proj_load_matrix(DATA / "htseq_cohort1.txt")
    ann1 = read_ann(DATA / "annotation_cohort1.csv")
    by1 = {r["SMAPLE_RNA"]: r for r in ann1}
    keep1 = [s for s in s1 if s in by1]
    t1 = cpm_log1p(m1[:, [s1.index(s) for s in keep1]])
    X1 = z_gene_wise(t1, top_mad(t1)).T
    y1 = np.array([int(by1[s]["fibrosis"]) for s in keep1])
    names = [g1[i] for i in top_mad(t1)]
    return X1, y1, by1, keep1, names


def corrected_gates():
    X1, y1, by1, keep1, _ = cohort1()
    X2, y2 = cohort2()
    out = {}

    for name, X, y in [("MB-8901", X1, (y1 >= 3).astype(int)),
                       ("MB-8911", X2, (y2 >= 3).astype(int))]:
        n = len(y)
        counts = Counter(y.tolist())
        maj = max(counts.values()) / n
        five = max(Counter((y1 if name == "MB-8901" else y2).tolist()).values()) / n
        for mname, factory in [
            ("logreg", lambda: LogisticRegression(max_iter=3000, C=1.0)),
            ("hgb", lambda: HistGradientBoostingClassifier(random_state=SEED)),
        ]:
            pred = oof(X, y, factory)
            accs = (pred == y).astype(float)
            lo, hi = bootstrap_ci(accs)
            out[f"{name}_{mname}"] = dict(
                n=n, accuracy=float(accs.mean()), ci=[lo, hi],
                majority_corrected=float(maj),
                majority_legacy_reported=float(five),
                beats_majority_corrected=bool(lo > maj),
                beats_majority_reported_legacy=bool(lo > five),
                n_majority=int(max(counts.values())),
                n_minority=int(n - max(counts.values())),
            )

    amc = np.array([_amc_stage(by1[s]["fibrosis_AMC"]) for s in keep1])
    joint = amc >= 0
    Xa, ya = X1[joint], (amc[joint] >= 3).astype(int)
    counts = Counter(ya.tolist())
    maj = max(counts.values()) / len(ya)
    five = max(Counter(amc[joint].tolist()).values()) / len(ya)
    for mname, factory in [
        ("logreg", lambda: LogisticRegression(max_iter=3000, C=1.0)),
        ("hgb", lambda: HistGradientBoostingClassifier(random_state=SEED)),
    ]:
        pred = oof(Xa, ya, factory)
        accs = (pred == ya).astype(float)
        lo, hi = bootstrap_ci(accs)
        out[f"MB-8921_{mname}"] = dict(
            n=len(ya), accuracy=float(accs.mean()), ci=[lo, hi],
            majority_corrected=float(maj), majority_legacy_reported=float(five),
            beats_majority_corrected=bool(lo > maj),
            n_majority=int(max(counts.values())),
            n_minority=int(len(ya) - max(counts.values())),
        )

    out["ordinal_superseded_by"] = (
        "v2_corrections.json part3_ordinal; the legacy LogisticRegression/"
        "HGBClassifier ordinal blocks are no longer computed in this artifact"
    )
    return out


BINARY = {"MB-8901", "MB-8911", "MB-8921"}


def llm_metrics():
    golds = {}
    for p, t in [
        (PROMPTS / "MB-89xx_plasmacf_test.jsonl.gz", "MB-8901"),
        (PROMPTS / "MB-89xx_plasmacf_ext_test.jsonl.gz", "MB-8911"),
        (PROMPTS / "MB-89xx_plasmacf_amcvar_test.jsonl.gz", "MB-8921"),
    ]:
        for r in read_jsonl_gz(p):
            if r.get("task") == t:
                golds[(t, r["sample"])] = r["answer"]

    rows, summary = [], {}
    for arc in sorted(RUNS.glob("*__MB-89xx.jsonl.gz")):
        model = arc.name.replace("__MB-89xx.jsonl.gz", "")
        recs = read_jsonl_gz(arc)
        mrows = []
        for r in recs:
            task = r.get("task")
            if task not in BINARY:
                continue
            gtxt = golds.get((task, r["sample"]), r.get("answer"))
            gold = 1 if str(gtxt).strip().lower() == "yes" else 0
            raw = r.get("raw") or ""
            if r.get("error"):
                pred, status = None, "operational_error"
            else:
                v = parse_yes_no(raw) if raw.strip() else None
                pred, status = ((1 if v == "yes" else 0), "scored") if v else (None, "invalid_answer")
            mrows.append(dict(model=model, task=task, sample=r["sample"],
                              gold=gold, pred=pred, status=status))
        df = pd.DataFrame(mrows)
        rows.append(df)
        summary[model] = {}
        for task in sorted(df["task"].unique()):
            d = df[df.task == task]
            m = binary_metrics(d.gold.tolist(), d.pred.tolist())
            correct = np.array([1.0 if (pp is not None and pp == gg) else 0.0
                                for pp, gg in zip(d.pred.tolist(), d.gold.tolist())])
            lo, hi = bootstrap_ci(correct)
            m["accuracy_ci"] = [lo, hi]
            m["operational_errors"] = int((d.status == "operational_error").sum())
            m["invalid_answers"] = int((d.status == "invalid_answer").sum())
            summary[model][task] = m
    if os.environ.get("MASLD_WRITE_SUBJECT_LEVEL") == "1":
        pd.concat(rows, ignore_index=True).to_csv(OUT / "per_item_metrics.csv", index=False)
    return summary


def discrimination():
    out = {}
    golds = {}
    for p, t in [
        (PROMPTS / "MB-89xx_plasmacf_test.jsonl.gz", "MB-8905"),
        (PROMPTS / "MB-89xx_plasmacf_ext_test.jsonl.gz", "MB-8915"),
    ]:
        for r in read_jsonl_gz(p):
            if r.get("task") == t:
                golds[(t, r["sample"])] = int(float(r["answer"]))
    for arc in sorted(RUNS.glob("*__MB-89xx.jsonl.gz")):
        model = arc.name.replace("__MB-89xx.jsonl.gz", "")
        recs = read_jsonl_gz(arc)
        for task in ("MB-8905", "MB-8915"):
            y, s = [], []
            for r in recs:
                if r.get("task") != task or r.get("error"):
                    continue
                v = parse_number(r.get("raw") or "")
                g = golds.get((task, r["sample"]))
                if v is None or g is None or not np.isfinite(v):
                    continue
                y.append(int(g >= 3))
                s.append(float(v))
            if len(set(y)) < 2 or len(y) < 10:
                continue
            out.setdefault(task, {})[model] = dict(
                n=len(y), pos=int(sum(y)),
                auroc=float(roc_auc_score(y, s)),
                average_precision=float(average_precision_score(y, s)),
            )
    return out


def signal_concentration():
    X1, y1, by1, keep1, names = cohort1()
    yb = (y1 >= 3).astype(int)
    legacy, nested = {}, {}
    for k in (5, 10, 20, 50, 200):
        aucs = [(abs(roc_auc_score(yb, X1[:, j]) - 0.5), j) for j in range(X1.shape[1])]
        idx = [j for _, j in sorted(aucs, reverse=True)[:k]]
        p = oof(X1[:, idx], yb, lambda: LogisticRegression(max_iter=3000, C=1.0))
        legacy[k] = float((p == yb).mean())
    for k in (5, 10, 20, 50, 200):
        skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
        pred = np.empty(len(yb), dtype=float)
        for tr, te in skf.split(X1, yb):
            aucs = [(abs(roc_auc_score(yb[tr], X1[tr, j]) - 0.5), j) for j in range(X1.shape[1])]
            idx = [j for _, j in sorted(aucs, reverse=True)[:k]]
            m = LogisticRegression(max_iter=3000, C=1.0).fit(X1[tr][:, idx], yb[tr])
            pred[te] = m.predict(X1[te][:, idx])
        nested[k] = float((pred == yb).mean())

    order = sorted(range(X1.shape[1]), key=lambda j: -abs(roc_auc_score(yb, X1[:, j]) - 0.5))
    single = {}
    for j in order[:8]:
        a = roc_auc_score(yb, X1[:, j])
        single[names[j]] = float(a if a >= 0.5 else 1 - a)

    top5 = order[:5]
    X2, y2 = cohort2()
    y2b = (y2 >= 3).astype(int)
    m = LogisticRegression(max_iter=3000, C=1.0).fit(X1[:, top5], yb)
    return dict(
        genes_top5=[names[j] for j in top5],
        legacy_leaky_oof_acc=legacy,
        nested_oof_acc=nested,
        single_gene_auc=single,
        anchor_fixed_transfer=dict(
            anchor_acc=float((m.predict(X1[:, top5]) == yb).mean()),
            extension_acc=float((m.predict(X2[:, top5]) == y2b).mean()),
            extension_majority=float(max(np.bincount(y2b)) / len(y2b)),
            extension_n=int(len(y2b)),
            note="panel fixed on anchor, classifier fit on anchor, applied unchanged to extension",
        ),
    )


def reader_sensitivity():
    X1, y1, by1, keep1, _ = cohort1()
    amc = np.array([_amc_stage(by1[s]["fibrosis_AMC"]) for s in keep1])
    joint = amc >= 0
    Xj, u, a = X1[joint], y1[joint], amc[joint]
    pred5 = oof(Xj, u, lambda: LogisticRegression(max_iter=3000, C=1.0))
    predb = oof(Xj, (u >= 3).astype(int), lambda: LogisticRegression(max_iter=3000, C=1.0))
    return dict(
        n_joint=int(joint.sum()),
        reader_agreement=dict(
            exact=int((u == a).sum()), exact_n=int(len(u)),
            exact_fraction=float((u == a).mean()),
            unweighted_kappa=float(cohen_kappa(u.tolist(), a.tolist())),
            quadratic_kappa=float(weighted_kappa(u, a, "quadratic")),
            linear_kappa=float(weighted_kappa(u, a, "linear")),
            binary_kappa=float(cohen_kappa((u >= 3).astype(int).tolist(),
                                           (a >= 3).astype(int).tolist())),
        ),
        five_class_fixed_predictions=dict(
            accuracy_vs_uza=float((pred5 == u).mean()),
            accuracy_vs_amc=float((pred5 == a).mean()),
            difference=float((pred5 == u).mean() - (pred5 == a).mean()),
            note="same OOF predictions, same 108 samples: reader-label sensitivity, not a ceiling",
        ),
        binary_fixed_predictions=dict(
            accuracy_vs_uza=float((predb == (u >= 3)).mean()),
            accuracy_vs_amc=float((predb == (a >= 3)).mean())),
    )


def multiplicity():
    fam = []
    for label, fn, task in [
        ("MB-8901 GPT-4o-mini vs always-no", "openai__gpt-4o-mini__MB-89xx.jsonl.gz", "MB-8901"),
        ("MB-8911 Qwen3-235B vs always-no", "qwen__qwen3-235b-a22b-2507__MB-89xx.jsonl.gz", "MB-8911"),
    ]:
        recs = [r for r in read_jsonl_gz(RUNS / fn) if r.get("task") == task]
        w = l = 0
        for r in recs:
            v = parse_yes_no(r.get("raw") or "")
            if v is None:
                continue
            g = r["answer"]
            ok, base = (v == g), (g == "no")
            if ok and not base:
                w += 1
            elif base and not ok:
                l += 1
        p = float(binomtest(min(w, l), w + l, 0.5).pvalue) if (w + l) else 1.0
        fam.append(dict(name=label, wins=w, losses=l, p_raw=p))
    adj = holm([f["p_raw"] for f in fam])
    for f, a in zip(fam, adj):
        f["p_holm"] = float(a)
        f["interpretation"] = ("no statistically detectable difference from always-no"
                               if a >= 0.05 else "statistically detectable difference")
    return dict(family="cfRNA binary LLM-vs-majority paired comparisons (2 tests)",
                tests=fam)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    corr = {}

    g = corrected_gates()
    (OUT / "gate_recompute.json").write_text(json.dumps(g, indent=1))
    legacy = json.loads((ROOT / "results" / "gates_mb89xx.json").read_text())
    for k, lk in [("MB-8901_logreg", "8901_anchor_binary"), ("MB-8911_logreg", "8911_ext_binary"),
                  ("MB-8921_logreg", "8921_amc_binary")]:
        corr[lk] = dict(legacy=legacy.get(lk), corrected=g.get(k))

    (OUT / "llm_binary_metrics.json").write_text(json.dumps(llm_metrics(), indent=1))
    (OUT / "reader_sensitivity.json").write_text(json.dumps(reader_sensitivity(), indent=1))
    if os.environ.get("MASLD_WRITE_LEGACY") == "1":
        # Historical diagnostics only; not part of the authoritative release path.
        (OUT / "discrimination.json").write_text(json.dumps(discrimination(), indent=1))
        (OUT / "signal_concentration.json").write_text(json.dumps(signal_concentration(), indent=1))
        (OUT / "multiplicity.json").write_text(json.dumps(multiplicity(), indent=1))

    corr["binary_majority_baselines"] = [
        dict(task="MB-8901", n=112, minority=32, corrected=80 / 112, legacy=0.3036,
             cause="five-class majority passed into binary gate"),
        dict(task="MB-8911", n=179, minority=84, corrected=95 / 179, legacy=0.3352,
             cause="five-class majority passed into binary gate"),
        dict(task="MB-8921", n=108, minority=35, corrected=73 / 108, legacy=0.3056,
             cause="five-class majority passed into binary gate"),
    ]
    corr["normalization"] = dict(
        methods_claim="per-sample z-score across the panel",
        implementation="per-gene z-score across samples",
        consequence="describe the frozen corpus accurately; label the analysis transductive",
    )
    corr["auprc"] = dict(
        implementation="argsort without tie grouping; trapezoid over PR curve labelled average precision",
        defect="row-order dependent under score ties",
        demonstration=dict(labels_1100_all_tied=1.0, labels_0011_all_tied=0.291667,
                           sklearn_average_precision_both=0.5),
    )
    corr["regression_scoring"] = dict(
        implementation="MAE over parsed values only; validity reported separately",
        declared_policy="invalid as error",
        consequence="conditional MAE is optimistic when validity is low",
        serialization_bug="`if lo` / `if hi` drops a legitimate 0.0 bound",
    )
    (OUT / "CORRECTIONS.json").write_text(json.dumps(corr, indent=1))
    print("wrote", OUT)
    for f in sorted(OUT.glob("*.json")):
        print("  ", f.name, f.stat().st_size)
    print("  per_item_metrics.csv exists:", (OUT / "per_item_metrics.csv").exists())


if __name__ == "__main__":
    main()
