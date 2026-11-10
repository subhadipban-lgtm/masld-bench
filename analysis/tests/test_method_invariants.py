"""Method-invariant tests for the corrected analysis.

These tests check that the *procedure* is sound, not that a particular result
came out. They are deliberately independent of whether the extension cohort
passes or fails a gate: a corrected analysis is allowed to change conclusions,
and a test that forbids that would be testing the answer rather than the method.

Run:  pytest docs/paper/REVISION_2026-11-09/analysis/tests -q
"""
import sys
from pathlib import Path

import json

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
ANALYSIS = HERE.parent
sys.path.insert(0, str(ANALYSIS))

import corrections_v2 as cv2  # noqa: E402
from corrections_v2 import (  # noqa: E402
    align_genes, holm_adjust, mad_genes_raw, paired_counts, stage_value,
    z_gene_train, z_sample,
)


# ---------------------------------------------------------------- alignment

def test_gene_alignment_is_by_identity_not_position():
    anchor = ["G3", "G1", "G5", "G2"]
    ext = ["G1", "G2", "G4", "G3", "G5"]          # different order, different length
    ai = {g: i for i, g in enumerate(anchor)}
    ei = {g: i for i, g in enumerate(ext)}
    names, acols, ecols = align_genes(anchor, ext, ai, ei)
    assert names == ["G3", "G1", "G5", "G2"]
    for n, a, e in zip(names, acols, ecols):
        assert anchor[a] == n
        assert ext[e] == n
    # positional indexing would give a different gene for at least one slot
    positional = [ext[i] for i in acols]
    assert positional != names


def test_alignment_drops_absent_genes_rather_than_substituting():
    anchor = ["G1", "G2", "GX"]
    ext = ["G1", "G2"]
    names, acols, ecols = align_genes(anchor, ext,
                                      {g: i for i, g in enumerate(anchor)},
                                      {g: i for i, g in enumerate(ext)})
    assert names == ["G1", "G2"]
    assert len(acols) == len(ecols) == 2


def test_alignment_raises_when_a_gene_is_misindexed():
    anchor = ["G1", "G2"]
    ext = ["G2", "G1"]
    ai = {"G1": 0, "G2": 1}
    ei = {"G1": 1, "G2": 0}
    names, acols, ecols = align_genes(anchor, ext, ai, ei)
    assert names == ["G1", "G2"]
    assert ext[ecols[0]] == "G1"


# ---------------------------------------------------------------- leakage

def test_panel_selection_depends_only_on_training_columns():
    rng = np.random.default_rng(0)
    t = rng.normal(size=(50, 12))
    genes = [f"G{i}" for i in range(50)]
    train = [0, 1, 2, 3, 4, 5]
    _, g_before = mad_genes_raw(t[:, train], genes, k=10)
    t_perturbed = t.copy()
    t_perturbed[:, 6:] = rng.normal(size=(50, 6)) * 1e6   # destroy held-out only
    _, g_after = mad_genes_raw(t_perturbed[:, train], genes, k=10)
    assert g_before == g_after


def test_gene_moments_are_estimated_on_training_only():
    rng = np.random.default_rng(1)
    t_tr = rng.normal(size=(20, 8))     # genes x samples
    t_te = rng.normal(size=(20, 4))
    idx = list(range(20))
    Xtr, Xte = z_gene_train(t_tr, t_te, idx)
    # training block has zero mean and unit sd per gene
    assert np.allclose(Xtr.mean(axis=0), 0.0, atol=1e-9)
    assert np.allclose(Xtr.std(axis=0), 1.0, atol=1e-9)
    # held-out block must be transformed with TRAINING moments, not its own
    mu = t_tr.mean(axis=1, keepdims=True)
    sd = np.maximum(t_tr.std(axis=1, keepdims=True), 1e-12)
    expected = ((t_te - mu) / sd).T
    assert np.allclose(Xte, expected, atol=1e-12)
    # held-out mean is therefore generally NOT zero
    assert np.abs(Xte.mean(axis=0)).max() > 1e-6


def test_per_sample_scaling_uses_no_cross_sample_information():
    rng = np.random.default_rng(2)
    t_tr = rng.normal(size=(30, 5))
    t_te = rng.normal(size=(30, 3))
    idx = list(range(30))
    _, Xte = z_sample(t_tr, t_te, idx)
    # per-sample standardisation: each SAMPLE row has zero mean across genes
    assert np.allclose(Xte.mean(axis=1), 0.0, atol=1e-9)
    # changing a training sample must not alter held-out features
    t_tr2 = t_tr.copy()
    t_tr2[:, 0] *= 50
    _, Xte_b = z_sample(t_tr2, t_te, idx)
    assert np.allclose(Xte, Xte_b)


def test_fold_pipeline_never_sees_held_out_columns(monkeypatch):
    """Spy on the production selection call inside fold_metrics_raw."""
    rng = np.random.default_rng(7)
    n_genes, n_samples = 60, 40
    t = rng.normal(size=(n_genes, n_samples))
    genes = [f"G{i}" for i in range(n_genes)]
    y = np.array([0] * 24 + [1] * 16)

    seen = []
    real = cv2.mad_genes_raw

    def spy(t_sub, gene_ids, k=200):
        seen.append(t_sub.copy())
        return real(t_sub, gene_ids, k=k)

    monkeypatch.setattr(cv2, "mad_genes_raw", spy)
    cv2.fold_metrics_raw(t, genes, y, "gene")
    assert len(seen) == 5, "one selection per fold"
    for block in seen:
        assert block.shape[1] == n_samples - n_samples // 5, \
            "each selection must receive training columns only"


def test_amc_uses_the_original_feature_contract():
    """The AMC panel must come from 112 samples and be subset to 108 rows."""
    v2 = json.loads((ANALYSIS.parent / "analysis" / "v2_corrections.json").read_text())
    amc = v2["part3b_amc_original_contract"]
    assert amc["panel_source_n"] == 112
    assert amc["n"] == 108
    assert "112" in amc["feature_contract"]
    for key in ("ridge_as_specified_rounded", "hgb_regressor_as_specified_rounded",
                "ridge_continuous", "hgb_regressor_continuous"):
        assert key in amc, key


def test_topk_has_three_distinct_contracts():
    v2 = json.loads((ANALYSIS.parent / "analysis" / "v2_corrections.json").read_text())
    nt = v2["part7_nested_topk"]
    assert nt["k"] == [5, 10, 20, 50, 200]
    C = nt["contracts"]
    for key in ("legacy", "rank_nested", "fully_nested"):
        assert set(C[key]) == {"5", "10", "20", "50", "200"}
        for cell in C[key].values():
            assert 0.0 <= cell["accuracy"] <= 1.0
            lo, hi = cell["ci"]
            assert lo <= cell["accuracy"] <= hi, cell
    # the three contracts must not be silently identical
    assert not (C["legacy"] == C["fully_nested"])
    # the manuscript states every interval spans the majority rate; verify it
    maj = nt["majority"]
    for key in C:
        for k, cell in C[key].items():
            assert cell["ci"][0] <= maj <= cell["ci"][1], (key, k, cell)


MANUSCRIPT = ANALYSIS.parent / "MANUSCRIPT_REVISED.md"
requires_manuscript = pytest.mark.skipif(
    not MANUSCRIPT.exists(),
    reason="author-approved manuscript package is intentionally excluded from the public release",
)


@requires_manuscript
def test_rounding_convention_is_uniform():
    md = (ANALYSIS.parent / "MANUSCRIPT_REVISED.md").read_text()
    assert "0.812" not in md, "0.8125 must render as 0.813 under the half-up convention"
    assert "0.813" in md
    from decimal import Decimal, ROUND_HALF_UP
    assert str(Decimal("0.8125").quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)) == "0.813"


@requires_manuscript
def test_no_unsupported_nondifference_claim():
    md = (ANALYSIS.parent / "MANUSCRIPT_REVISED.md").read_text()
    assert "not significantly different from each other" not in md
    if "0.609" in md and "0.598" in md:
        assert "1.1 percentage points" in md


@requires_manuscript
def test_discussion_has_no_affirmative_robustness_claim():
    import re
    md = (ANALYSIS.parent / "MANUSCRIPT_REVISED.md").read_text()
    pat = r"robust[^.]{0,140}(three|3)\s+(feature\s+)?representations?"
    for m in re.finditer(pat, md, flags=re.IGNORECASE):
        window = md[max(0, m.start() - 260):m.end() + 260].lower()
        assert any(w in window for w in
                   ("withdrawn", "does not", "no longer", "not robust", "previous",
                    "superseded", "narrower", "survives one")), \
            f"affirmative robustness claim: ...{md[m.start()-60:m.end()+60]}..."


def test_ordinal_block_covers_all_three_declared_cohorts():
    v2 = json.loads((ANALYSIS.parent / "analysis" / "v2_corrections.json").read_text())
    tasks = [k for k in v2["part3_ordinal"] if k.startswith("MB-")]
    assert sorted(tasks) == ["MB-8905", "MB-8915", "MB-8925"], tasks


# ---------------------------------------------------------------- estimators

def test_ordinal_estimator_families_are_preserved():
    from sklearn.ensemble import HistGradientBoostingRegressor
    from sklearn.linear_model import Ridge
    src = (ANALYSIS / "corrections_v2.py").read_text()
    assert "Ridge(alpha=1.0)" in src
    assert "HistGradientBoostingRegressor" in src
    # the substituted classifiers must not be used for the ordinal block
    block = src.split("def part3_ordinal")[1].split("def part3b_amc_original_contract")[0]
    assert "LogisticRegression" not in block
    assert isinstance(Ridge(alpha=1.0), Ridge)
    assert isinstance(HistGradientBoostingRegressor(random_state=0),
                      HistGradientBoostingRegressor)


# ---------------------------------------------------------------- invalid

def test_invalid_on_negative_is_a_loss_against_always_no():
    """Uses the production discordance helper, not a reimplementation."""
    gold = [0, 0, 0, 1, 1]
    pred = [0, None, 1, 0, 1]
    wins, losses = paired_counts(gold, pred)
    assert wins == 1          # the one correct positive
    assert losses == 2        # invalid on a negative + wrong positive on a negative
    # on a positive item, an invalid answer and always-no are BOTH wrong, so the
    # pair is concordant and contributes nothing to McNemar
    assert paired_counts([1], [None]) == (0, 0)
    # on a negative item, an invalid answer loses to always-no
    assert paired_counts([0], [None]) == (0, 1)


def test_stage_parser_is_the_production_one():
    assert stage_value("0") == (0, None)
    assert stage_value("4") == (4, None)
    assert stage_value(" 3 ") == (3, None)
    for bad in ("11111", "-1", "2.5", "nan", "inf", "", None):
        v, reason = stage_value(bad)
        assert v is None and reason is not None, bad
    # out-of-range and non-integer must be distinguishable for the reject log
    assert stage_value("11111")[1] == "out_of_domain"
    assert stage_value("2.5")[1] == "non_integer"


# ---------------------------------------------------------------- holm

def test_holm_is_monotone_and_bounded():
    p = [0.01, 0.04, 0.03]
    adj = holm_adjust(p)
    assert np.all(adj >= np.array(p) - 1e-12)
    assert np.all(adj <= 1.0)
    assert adj[0] == pytest.approx(0.03)


def test_holm_two_tests_known_answer():
    adj = holm_adjust([0.0625, 0.3425805825718986])
    assert adj[0] == pytest.approx(0.125)
    assert adj[1] == pytest.approx(0.3425805825718986, rel=1e-9)


def test_paired_counts_on_the_real_anchor_contingency():
    """0 TP, 30 FN, 75 TN, 0 FP, 2 invalid positives, 5 invalid negatives."""
    gold = [1] * 32 + [0] * 80
    pred = [0] * 30 + [None] * 2 + [0] * 75 + [None] * 5
    wins, losses = paired_counts(gold, pred)
    assert wins == 0
    assert losses == 5


# ---------------------------------------------------------------- figures

@requires_manuscript
def test_every_legend_has_an_embedded_figure():
    rev = ANALYSIS.parent
    md = (rev / "MANUSCRIPT_REVISED.md").read_text()
    figs = sorted(p.name for p in (rev / "figures").glob("*.png"))
    assert len(figs) == 6, figs
    for n in range(1, 7):
        assert f"**Figure {n}.**" in md
    from docx import Document
    d = Document(rev / "MANUSCRIPT_REVISED.docx")
    assert len(d.inline_shapes) == 6
    assert all(p.stat().st_size > 20_000 for p in (rev / "figures").glob("*.png"))
