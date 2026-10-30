#!/usr/bin/env python3
"""C2-style paired significance for MB-89xx + LLM-vs-logreg head-to-head.

1. Per-task best-LLM-vs-rest McNemar tables (8901 anchor, 8911 extension).
2. Top LLM vs the classical logreg gate on IDENTICAL items (McNemar exact) —
   the C4 regime-split test on the new family.

Outputs: results/c2_significance_89xx.{md,csv}
"""

from __future__ import annotations

import json
import os
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from scipy.stats import binomtest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_mb89xx import cpm_log1p_z, load_matrix, read_ann, top_mad_genes, zscore_panel  # noqa: E402
from c2_paired import answer_type, archive_model_name, gold_value, parse_answer, read_jsonl  # noqa: E402
from gates_mb89xx import oof_predict  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402

ROOT = Path(os.environ.get("MASLD_LLM_ROOT", Path(__file__).resolve().parents[1]))
RUNS = ROOT / "results" / "frontier_runs"
DATA = ROOT / "data" / "sbsst1614"
RESULTS = ROOT / "results"
SEED = 20260929


def load_archive(path: Path) -> dict[tuple[str, str], dict]:
    out = {}
    for r in read_jsonl(path):
        if "__meta__" in r:
            continue
        out[(r["task"], r["sample"])] = r
    return out


def mcnemar_exact(b: int, c: int):
    n = b + c
    if n == 0:
        return None
    return float(binomtest(b, n, 0.5).pvalue)


def logreg_oof_binary(X, y):
    return oof_predict(X, y, lambda: LogisticRegression(max_iter=3000, C=1.0))


def main():
    archives = sorted(RUNS.glob("*__MB-89xx.jsonl.gz"))
    models = {}
    for p in archives:
        name, _ = archive_model_name(p)
        models[name] = load_archive(p)

    md = ["# C2 paired significance — MB-89xx (2026-10-29/30)",
          "",
          "McNemar exact on identical items; verdict at p < 0.05.",
          ""]
    csv_rows = []

    for task in ("MB-8901", "MB-8911"):
        at = answer_type(task)
        # per-model accuracy on the task
        accs = {}
        for name, arch in models.items():
            preds, golds = [], []
            for (t, s), r in arch.items():
                if t != task:
                    continue
                try:
                    g = gold_value(str(r["answer"]), at)
                except (ValueError, IndexError):
                    continue
                golds.append(g)
                preds.append(parse_answer(r.get("raw"), at))
            if not golds:
                continue
            accs[name] = sum(1 for p, g in zip(preds, golds) if p is not None and p == g) / len(golds)
        best = max(accs, key=accs.get)
        md.append(f"## {task} — best LLM {best} ({accs[best]:.4f}) vs the bracket")
        md.append("")
        md.append("| reference | n | cand | ref | both | cand_only | ref_only | neither | mcnemar_p | verdict |")
        md.append("|---|---|---|---|---|---|---|---|---|---|")
        cand_arch = models[best]
        for name, arch in models.items():
            if name == best:
                continue
            keys = sorted({(t, s) for (t, s) in cand_arch if t == task} &
                          {(t, s) for (t, s) in arch if t == task})
            both = c_only = r_only = 0
            for k in keys:
                try:
                    g = gold_value(str(cand_arch[k]["answer"]), at)
                except (ValueError, IndexError):
                    continue
                cp = parse_answer(cand_arch[k].get("raw"), at)
                rp = parse_answer(arch[k].get("raw"), at)
                cc = cp is not None and cp == g
                rc = rp is not None and rp == g
                if cc and rc:
                    both += 1
                elif cc:
                    c_only += 1
                elif rc:
                    r_only += 1
            n = len(keys)
            neither = n - both - c_only - r_only
            p = mcnemar_exact(c_only, r_only)
            if p is not None and p < 0.05:
                verdict = "WIN" if c_only > r_only else "LOSS"
            else:
                verdict = "TIE"
            ref_acc = accs[name]
            md.append(f"| {name} | {n} | {accs[best]:.4f} | {ref_acc:.4f} | {both} | "
                      f"{c_only} | {r_only} | {neither} | {p if p is None else round(p, 6)} | {verdict} |")
            csv_rows.append(dict(task=task, candidate=best, reference=name, n=n,
                                 cand=round(accs[best], 4), ref=round(ref_acc, 4),
                                 both=both, cand_only=c_only, ref_only=r_only,
                                 neither=neither, mcnemar_p=p, verdict=verdict))
        md.append("")

    # ---- LLM vs logreg on identical items (C4) ----
    s1, g1, m1 = load_matrix(DATA / "htseq_cohort1.txt")
    ann1 = read_ann(DATA / "annotation_cohort1.csv")
    by_id = {r["SMAPLE_RNA"]: r for r in ann1}
    keep1 = [s for s in s1 if s in by_id]
    idx1 = [s1.index(s) for s in keep1]
    t1 = cpm_log1p_z(m1[:, idx1])
    panel1, pidx1 = top_mad_genes(t1, g1)
    X1 = zscore_panel(t1, pidx1).T
    y1 = np.array([int(by_id[s]["fibrosis"]) for s in keep1]) >= 3

    s2, g2, m2 = load_matrix(DATA / "htseq_cohort2.txt")
    ann2 = read_ann(DATA / "annotation_cohort2.csv")
    from build_mb89xx import F_STAGES, NAFLD_ETIOLOGIES
    sub = [r for r in ann2 if r.get("Etiology") in NAFLD_ETIOLOGIES]
    by_subj: dict[str, list] = {}
    for r in sub:
        by_subj.setdefault(r["Subject_ID"], []).append(r)
    kept2 = []
    for sid, rs in by_subj.items():
        base = [r for r in rs if r.get("Visit_Type") == "Baseline"]
        kept2.append((base or rs)[0])
    kept2 = [r for r in kept2 if r.get("Fibrosis") in F_STAGES]
    s2_sel = [r["SMAPLE_RNA"] for r in kept2]
    idx2 = [s2.index(s) for s in s2_sel]
    t2 = cpm_log1p_z(m2[:, idx2])
    panel2, pidx2 = top_mad_genes(t2, g2)
    X2 = zscore_panel(t2, pidx2).T
    y2 = np.array([F_STAGES[r["Fibrosis"]] for r in kept2]) >= 3

    md.append("## LLM vs logreg on identical items (C4 regime split)")
    md.append("")
    md.append("| task | llm | llm_acc | logreg_acc | n | both | llm_only | logreg_only | neither | mcnemar_p | verdict |")
    md.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for task, llm_name, X, y, samples in (
        ("MB-8901", "openai__gpt-4o-mini", X1, y1, keep1),
        ("MB-8911", "qwen__qwen3-235b-a22b-2507", X2, y2, s2_sel),
    ):
        at = answer_type(task)
        preds_lr = logreg_oof_binary(X, y.astype(int))
        arch = models[llm_name]
        n_total = 0
        both = c_only = r_only = 0
        for i, s in enumerate(samples):
            r = arch.get((task, s))
            if r is None:
                continue
            try:
                g = gold_value(str(r["answer"]), at)
            except (ValueError, IndexError):
                continue
            n_total += 1
            cp = parse_answer(r.get("raw"), at)
            cc = cp is not None and cp == g
            rc = bool(preds_lr[i]) == (g == "yes")
            if cc and rc:
                both += 1
            elif cc:
                c_only += 1
            elif rc:
                r_only += 1
        p = mcnemar_exact(c_only, r_only)
        llm_acc = (both + c_only) / n_total
        lr_acc = (both + r_only) / n_total
        neither = n_total - both - c_only - r_only
        verdict = "TIE" if (p is None or p >= 0.05) else ("WIN" if c_only > r_only else "LOSS")
        md.append(f"| {task} | {llm_name} | {llm_acc:.4f} | {lr_acc:.4f} | {n_total} | {both} | "
                  f"{c_only} | {r_only} | {neither} | {p if p is None else round(p, 6)} | {verdict} |")
        csv_rows.append(dict(task=task, candidate=llm_name, reference="logreg_gate",
                             n=n_total, cand=round(llm_acc, 4), ref=round(lr_acc, 4),
                             both=both, cand_only=c_only, ref_only=r_only,
                             neither=neither, mcnemar_p=p, verdict=verdict))

    (RESULTS / "c2_significance_89xx.md").write_text("\n".join(md) + "\n")
    import csv as _csv
    with open(RESULTS / "c2_significance_89xx.csv", "w", newline="") as f:
        w = _csv.DictWriter(f, fieldnames=["task", "candidate", "reference", "n", "cand",
                                           "ref", "both", "cand_only", "ref_only",
                                           "neither", "mcnemar_p", "verdict"])
        w.writeheader()
        w.writerows(csv_rows)
    print("\n".join(md))


if __name__ == "__main__":
    main()
