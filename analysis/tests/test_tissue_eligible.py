import json
from pathlib import Path

A = Path(__file__).resolve().parents[1]


def test_tissue_eligible_roster_and_denominators():
    d = json.loads((A / "tissue_eligible.json").read_text())
    assert d["eligible_model_count"] == 17
    exposed = set(d["exposed_models"])
    records = d["records"]
    eligible_models = {r["model"] for r in records if r["roster"] == "eligible"}
    assert len(eligible_models) == 17
    assert not (eligible_models & exposed)
    for r in records:
        n = int(r["n"])
        valid = int(r["valid"])
        assert 0 <= valid <= n
        if r["roster"] == "eligible" and r["task"] in {"MB-2001", "MB-2002", "MB-2006"}:
            assert n == 163
        if r["roster"] == "eligible" and r["task"] == "MB-2005":
            assert n == 162


def test_tissue_pairwise_manifests_are_not_mixed():
    d = json.loads((A / "tissue_eligible.json").read_text())
    pairwise = [r for r in d["records"] if r["task"] == "MB-2003" and r["roster"].startswith("pairwise_manifest")]
    manifest_sizes = {r["roster"]: int(r["n"]) for r in pairwise}
    assert set(manifest_sizes.values()) == {258, 300, 414}
    assert len({r["roster"] for r in pairwise}) == 3


def test_five_class_majority_and_interval_relationship():
    d = json.loads((A / "tissue_eligible.json").read_text())
    dist = d["aligned_label_distributions"]["MB-2002"]
    assert dist["n"] == 163
    assert dist["counts"] == {"F0": 31, "F1": 35, "F2": 42, "F3": 43, "F4": 12}
    majority = dist["majority_accuracy"]
    assert abs(majority - 43 / 163) < 1e-12
    # Uniform-choice chance is a separate baseline, not the observed majority.
    assert abs(majority - 0.2) > 0.05
    nemotron = next(r for r in d["records"]
                    if r["model"] == "nvidia__nemotron-3-super-120b-a12b:free"
                    and r["task"] == "MB-2002" and r["roster"] == "eligible")
    lo, hi = float(nemotron["ci_lo"]), float(nemotron["ci_hi"])
    assert lo <= majority <= hi
    assert not (lo <= 0.2 <= hi)


def test_regression_conditional_and_joint_valid_denominators():
    d = json.loads((A / "tissue_eligible.json").read_text())
    v5 = next(r for r in d["records"] if r["model"] == "qwen3-1.7b-masld-v5"
              and r["task"] == "MB-2005" and r["roster"] == "eligible")
    llama = next(r for r in d["records"] if r["model"] == "meta-llama__llama-3.3-70b-instruct"
                 and r["task"] == "MB-2005" and r["roster"] == "eligible")
    assert int(v5["n"]) == int(v5["valid"]) == 162
    assert int(llama["n"]) == 162 and int(llama["valid"]) == 150
    joint = d["joint_valid_regression"]
    assert joint["n_joint_valid"] == 150
    assert joint["qwen3_1_7b_v5_mae"] < joint["llama_3_3_70b_mae"]
    assert joint["n_joint_valid"] <= int(v5["valid"])
    assert joint["n_joint_valid"] <= int(llama["valid"])
