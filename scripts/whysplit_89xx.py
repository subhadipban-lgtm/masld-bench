#!/usr/bin/env python3
"""Why is the MB-89xx binary signal readable? (post-hoc, labeled as such)

1. Univariate per-gene AUROC for 8901/8911 -> top gene identities.
2. Overlap of top genes with the deposit's cell-type Gini marker table
   (hepatocyte_signature_deconvolution.csv).
3. Signal-concentration ablation: OOF logreg accuracy with top-k MAD genes
   (k = 5/10/20/50) vs the full 200 panel.
4. Item-contrast check: does model agreement rise with max|z|?

All classical-only; documents the explanation candidates, does not
pre-register anything.
"""

from __future__ import annotations

import csv
import json
import os
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_mb89xx import (  # noqa: E402
    F_STAGES,
    NAFLD_ETIOLOGIES,
    cpm_log1p_z,
    load_matrix,
    read_ann,
    top_mad_genes,
    zscore_panel,
)
from c2_paired import answer_type, archive_model_name, gold_value, parse_answer, read_jsonl  # noqa: E402
from gates_mb89xx import oof_predict  # noqa: E402

ROOT = Path(os.environ.get("MASLD_LLM_ROOT", Path(__file__).resolve().parents[1]))
DATA = ROOT / "data" / "sbsst1614"
RUNS = ROOT / "results" / "frontier_runs"
SEED = 20260929


def load_symbols() -> dict[str, str]:
    cache = ROOT / "data" / "ensembl_to_symbol_cache.csv"
    out = {}
    if cache.exists():
        with open(cache) as f:
            for row in csv.DictReader(f):
                for k in ("ensembl", "ensembl_gene_id", "ENSG", "gene_id"):
                    if k in row and row.get("symbol") or row.get("gene_symbol"):
                        ens = row.get(k, "")
                        sym = row.get("symbol") or row.get("gene_symbol") or ""
                        if ens and sym:
                            out[ens] = sym
                        break
    return out


def anchor_data():
    s1, g1, m1 = load_matrix(DATA / "htseq_cohort1.txt")
    ann1 = read_ann(DATA / "annotation_cohort1.csv")
    by_id = {r["SMAPLE_RNA"]: r for r in ann1}
    keep1 = [s for s in s1 if s in by_id]
    idx1 = [s1.index(s) for s in keep1]
    t1 = cpm_log1p_z(m1[:, idx1])
    panel1, pidx1 = top_mad_genes(t1, g1)
    X1 = zscore_panel(t1, pidx1).T
    y1 = np.array([int(by_id[s]["fibrosis"]) for s in keep1]) >= 3
    return keep1, panel1, X1, y1


def ext_data():
    s2, g2, m2 = load_matrix(DATA / "htseq_cohort2.txt")
    ann2 = read_ann(DATA / "annotation_cohort2.csv")
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
    return s2_sel, panel2, X2, y2


def load_gini() -> dict[str, dict[str, float]]:
    out = {}
    gini_path = DATA / "hepatocyte_signature_deconvolution.csv"
    with open(gini_path) as f:
        for row in csv.DictReader(f):
            ens = next(iter(row.values()))  # first column holds the ENSG id
            if not ens.startswith("ENSG"):
                continue
            out[ens] = {k: float(v) for k, v in row.items()
                        if k and v and k != ens and v.strip()}
    return out


def main():
    symbols = load_symbols()
    gini = load_gini()
    print(f"gini marker table: {len(gini)} genes; symbols cache: {len(symbols)}")
    report = {}

    for name, get_data in (("8901_anchor", anchor_data), ("8911_ext", ext_data)):
        samples, panel, X, y = get_data()
        print(f"\n== {name}: n={len(y)} pos={y.sum()} ==")
        # univariate AUROC
        aucs = []
        for j, ens in enumerate(panel):
            col = X[:, j]
            if len(set(col)) < 2:
                continue
            try:
                a = roc_auc_score(y, col)
            except ValueError:
                continue
            aucs.append((abs(a - 0.5) * 2, a, ens))
        aucs.sort(reverse=True)
        top = []
        for dev, a, ens in aucs[:20]:
            sym = symbols.get(ens, ens)
            g = gini.get(ens, {})
            top.append(dict(gene=ens, symbol=sym, auc=round(a, 3),
                            deviation=round(dev, 3),
                            celltype_gini={k: round(v, 2) for k, v in g.items()}))
        print("  top-10 genes (|AUC-0.5|):")
        for t in top[:10]:
            print(f"    {t['symbol']:12s} auc {t['auc']:.3f} dev {t['deviation']:.3f} "
                  f"gini {t['celltype_gini']}")
        report[name] = dict(pos=int(y.sum()), neg=int((~y).sum()), top_genes=top)

        # how many top-20 genes are known cell-type markers (any Gini >= 0.9)?
        n_marker = sum(1 for t in top if any(v >= 0.9 for v in t["celltype_gini"].values()))
        n_hep = sum(1 for t in top if t["celltype_gini"].get("Hepatocytes-gini", 0) >= 0.9)
        print(f"  top-20: {n_marker} strong cell-type markers, {n_hep} hepatocyte markers")
        report[name]["n_markers_top20"] = n_marker
        report[name]["n_hepatocyte_markers_top20"] = n_hep

        # signal-concentration ablation
        devs = []
        for j, ens in enumerate(panel):
            col = X[:, j]
            try:
                a = roc_auc_score(y, col)
            except ValueError:
                a = 0.5
            devs.append((abs(a - 0.5), j))
        devs.sort(reverse=True)
        ab = {}
        for k in (5, 10, 20, 50, 200):
            idx = [j for _, j in devs[:min(k, len(devs))]]
            preds = oof_predict(X[:, idx], y.astype(int),
                                lambda: LogisticRegression(max_iter=3000, C=1.0))
            ab[k] = round(float(np.mean(preds == y)), 4)
        print("  ablation (top-k informative genes, OOF acc):", ab)
        report[name]["ablation_topk_acc"] = ab

        # MAD-panel sanity: full 200-panel OOF (the frozen gate number)
        preds = oof_predict(X, y.astype(int), lambda: LogisticRegression(max_iter=3000, C=1.0))
        report[name]["full_panel_oof"] = round(float(np.mean(preds == y)), 4)

    # item-contrast check: max|z| vs agreement between best LLM and logreg
    print("\n== item-contrast check (anchor) ==")
    samples, panel, X, y = anchor_data()
    preds_lr = oof_predict(X, y.astype(int), lambda: LogisticRegression(max_iter=3000, C=1.0))
    arch = None
    for p in sorted(RUNS.glob("openai__gpt-4o-mini__MB-89xx.jsonl.gz")):
        arch = {(r["task"], r["sample"]): r for r in read_jsonl(p) if "__meta__" not in r}
    at = answer_type("MB-8901")
    agree, maxz = [], []
    for i, s in enumerate(samples):
        r = arch.get(("MB-8901", s))
        if r is None:
            continue
        try:
            g = gold_value(str(r["answer"]), at)
        except (ValueError, IndexError):
            continue
        cp = parse_answer(r.get("raw"), at)
        if cp is None:
            continue
        llm_ok = cp == g
        lr_ok = bool(preds_lr[i]) == (g == "yes")
        agree.append(1.0 if llm_ok == lr_ok else 0.0)
        maxz.append(float(np.max(np.abs(X[i]))))
    rho = spearmanr(maxz, agree).statistic
    lo = np.mean([a for a, z in zip(agree, maxz) if z < np.median(maxz)])
    hi = np.mean([a for a, z in zip(agree, maxz) if z >= np.median(maxz)])
    print(f"  LLM-logreg agreement: low-maxz items {lo:.3f} vs high-maxz items {hi:.3f}; "
          f"spearman(maxz, agree) = {rho:.3f}")
    report["contrast_anchor"] = dict(agree_low_maxz=round(lo, 3),
                                     agree_high_maxz=round(hi, 3),
                                     spearman=round(rho, 3))

    out = ROOT / "results" / "whysplit_89xx.json"
    out.write_text(json.dumps(report, indent=1))
    print(f"\n-> {out}")


if __name__ == "__main__":
    main()
