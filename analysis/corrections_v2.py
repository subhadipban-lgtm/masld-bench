#!/usr/bin/env python3
"""
Second-round corrections, addressing the 10 November review.

Defects repaired here
---------------------
1. The "fully inductive" analysis was still transductive: the fold panel was
   intersected with a corpus-wide panel. Now genes are chosen from training
   samples only and read directly from the raw matrix.
2. The anchor->extension "transfer" indexed columns, not genes. Each cohort has
   its own MAD panel, so the same column held different genes (5/5 mismatched,
   panel overlap 9/200). Now aligned by Ensembl identifier and transformed with
   anchor-frozen moments.
3. The ordinal correction replaced Ridge/HGBRegressor with LogisticRegression/
   HGBClassifier. The original estimator families are restored.
4. Paired tests dropped invalid answers. Invalid is now a model error, so an
   invalid answer on a gold-negative item is a loss against always-"no".

Outputs: analysis/v2_*.json
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
from scipy.stats import binomtest
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold

ROOT = Path(os.environ.get(
    "MASLD_DATA_ROOT",
    os.environ.get("MASLD_LLM_ROOT", Path(__file__).resolve().parents[1]),
))
OUT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "sbsst1614"
RUNS = ROOT / "results" / "frontier_runs"
SEED = 20260929
N_BOOT = 2000
sys.path.insert(0, str(ROOT / "scripts"))
from build_mb89xx import (  # noqa: E402
    F_STAGES, NAFLD_ETIOLOGIES, cpm_log1p_z, load_matrix, read_ann,
)
from c2_paired import parse_yes_no  # noqa: E402


def stage_value(raw):
    """Production stage parser: integer 0-4 only; everything else is rejected.

    Returns (value, reason). reason is None on success.
    """
    from c2_paired import parse_number
    if raw is None or not str(raw).strip():
        return None, "empty"
    v = parse_number(str(raw))
    if v is None:
        return None, "unparseable"
    if not np.isfinite(v):
        return None, "non_finite"
    if float(v) != int(v):
        return None, "non_integer"
    if v < 0 or v > 4:
        return None, "out_of_domain"
    return int(v), None


def paired_counts(gold, pred):
    """Discordance counts for a model versus the always-negative baseline.

    pred None means invalid, which counts as a model error (invalid-as-error).
    Returns (model_wins, baseline_wins).
    """
    wins = losses = 0
    for g, p in zip(gold, pred):
        model_correct = (p is not None) and (int(p) == int(g))
        base_correct = (int(g) == 0)
        if model_correct and not base_correct:
            wins += 1
        elif base_correct and not model_correct:
            losses += 1
    return wins, losses


def holm_adjust(pvals):
    """Holm-Bonferroni adjusted p-values, monotone and bounded at 1."""
    p = list(pvals)
    m = len(p)
    order = np.argsort(p)
    adj = np.empty(m)
    run = 0.0
    for rank, i in enumerate(order):
        run = max(run, min(1.0, (m - rank) * p[i]))
        adj[i] = run
    return adj


def boot_ci(vals, n=N_BOOT, seed=SEED):
    rng = np.random.default_rng(seed)
    v = np.asarray(vals, float)
    idx = rng.integers(0, len(v), size=(n, len(v)))
    m = v[idx].mean(axis=1)
    return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def mad_genes_raw(t_train, gene_ids, k=200):
    """Top-k MAD genes computed on TRAINING columns only."""
    mad = np.median(np.abs(t_train - np.median(t_train, axis=1, keepdims=True)), axis=1)
    idx = np.argsort(mad)[::-1][:k]
    return idx, [gene_ids[i] for i in idx]


def z_gene_train(t_train, t_test, idx):
    """Per-gene standardisation with moments estimated on training samples only."""
    tr = t_train[idx]
    te = t_test[idx]
    mu = tr.mean(axis=1, keepdims=True)
    sd = np.maximum(tr.std(axis=1, keepdims=True), 1e-12)
    return ((tr - mu) / sd).T, ((te - mu) / sd).T


def z_sample(t_train, t_test, idx):
    """Per-sample standardisation: uses only within-sample statistics."""
    def f(t):
        s = t[idx]
        return ((s - s.mean(axis=0, keepdims=True)) /
                np.maximum(s.std(axis=0, keepdims=True), 1e-12)).T
    return f(t_train), f(t_test)


def fold_metrics_raw(t_raw, genes, y, mode):
    """OOF accuracy under a chosen preprocessing contract.

    mode 'gene' : train-only MAD panel + train-only per-gene moments
    mode 'sample': train-only MAD panel + per-sample standardisation
    """
    skf = StratifiedKFold(5, shuffle=True, random_state=SEED)
    pred = np.empty(len(y), dtype=int)
    chosen = []
    for tr, te in skf.split(t_raw.T, y):
        idx, fold_genes = mad_genes_raw(t_raw[:, tr], genes, k=min(200, len(genes)))
        chosen.append(fold_genes)
        if mode == "gene":
            Xtr, Xte = z_gene_train(t_raw[:, tr], t_raw[:, te], idx)
        else:
            Xtr, Xte = z_sample(t_raw[:, tr], t_raw[:, te], idx)
        m = LogisticRegression(max_iter=3000, C=1.0).fit(Xtr, y[tr])
        pred[te] = m.predict(Xte)
    acc = (pred == y).astype(float)
    lo, hi = boot_ci(acc)
    # leakage audit: genes chosen per fold must all be real, and folds must differ
    return dict(accuracy=float(acc.mean()), ci=[lo, hi],
                n=int(len(y)), n_selected=[len(c) for c in chosen],
                folds_distinct=len({tuple(c) for c in chosen}))


def align_genes(anchor_genes, ext_genes, anchor_index, ext_index):
    """Map anchor panel positions to extension positions by gene identity.

    Returns (shared_names, anchor_cols, ext_cols). Raises if any requested
    alignment would be positional rather than identity-based.
    """
    out_names, a_cols, e_cols = [], [], []
    for name in anchor_genes:
        if name in ext_index and name in anchor_index:
            out_names.append(name)
            a_cols.append(anchor_index[name])
            e_cols.append(ext_index[name])
    assert len(out_names) == len(a_cols) == len(e_cols)
    for n, a, e in zip(out_names, a_cols, e_cols):
        assert anchor_genes[a_cols.index(a)] == n
        assert ext_genes[e] == n, f"gene misalignment at {n}"
    return out_names, a_cols, e_cols


def load_cohorts():
    s1, g1, m1 = load_matrix(DATA / "htseq_cohort1.txt")
    a1 = read_ann(DATA / "annotation_cohort1.csv")
    by1 = {r["SMAPLE_RNA"]: r for r in a1}
    keep1 = [s for s in s1 if s in by1]
    t1 = cpm_log1p_z(m1[:, [s1.index(s) for s in keep1]])
    y1 = np.array([int(by1[s]["fibrosis"]) for s in keep1])

    s2, g2, m2 = load_matrix(DATA / "htseq_cohort2.txt")
    a2 = read_ann(DATA / "annotation_cohort2.csv")
    sub = [r for r in a2 if r.get("Etiology") in NAFLD_ETIOLOGIES]
    bys = {}
    for r in sub:
        bys.setdefault(r["Subject_ID"], []).append(r)
    kept = [([r for r in rs if r.get("Visit_Type") == "Baseline"] or rs)[0]
            for rs in bys.values()]
    kept = [r for r in kept if r.get("Fibrosis") in F_STAGES]
    t2 = cpm_log1p_z(m2[:, [s2.index(r["SMAPLE_RNA"]) for r in kept]])
    y2 = np.array([F_STAGES[r["Fibrosis"]] for r in kept])
    return (t1, g1, y1), (t2, g2, y2)


def part1_inductive():
    (t1, g1, y1), (t2, g2, y2) = load_cohorts()
    res = {}
    for name, t, g, y in (("MB-8901", t1, g1, (y1 >= 3).astype(int)),
                          ("MB-8911", t2, g2, (y2 >= 3).astype(int))):
        res[name] = {
            "gene_wise_train_moments": fold_metrics_raw(t, g, y, "gene"),
            "per_sample": fold_metrics_raw(t, g, y, "sample"),
            "majority": float(max(np.bincount(y)) / len(y)),
            "n": int(len(y)),
        }
    return res


def part2_transfer():
    """Gene-aligned transfer: align by Ensembl ID, freeze the anchor transform."""
    (t1, g1, y1), (t2, g2, y2) = load_cohorts()
    yb1 = (y1 >= 3).astype(int)
    yb2 = (y2 >= 3).astype(int)
    g1i = {g: i for i, g in enumerate(g1)}
    g2i = {g: i for i, g in enumerate(g2)}

    # anchor-only panel: top-5 by |AUC-0.5| on the anchor, gene-wise z (anchor moments)
    idx_all, _ = mad_genes_raw(t1, g1, k=min(200, len(g1)))
    mu = t1[idx_all].mean(axis=1, keepdims=True)
    sd = np.maximum(t1[idx_all].std(axis=1, keepdims=True), 1e-12)
    Z1 = (t1[idx_all] - mu) / sd
    aucs = [(abs(roc_auc_score(yb1, Z1[k]) - 0.5), k) for k in range(len(idx_all))]
    top = [k for _, k in sorted(aucs, reverse=True)[:5]]
    anchor_genes = [g1[idx_all[k]] for k in top]

    shared = [g for g in anchor_genes if g in g2i]
    dropped = [g for g in anchor_genes if g not in g2i]

    if len(shared) < 2:
        return dict(error="fewer than two anchor genes present in the extension matrix",
                    anchor_genes=anchor_genes, dropped=dropped)

    # rebuild using only shared genes, moments frozen on the anchor
    a_idx = [g1i[g] for g in shared]
    e_idx = [g2i[g] for g in shared]
    mu_a = t1[a_idx].mean(axis=1, keepdims=True)
    sd_a = np.maximum(t1[a_idx].std(axis=1, keepdims=True), 1e-12)
    Xa = ((t1[a_idx] - mu_a) / sd_a).T
    Xe = ((t2[e_idx] - mu_a) / sd_a).T   # anchor moments applied unchanged

    model = LogisticRegression(max_iter=3000, C=1.0).fit(Xa, yb1)
    train_acc = float((model.predict(Xa) == yb1).mean())
    ext_pred = model.predict(Xe)
    ext_acc = float((ext_pred == yb2).mean())
    correct = (ext_pred == yb2).astype(float)
    lo, hi = boot_ci(correct)

    # anchor held-out estimate on the same gene set
    skf = StratifiedKFold(5, shuffle=True, random_state=SEED)
    oof = np.empty(len(yb1), dtype=int)
    for tr, te in skf.split(Xa, yb1):
        m = LogisticRegression(max_iter=3000, C=1.0).fit(Xa[tr], yb1[tr])
        oof[te] = m.predict(Xa[te])
    anchor_oof = float((oof == yb1).mean())

    # extension internal baseline on the same genes, for context
    skf2 = StratifiedKFold(5, shuffle=True, random_state=SEED)
    oof2 = np.empty(len(yb2), dtype=int)
    for tr, te in skf2.split(Xe, yb2):
        m = LogisticRegression(max_iter=3000, C=1.0).fit(Xe[tr], yb2[tr])
        oof2[te] = m.predict(Xe[te])
    ext_internal = float((oof2 == yb2).mean())

    return dict(
        note="genes aligned by Ensembl ID; anchor moments frozen and applied to the extension; "
             "train accuracy is resubstitution and is reported separately from external accuracy",
        anchor_genes=anchor_genes, shared_genes=shared, dropped_genes=dropped,
        n_shared=len(shared),
        anchor_train_resubstitution=train_acc,
        anchor_out_of_fold=anchor_oof,
        extension_external_accuracy=ext_acc,
        extension_external_ci=[lo, hi],
        extension_majority=float(max(np.bincount(yb2)) / len(yb2)),
        extension_n=int(len(yb2)),
        extension_internal_oof=ext_internal,
        extension_sensitivity=float(ext_pred[yb2 == 1].mean()),
        extension_specificity=float((ext_pred[yb2 == 0] == 0).mean()),
    )


def part2b_nested_panel():
    """Nested validation of the five-gene panel procedure within the anchor.

    part2_transfer reports a *conditional* CV: the panel is chosen once using all
    anchor labels, then only the classifier is cross-validated. That is not an
    unbiased estimate of the selection procedure. Here MAD selection, supervised
    ranking and scaling are all repeated inside each training fold.
    """
    (t1, g1, y1), (t2, g2, y2) = load_cohorts()
    yb = (y1 >= 3).astype(int)
    skf = StratifiedKFold(5, shuffle=True, random_state=SEED)
    pred = np.empty(len(yb), dtype=int)
    chosen = []
    for tr, te in skf.split(t1.T, yb):
        idx, genes = mad_genes_raw(t1[:, tr], g1, k=min(200, len(g1)))
        mu = t1[:, tr][idx].mean(axis=1, keepdims=True)
        sd = np.maximum(t1[:, tr][idx].std(axis=1, keepdims=True), 1e-12)
        Ztr = (t1[:, tr][idx] - mu) / sd
        Zte = (t1[:, te][idx] - mu) / sd
        aucs = [(abs(roc_auc_score(yb[tr], Ztr[k]) - 0.5), k) for k in range(len(idx))]
        top = [k for _, k in sorted(aucs, reverse=True)[:5]]
        chosen.append([genes[k] for k in top])
        m = LogisticRegression(max_iter=3000, C=1.0).fit(Ztr[top].T, yb[tr])
        pred[te] = m.predict(Zte[top].T)
    acc = (pred == yb).astype(float)
    lo, hi = boot_ci(acc)
    conditional = part2_transfer_conditional()
    return dict(
        nested_panel_selection_accuracy=float(acc.mean()),
        nested_ci=[lo, hi],
        majority=float(max(np.bincount(yb)) / len(yb)),
        n=int(len(yb)),
        folds_distinct=len({tuple(c) for c in chosen}),
        selected_genes_per_fold=chosen,
        conditional_fixed_panel=conditional,
        note="nested repeats MAD selection, supervised ranking and scaling inside each "
             "training fold; conditional reuses one panel chosen on all anchor labels",
    )


def part2_transfer_conditional():
    (t1, g1, y1), (t2, g2, y2) = load_cohorts()
    yb = (y1 >= 3).astype(int)
    idx, _ = mad_genes_raw(t1, g1, k=min(200, len(g1)))
    mu = t1[idx].mean(axis=1, keepdims=True)
    sd = np.maximum(t1[idx].std(axis=1, keepdims=True), 1e-12)
    Z = (t1[idx] - mu) / sd
    aucs = [(abs(roc_auc_score(yb, Z[k]) - 0.5), k) for k in range(len(idx))]
    top = [k for _, k in sorted(aucs, reverse=True)[:5]]
    skf = StratifiedKFold(5, shuffle=True, random_state=SEED)
    pred = np.empty(len(yb), dtype=int)
    for tr, te in skf.split(Z[top].T, yb):
        m = LogisticRegression(max_iter=3000, C=1.0).fit(Z[top][:, tr].T, yb[tr])
        pred[te] = m.predict(Z[top][:, te].T)
    return float((pred == yb).mean()), [g1[idx[k]] for k in top]


def part2c_transfer_paired():
    """Paired comparison of the gene-aligned external panel against always-no.

    A marginal accuracy interval that excludes a fixed observed majority rate is
    not the same procedure as a paired test against the majority classifier.
    """
    (t1, g1, y1), (t2, g2, y2) = load_cohorts()
    yb1 = (y1 >= 3).astype(int)
    yb2 = (y2 >= 3).astype(int)
    g1i = {g: i for i, g in enumerate(g1)}
    g2i = {g: i for i, g in enumerate(g2)}
    idx, _ = mad_genes_raw(t1, g1, k=min(200, len(g1)))
    mu = t1[idx].mean(axis=1, keepdims=True)
    sd = np.maximum(t1[idx].std(axis=1, keepdims=True), 1e-12)
    Z1 = (t1[idx] - mu) / sd
    aucs = [(abs(roc_auc_score(yb1, Z1[k]) - 0.5), k) for k in range(len(idx))]
    top = [k for _, k in sorted(aucs, reverse=True)[:5]]
    genes = [g1[idx[k]] for k in top]
    shared = [g for g in genes if g in g2i]
    a_idx = [g1i[g] for g in shared]
    e_idx = [g2i[g] for g in shared]
    mu_a = t1[a_idx].mean(axis=1, keepdims=True)
    sd_a = np.maximum(t1[a_idx].std(axis=1, keepdims=True), 1e-12)
    Xa = ((t1[a_idx] - mu_a) / sd_a).T
    Xe = ((t2[e_idx] - mu_a) / sd_a).T
    model = LogisticRegression(max_iter=3000, C=1.0).fit(Xa, yb1)
    pred = model.predict(Xe)
    model_correct = (pred == yb2)
    base_correct = np.ones(len(yb2), dtype=bool) & (yb2 == 0)   # always-no is correct on negatives
    wins = int((model_correct & ~base_correct).sum())
    losses = int((~model_correct & base_correct).sum())
    p = float(binomtest(min(wins, losses), wins + losses, 0.5).pvalue)
    diff = model_correct.astype(float) - base_correct.astype(float)
    lo, hi = boot_ci(diff)
    return dict(
        n=int(len(yb2)), model_wins=wins, baseline_wins=losses,
        p_exact=p,
        paired_accuracy_difference=float(diff.mean()),
        paired_difference_ci=[lo, hi],
        marginal_accuracy=float(model_correct.mean()),
        majority_rate=float(max(np.bincount(yb2)) / len(yb2)),
        note="paired McNemar over the same extension subjects; a marginal interval "
             "excluding the fixed majority rate is a different procedure and can "
             "disagree with this test",
    )


def part3_ordinal():
    """Reproduce the ORIGINAL estimators: Ridge and HistGradientBoostingRegressor."""
    (t1, g1, y1), (t2, g2, y2) = load_cohorts()

    def gate(t, g, y, name):
        idx, _ = mad_genes_raw(t, g, k=min(200, len(g)))
        mu = t[idx].mean(axis=1, keepdims=True)
        sd = np.maximum(t[idx].std(axis=1, keepdims=True), 1e-12)
        X = ((t[idx] - mu) / sd).T
        out = {}
        base = {}
        skf = StratifiedKFold(5, shuffle=True, random_state=SEED)
        med_pred = np.empty(len(y), float)
        for tr, te in skf.split(X, y):
            med_pred[te] = np.median(y[tr])
        for mname, factory in (("ridge", lambda: Ridge(alpha=1.0)),
                               ("hgb_regressor", lambda: HistGradientBoostingRegressor(random_state=SEED))):
            skf = StratifiedKFold(5, shuffle=True, random_state=SEED)
            rounded = np.empty(len(y), float)
            raw = np.empty(len(y), float)
            for tr, te in skf.split(X, y):
                reg = factory().fit(X[tr], y[tr])
                p = reg.predict(X[te])
                raw[te] = p
                rounded[te] = np.clip(np.round(p), 0, 4)
            for label, pred in (("as_specified_rounded", rounded), ("continuous", raw)):
                err = np.abs(pred - y)
                med_err = np.abs(med_pred - y)
                diff = med_err - err
                lo, hi = boot_ci(diff)
                out[f"{mname}_{label}"] = dict(
                    mae=float(err.mean()),
                    constant_mae=float(med_err.mean()),
                    paired_diff=float(diff.mean()),
                    ci=[lo, hi],
                    beats_constant=bool(lo > 0),
                )
        return out

    # AMC reader cohort: 108 jointly staged samples, AMC gold
    s1, g1_, m1 = load_matrix(DATA / "htseq_cohort1.txt")
    a1 = read_ann(DATA / "annotation_cohort1.csv")
    by1 = {r["SMAPLE_RNA"]: r for r in a1}
    keep1 = [x for x in s1 if x in by1]
    t1_full = cpm_log1p_z(m1[:, [s1.index(x) for x in keep1]])
    amc = []
    for x in keep1:
        v = str(by1[x]["fibrosis_AMC"]).strip()
        amc.append(-1 if v in {"", "NA", "na", "nan", "None"} else int(float(v)))
    amc = np.array(amc)
    joint = amc >= 0
    t_amc = t1_full[:, joint]

    return {
        "MB-8905": gate(t1, g1, y1, "MB-8905"),
        "MB-8915": gate(t2, g2, y2, "MB-8915"),
        "MB-8925": gate(t_amc, g1, amc[joint], "MB-8925"),
        "note": "estimators restored to Ridge(alpha=1.0) and HistGradientBoostingRegressor, "
                "matching scripts/gates_mb89xx.py:91-92; both the as-specified rounded "
                "predictions and the untransformed continuous predictions are reported; "
                "MB-8925 uses the 108 jointly staged samples with the AMC gold",
    }


def _amc_joint():
    s1, g1, m1 = load_matrix(DATA / "htseq_cohort1.txt")
    a1 = read_ann(DATA / "annotation_cohort1.csv")
    by1 = {r["SMAPLE_RNA"]: r for r in a1}
    keep1 = [x for x in s1 if x in by1]
    t1 = cpm_log1p_z(m1[:, [s1.index(x) for x in keep1]])
    amc = []
    for x in keep1:
        v = str(by1[x]["fibrosis_AMC"]).strip()
        amc.append(-1 if v in {"", "NA", "na", "nan", "None"} else int(float(v)))
    amc = np.array(amc)
    return t1, g1, amc, amc >= 0


def part3b_amc_original_contract():
    """MB-8925 evaluated exactly as the original script did.

    scripts/gates_mb89xx.py builds the panel and gene-wise moments on all 112
    anchor samples, then subsets that feature matrix to the 108 AMC-staged rows
    (`Xa = X1[amc_mask]`). The panel is therefore a 112-sample panel, not a
    108-sample panel. This function reproduces that contract.
    """
    t1, g1, amc, joint = _amc_joint()
    idx, _ = mad_genes_raw(t1, g1, k=min(200, len(g1)))
    mu = t1[idx].mean(axis=1, keepdims=True)
    sd = np.maximum(t1[idx].std(axis=1, keepdims=True), 1e-12)
    X1 = ((t1[idx] - mu) / sd).T          # 112 x 200, moments from all 112
    Xa = X1[joint]                        # subset rows to the 108 AMC samples
    y = amc[joint]

    skf = StratifiedKFold(5, shuffle=True, random_state=SEED)
    med = np.empty(len(y), float)
    for tr, te in skf.split(Xa, y):
        med[te] = np.median(y[tr])
    out = {"n": int(len(y)), "panel_source_n": int(X1.shape[0]),
           "constant_mae": float(np.mean(np.abs(med - y))),
           "feature_contract": "panel and gene-wise moments from all 112 anchor samples, "
                               "rows subset to the 108 AMC-staged samples"}
    for name, factory in (("ridge", lambda: Ridge(alpha=1.0)),
                          ("hgb_regressor", lambda: HistGradientBoostingRegressor(random_state=SEED))):
        skf = StratifiedKFold(5, shuffle=True, random_state=SEED)
        rnd = np.empty(len(y), float)
        raw = np.empty(len(y), float)
        for tr, te in skf.split(Xa, y):
            reg = factory().fit(Xa[tr], y[tr])
            p = reg.predict(Xa[te])
            raw[te] = p
            rnd[te] = np.clip(np.round(p), 0, 4)
        for label, pred in (("as_specified_rounded", rnd), ("continuous", raw)):
            err = np.abs(pred - y)
            diff = np.abs(med - y) - err
            lo, hi = boot_ci(diff)
            out[f"{name}_{label}"] = dict(
                mae=float(err.mean()), paired_diff=float(diff.mean()),
                ci=[lo, hi], beats_constant=bool(lo > 0))
    return out


def part7_nested_topk():
    """Top-k accuracy with bootstrap intervals, under three preprocessing contracts.

    legacy        ranking outside CV, corpus-wide panel and scaling
    rank_nested   ranking inside CV, corpus-wide panel and scaling held fixed
    fully_nested  MAD panel, ranking and scaling all inside each training fold
    """
    (t1, g1, y1), _ = load_cohorts()
    yb = (y1 >= 3).astype(int)
    ks = (5, 10, 20, 50, 200)
    out = {"k": list(ks), "majority": float(max(np.bincount(yb)) / len(yb)),
           "contracts": {c: {} for c in ("legacy", "rank_nested", "fully_nested")}}

    def record(contract, k, pred, y):
        correct = (pred == y).astype(float)
        lo, hi = boot_ci(correct)
        out["contracts"][contract][str(k)] = dict(
            accuracy=float(correct.mean()), ci=[lo, hi], n=int(len(y)))

    idx_all, _ = mad_genes_raw(t1, g1, k=min(200, len(g1)))
    mu = t1[idx_all].mean(axis=1, keepdims=True)
    sd = np.maximum(t1[idx_all].std(axis=1, keepdims=True), 1e-12)
    Z = ((t1[idx_all] - mu) / sd).T

    for k in ks:
        aucs = [(abs(roc_auc_score(yb, Z[:, j]) - 0.5), j) for j in range(Z.shape[1])]
        cols = [j for _, j in sorted(aucs, reverse=True)[:k]]
        skf = StratifiedKFold(5, shuffle=True, random_state=SEED)
        pred = np.empty(len(yb), dtype=int)
        for tr, te in skf.split(Z[:, cols], yb):
            m = LogisticRegression(max_iter=3000, C=1.0).fit(Z[tr][:, cols], yb[tr])
            pred[te] = m.predict(Z[te][:, cols])
        record("legacy", k, pred, yb)

        skf = StratifiedKFold(5, shuffle=True, random_state=SEED)
        pred = np.empty(len(yb), dtype=int)
        for tr, te in skf.split(Z, yb):
            a = [(abs(roc_auc_score(yb[tr], Z[tr, j]) - 0.5), j) for j in range(Z.shape[1])]
            c = [j for _, j in sorted(a, reverse=True)[:k]]
            m = LogisticRegression(max_iter=3000, C=1.0).fit(Z[tr][:, c], yb[tr])
            pred[te] = m.predict(Z[te][:, c])
        record("rank_nested", k, pred, yb)

        skf = StratifiedKFold(5, shuffle=True, random_state=SEED)
        pred = np.empty(len(yb), dtype=int)
        for tr, te in skf.split(t1.T, yb):
            fidx, _ = mad_genes_raw(t1[:, tr], g1, k=min(200, len(g1)))
            m_ = t1[:, tr][fidx].mean(axis=1, keepdims=True)
            s_ = np.maximum(t1[:, tr][fidx].std(axis=1, keepdims=True), 1e-12)
            Ztr = ((t1[:, tr][fidx] - m_) / s_).T
            Zte = ((t1[:, te][fidx] - m_) / s_).T
            a = [(abs(roc_auc_score(yb[tr], Ztr[:, j]) - 0.5), j) for j in range(Ztr.shape[1])]
            c = [j for _, j in sorted(a, reverse=True)[:k]]
            m = LogisticRegression(max_iter=3000, C=1.0).fit(Ztr[:, c], yb[tr])
            pred[te] = m.predict(Zte[:, c])
        record("fully_nested", k, pred, yb)

    out["note"] = ("every point carries a 2000-resample bootstrap interval over items; "
                   "these are prompt-level intervals and are anti-conservative for "
                   "repeated donors")
    return out


def part4_paired():
    def compare(archive, task):
        recs = [json.loads(l) for l in __import__("gzip").open(RUNS / archive, "rt")]
        sub = [r for r in recs if r.get("task") == task]
        gold, pred = [], []
        invalid_pos = invalid_neg = 0
        for r in sub:
            g = r["answer"]
            v = None if r.get("error") else parse_yes_no(r.get("raw") or "")
            if v is None:
                if g == "yes":
                    invalid_pos += 1
                else:
                    invalid_neg += 1
            gold.append(1 if g == "yes" else 0)
            pred.append(None if v is None else (1 if v == "yes" else 0))
        b, c = paired_counts(gold, pred)
        p = float(binomtest(min(b, c), b + c, 0.5).pvalue) if (b + c) else 1.0
        return dict(task=task, model_wins=b, baseline_wins=c, discordant=b + c,
                    p_exact=p, invalid_on_positive=invalid_pos,
                    invalid_on_negative=invalid_neg, n=len(sub))

    a = compare("openai__gpt-4o-mini__MB-89xx.jsonl.gz", "MB-8901")
    e = compare("qwen__qwen3-235b-a22b-2507__MB-89xx.jsonl.gz", "MB-8911")
    holm = holm_adjust([a["p_exact"], e["p_exact"]])
    a["p_holm"] = float(holm[0])
    e["p_holm"] = float(holm[1])
    return dict(
        family="two cfRNA binary comparisons of the selected best model against always-no",
        caveat="the models were selected as the best performers on these same sets, so the "
               "tests are post-selection and exploratory; the family does not cover the full "
               "14-model roster",
        anchor_gpt4omini=a, extension_qwen3235b=e)


def part5_discrimination_strict():
    """AUROC/AP with the declared stage domain enforced (0-4 integer only)."""
    import gzip
    from sklearn.metrics import average_precision_score
    golds = {}
    for fn, t in (("MB-89xx_plasmacf_test.jsonl.gz", "MB-8905"),
                  ("MB-89xx_plasmacf_ext_test.jsonl.gz", "MB-8915")):
        with gzip.open(ROOT / "prompts" / fn, "rt") as f:
            for line in f:
                r = json.loads(line)
                if r.get("task") == t:
                    golds[(t, r["sample"])] = int(float(r["answer"]))
    out = {}
    for arc in sorted(RUNS.glob("*__MB-89xx.jsonl.gz")):
        model = arc.name.replace("__MB-89xx.jsonl.gz", "")
        with gzip.open(arc, "rt") as f:
            recs = [json.loads(l) for l in f]
        for task in ("MB-8905", "MB-8915"):
            y, s, rejected = [], [], {"non_finite": 0, "out_of_domain": 0,
                                      "non_integer": 0, "unparseable": 0}
            for r in recs:
                if r.get("task") != task:
                    continue
                if r.get("error"):
                    rejected["unparseable"] += 1
                    continue
                v, reason = stage_value(r.get("raw"))
                if reason is not None:
                    rejected[reason] = rejected.get(reason, 0) + 1
                    continue
                g = golds.get((task, r["sample"]))
                if g is None:
                    continue
                y.append(int(g >= 3))
                s.append(float(v))
            if len(set(y)) < 2 or len(y) < 10:
                continue
            out.setdefault(task, {})[model] = dict(
                n=len(y), pos=int(sum(y)),
                auroc=float(roc_auc_score(y, s)),
                average_precision=float(average_precision_score(y, s)),
                rejected=rejected,
                coverage=len(y) / max(1, len(y) + sum(rejected.values())),
            )
    return out


def part6_confusion():
    """Valid-only confusion matrix plus invalid counts by gold class, per model."""
    import gzip
    golds = {}
    for fn, t in (("MB-89xx_plasmacf_test.jsonl.gz", "MB-8901"),
                  ("MB-89xx_plasmacf_ext_test.jsonl.gz", "MB-8911")):
        with gzip.open(ROOT / "prompts" / fn, "rt") as f:
            for line in f:
                r = json.loads(line)
                if r.get("task") == t:
                    golds[(t, r["sample"])] = 1 if r["answer"] == "yes" else 0
    out = {}
    for arc in sorted(RUNS.glob("*__MB-89xx.jsonl.gz")):
        model = arc.name.replace("__MB-89xx.jsonl.gz", "")
        with gzip.open(arc, "rt") as f:
            recs = [json.loads(l) for l in f]
        for task in ("MB-8901", "MB-8911"):
            tp = tn = fp = fn = np_ = nn = 0
            op_pos = op_neg = inv_pos = inv_neg = 0
            for r in recs:
                if r.get("task") != task:
                    continue
                g = golds.get((task, r["sample"]))
                if g is None:
                    continue
                if r.get("error"):
                    if g == 1: op_pos += 1
                    else: op_neg += 1
                    continue
                v = parse_yes_no(r.get("raw") or "")
                if v is None:
                    if g == 1: inv_pos += 1
                    else: inv_neg += 1
                    continue
                p = 1 if v == "yes" else 0
                if g == 1:
                    np_ += 1
                    tp += int(p == 1); fn += int(p == 0)
                else:
                    nn += 1
                    tn += int(p == 0); fp += int(p == 1)
            out.setdefault(task, {})[model] = dict(
                valid_only=dict(TP=tp, FN=fn, TN=tn, FP=fp,
                                n_valid=np_ + nn, n_pos=np_, n_neg=nn),
                invalid=dict(on_positive=inv_pos, on_negative=inv_neg),
                operational=dict(on_positive=op_pos, on_negative=op_neg),
            )
    return out


def main():
    out = {
        "part1_inductive": part1_inductive(),
        "part2_transfer": part2_transfer(),
        "part2b_nested_panel": part2b_nested_panel(),
        "part2c_transfer_paired": part2c_transfer_paired(),
        "part3_ordinal": part3_ordinal(),
        "part3b_amc_original_contract": part3b_amc_original_contract(),
        "part7_nested_topk": part7_nested_topk(),
        "part4_paired": part4_paired(),
        "part5_discrimination_strict": part5_discrimination_strict(),
        "part6_confusion": part6_confusion(),
    }
    (OUT / "v2_corrections.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
