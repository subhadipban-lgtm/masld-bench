import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_legacy_figure3_generation_is_removed():
    src = (ROOT / "code/make_revised_figs.py").read_text()
    assert "def fig3(" not in src
    assert "fig3()" not in src
    assert "Figure_3_binary_corrected.png" not in src
    assert "fig6()" in src


def test_gate_recompute_has_no_classifier_ordinal_blocks():
    src = (ROOT / "analysis/revised_metrics.py").read_text()
    g = json.loads((ROOT / "analysis/gate_recompute.json").read_text())
    assert "ordinal_gate" not in src
    for key in ("MB-8905", "MB-8915", "MB-8925"):
        assert key not in g, f"superseded ordinal block {key} still present"
    assert "ordinal_superseded_by" in g
    assert "part3_ordinal" in g["ordinal_superseded_by"]
