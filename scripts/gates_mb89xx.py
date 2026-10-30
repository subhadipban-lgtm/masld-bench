#!/usr/bin/env python3
"""Classical gates for MB-89xx (per ANALYSIS_PLAN_MB89xx §9, frozen 2026-10-29).

logreg + HGB on the SAME features the prompts carry (panel top-200 MAD,
CPM->log1p->per-sample z, reconstructed exactly as build_mb89xx.py), grouped
CV (samples are unique per corpus), 2000 bootstraps, seed 20260929.

Gates: binary/5-class must beat chance AND majority; ordinal must beat
median MAE. Also emits the AMC-vs-UZA label-noise readout: the same trained
models scored against both golds on the 108 AMC-staged samples.

Outputs: results/gates_mb89xx.json + results/gates_mb89xx.md
"""

from __future__ import annotations

import json
import os
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.model_selection import StratifiedKFold

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

ROOT = Path(os.environ.get("MASLD_LLM_ROOT", Path(__file__).resolve().parents[1]))
DATA = ROOT / "data" / "sbsst1614"
RESULTS = ROOT / "results"
SEED = 20260929
N_BOOT = 2000


def bootstrap_ci(vals, n=N_BOOT, seed=SEED):
    rng = np.random.default_rng(seed)
    vals = np.asarray(vals, dtype=float)
    idx = rng.integers(0, len(vals), size=(n, len(vals)))
    means = vals[idx].mean(axis=1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def oof_predict(X, y, clf_factory, n_splits=5):
    """Pooled stratified out-of-fold predictions (deterministic split seed)."""
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=SEED)
    preds = np.empty(len(y), dtype=float)
    for tr, te in skf.split(X, y):
        clf = clf_factory()
        clf.fit(X[tr], y[tr])
        preds[te] = clf.predict(X[te])
    return preds


def gate_classification(name, X, y, majority):
    out = {}
    for mname, factory in [
        ("logreg", lambda: LogisticRegression(max_iter=3000, C=1.0)),
        ("hgb", lambda: HistGradientBoostingClassifier(random_state=SEED)),
    ]:
        preds = oof_predict(X, y, factory)
        acc = float(np.mean(preds == y))
        lo, hi = bootstrap_ci((preds == y).astype(float))
        n_class = len(set(y))
        chance = 1.0 / n_class
        out[mname] = dict(
            acc=round(acc, 4), ci=[round(lo, 4), round(hi, 4)],
            chance=chance, majority=round(majority, 4),
            beats_chance=lo > chance, beats_majority=lo > majority,
        )
    print(f"  {name}: " + " | ".join(
        f"{k} acc {v['acc']} [{v['ci'][0]},{v['ci'][1]}] vs maj {v['majority']}"
        for k, v in out.items()))
    return out


def gate_regression(name, X, y, median_mae):
    out = {}
    for mname, factory in [
        ("logreg", lambda: Ridge(alpha=1.0)),
        ("hgb", lambda: HistGradientBoostingRegressor(random_state=SEED)),
    ]:
        # regression has no stratification axis; use the same split scheme
        skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
        preds = np.empty(len(y), dtype=float)
        for tr, te in skf.split(X, y):
            reg = factory()
            reg.fit(X[tr], y[tr])
            preds[te] = np.clip(np.round(reg.predict(X[te])), 0, 4)
        mae = float(np.mean(np.abs(preds - y)))
        lo, hi = bootstrap_ci(np.abs(preds - y))
        rho = float(spearmanr(preds, y).statistic) if len(set(preds)) > 1 and len(set(y)) > 1 else None
        out[mname] = dict(
            mae=round(mae, 4), ci=[round(lo, 4), round(hi, 4)],
            median_mae=round(median_mae, 4), beats_median=lo < median_mae,
            rho=round(rho, 4) if rho is not None else None,
        )
    print(f"  {name}: " + " | ".join(
        f"{k} MAE {v['mae']} [{v['ci'][0]},{v['ci'][1]}] vs median {v['median_mae']}"
        for k, v in out.items()))
    return out


def main():
    if not (DATA / "htseq_cohort1.txt").exists():
        raise SystemExit(f"source data missing under {DATA}")
    report = {}

    # ---- cohort 1 anchor (112) ----
    s1, g1, m1 = load_matrix(DATA / "htseq_cohort1.txt")
    ann1 = read_ann(DATA / "annotation_cohort1.csv")
    by_id = {r["SMAPLE_RNA"]: r for r in ann1}
    keep1 = [s for s in s1 if s in by_id]  # drops unannotated RNA015845
    idx1 = [s1.index(s) for s in keep1]
    t1 = cpm_log1p_z(m1[:, idx1])
    panel1, pidx1 = top_mad_genes(t1, g1)
    X1 = zscore_panel(t1, pidx1).T  # samples x genes
    y1_uza = np.array([int(by_id[s]["fibrosis"]) for s in keep1])
    y1_amc_ok = np.array([s in keep1 and by_id[s]["fibrosis_AMC"] in {"0", "1", "2", "3", "4"}
                          for s in keep1])
    y1_amc = np.array([int(by_id[s]["fibrosis_AMC"]) if ok else -1
                       for s, ok in zip(keep1, y1_amc_ok)])
    maj1 = max(Counter(y1_uza).values()) / len(y1_uza)
    median1 = float(np.median(y1_uza))

    print("== anchor (n=%d): binary / 5-class / ordinal, UZA gold ==" % len(keep1))
    report["8901_anchor_binary"] = gate_classification(
        "MB-8901", X1, (y1_uza >= 3).astype(int), maj1)
    report["8902_anchor_5class"] = gate_classification("MB-8902", X1, y1_uza, maj1)
    report["8905_anchor_ordinal"] = gate_regression("MB-8905", X1, y1_uza, median1)

    # AMC-gold readout on the same trained features (label-noise cap)
    amc_mask = y1_amc_ok
    if amc_mask.sum() >= 2:
        print(f"== AMC-gold readout (n={amc_mask.sum()}) ==")
        Xa, yu, ya = X1[amc_mask], y1_uza[amc_mask], y1_amc[amc_mask]
        maj_a = max(Counter(ya).values()) / len(ya)
        report["8921_amc_binary"] = gate_classification("MB-8921", Xa, (ya >= 3).astype(int), maj_a)
        report["8922_amc_5class"] = gate_classification("MB-8922", Xa, ya, maj_a)
        report["8925_amc_ordinal"] = gate_regression("MB-8925", Xa, ya, float(np.median(ya)))
        # label-noise cap: logreg predictions scored against BOTH golds
        preds_uza = oof_predict(Xa, yu, lambda: LogisticRegression(max_iter=3000, C=1.0))
        acc_uza = float(np.mean(preds_uza == yu))
        acc_amc = float(np.mean(preds_uza == ya))
        report["label_noise_logreg"] = dict(
            acc_vs_uza=round(acc_uza, 4), acc_vs_amc=round(acc_amc, 4),
            gap=round(acc_uza - acc_amc, 4))

    # ---- cohort 2 extension (179) ----
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
    y2 = np.array([F_STAGES[r["Fibrosis"]] for r in kept2])
    maj2 = max(Counter(y2).values()) / len(y2)

    print(f"== extension (n={len(kept2)}): binary / 5-class / ordinal, clinical-consensus gold ==")
    report["8911_ext_binary"] = gate_classification(
        "MB-8911", X2, (y2 >= 3).astype(int), maj2)
    report["8912_ext_5class"] = gate_classification("MB-8912", X2, y2, maj2)
    report["8915_ext_ordinal"] = gate_regression("MB-8915", X2, y2, float(np.median(y2)))

    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "gates_mb89xx.json").write_text(json.dumps(report, indent=1))
    md = ["# MB-89xx classical gates (2026-10-29, frozen §9)",
          "",
          "logreg + HGB, stratified 5-fold OOF (seed 20260929), 2000 bootstraps. "
          "Features = the prompt panel (top-200 MAD, CPM->log1p->z).",
          ""]
    for k, v in report.items():
        md.append(f"## {k}\n```json\n{json.dumps(v, indent=1)}\n```")
    (RESULTS / "gates_mb89xx.md").write_text("\n".join(md) + "\n")
    print(f"\n-> {RESULTS / 'gates_mb89xx.json'} / .md")


if __name__ == "__main__":
    main()
