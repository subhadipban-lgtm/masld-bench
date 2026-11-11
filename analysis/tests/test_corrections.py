"""Regression tests for each confirmed defect in the original analysis.

Run:  pytest docs/paper/REVISION_2026-11-09/analysis/tests -q
Each test encodes the failure that was actually observed, so a regression
fails loudly instead of silently reverting to the old behaviour.
"""
import sys
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
ANALYSIS = HERE.parent
sys.path.insert(0, str(ANALYSIS))

from revised_metrics import (  # noqa: E402
    _amc_stage, binary_metrics, cohen_kappa, holm, weighted_kappa, z_gene_wise,
    z_sample_wise, bootstrap_ci,
)


# --- 1. binary majority must come from the binary label vector -------------

def test_binary_majority_is_not_five_class_majority():
    five = np.array([0] * 34 + [1] * 22 + [2] * 24 + [3] * 15 + [4] * 17)  # 112
    binary = (five >= 3).astype(int)                                      # 32 positive
    five_majority = np.bincount(five).max() / len(five)
    binary_majority = np.bincount(binary).max() / len(binary)
    assert abs(five_majority - 0.3035714) < 1e-6
    assert abs(binary_majority - 0.7142857) < 1e-6
    assert binary_majority > five_majority + 0.4


def test_extension_and_amc_majorities():
    assert abs(95 / 179 - 0.5307263) < 1e-6
    assert abs(73 / 108 - 0.6759259) < 1e-6


# --- 2. tie-aware average precision ---------------------------------------

def test_average_precision_is_tie_order_invariant():
    from sklearn.metrics import average_precision_score
    scores = np.array([0.5, 0.5, 0.5, 0.5])
    a = average_precision_score([1, 1, 0, 0], scores)
    b = average_precision_score([0, 0, 1, 1], scores)
    assert a == pytest.approx(0.5)
    assert b == pytest.approx(0.5)
    assert a == pytest.approx(b)


def test_legacy_auprc_was_order_dependent():
    """Reproduce the defect so the test documents what was wrong."""
    def legacy_auprc(y, s):
        order = np.argsort(-s)
        y = np.asarray(y)[order]
        tp = np.cumsum(y)
        prec = tp / np.arange(1, len(y) + 1)
        rec = tp / max(1, tp[-1])
        rec = np.concatenate([[0.0], rec])
        prec = np.concatenate([[1.0], prec])
        return float(np.trapezoid(prec, rec))

    s = np.array([0.5, 0.5, 0.5, 0.5])
    assert legacy_auprc([1, 1, 0, 0], s) == pytest.approx(1.0)
    assert legacy_auprc([0, 0, 1, 1], s) == pytest.approx(0.2916667, abs=1e-6)


# --- 3. median label is not the constant predictor's MAE ------------------

def test_median_label_is_not_median_predictor_mae():
    y = np.array([0] * 34 + [1] * 22 + [2] * 24 + [3] * 15 + [4] * 17)
    median_label = float(np.median(y))
    constant_mae = float(np.mean(np.abs(median_label - y)))
    assert median_label == 1.5
    assert constant_mae == pytest.approx(1.2410714, abs=1e-6)
    assert abs(median_label - constant_mae) > 0.2


# --- 4. z-scoring direction -------------------------------------------------

def test_gene_wise_z_gives_zero_gene_means():
    t = np.array([[1.0, 2.0, 3.0],
                  [10.0, 20.0, 30.0]])
    z = z_gene_wise(t, [0, 1])
    assert np.allclose(z.mean(axis=1), 0.0)      # zero mean per GENE
    assert not np.allclose(z.mean(axis=0), 0.0)  # not per sample


def test_sample_wise_z_gives_zero_sample_means():
    t = np.array([[1.0, 2.0, 3.0],
                  [10.0, 20.0, 30.0]])
    z = z_sample_wise(t, [0, 1])
    assert np.allclose(z.mean(axis=0), 0.0)
    assert not np.allclose(z.mean(axis=1), 0.0)


# --- 5. invalid answers must count as errors ------------------------------

def test_invalid_answers_are_errors_not_dropped():
    gold = [1, 0]
    pred = [1, None]
    m = binary_metrics(gold, pred)
    assert m["n"] == 2
    assert m["valid"] == 1
    assert m["accuracy"] == pytest.approx(0.5)   # not 1.0
    assert m["sensitivity"] == pytest.approx(1.0)
    assert m["specificity"] == pytest.approx(0.0)


def test_all_no_classifier_has_zero_sensitivity():
    """Exact contingency observed for GPT-4o-mini on MB-8901.

    32 positives: 30 answered "no", 2 unparseable.
    80 negatives: 75 answered "no", 5 unparseable.
    """
    gold = [1] * 32 + [0] * 80
    pred = [0] * 30 + [None] * 2 + [0] * 75 + [None] * 5
    assert sum(1 for p in pred if p == 0) == 105
    assert sum(1 for p in pred if p is None) == 7
    m = binary_metrics(gold, pred)
    assert m["tp"] == 0
    assert m["sensitivity"] == 0.0
    assert m["specificity"] == pytest.approx(75 / 80)
    assert m["balanced_accuracy"] == pytest.approx(0.46875)
    assert m["accuracy"] == pytest.approx(75 / 112)


# --- 6. reader agreement denominators and weighting -----------------------

def test_kappa_uses_joint_denominator():
    u = [0, 0, 1, 1, 2, 2]
    a = [0, 1, 1, 1, 2, 3]
    assert cohen_kappa(u, a) == pytest.approx(0.5, abs=0.08)
    q = weighted_kappa(u, a, "quadratic")
    assert q > cohen_kappa(u, a)  # weighting credits near misses


def test_quadratic_kappa_exceeds_unweighted_on_ordinal_data():
    u = np.array([0, 1, 2, 3, 4] * 10)
    a = np.array([0, 1, 2, 3, 4] * 10)
    a[::10] = np.clip(a[::10] + 1, 0, 4)  # small ordinal shifts
    assert weighted_kappa(u, a, "quadratic") >= cohen_kappa(u.tolist(), a.tolist())


# --- 7. AMC stage parsing ---------------------------------------------------

def test_amc_stage_parses_na_as_missing():
    assert _amc_stage("3") == 3
    assert _amc_stage("3.0") == 3
    assert _amc_stage("NA") == -1
    assert _amc_stage("") == -1
    assert _amc_stage(None) == -1


# --- 8. Holm adjustment ----------------------------------------------------

def test_holm_is_monotone_and_bounded():
    p = [0.01, 0.04, 0.03]
    adj = holm(p)
    assert np.all(adj >= np.array(p) - 1e-12)
    assert np.all(adj <= 1.0)
    assert adj[0] == pytest.approx(0.03)


# --- 9. zero CI bounds are not dropped ------------------------------------

def test_bootstrap_ci_can_return_zero_lower_bound():
    vals = np.array([0.0, 0.0, 0.0, 1.0] * 25)
    lo, hi = bootstrap_ci(vals, n=200)
    assert isinstance(lo, float)
    assert 0.0 <= lo <= hi <= 1.0
