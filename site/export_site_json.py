#!/usr/bin/env python3
"""Export the MASLD-Bench leaderboard + gates to the site JSON.

Usage:
  MASLD_LLM_ROOT="/path/to/My Drive/masld-llm" python3 export_site_json.py
Writes assets/leaderboard.json next to this script.
"""
import csv
import json
import os
import sys
from pathlib import Path

ROOT = Path(os.environ.get("MASLD_LLM_ROOT", ""))
if not ROOT or not (ROOT / "results" / "leaderboard.csv").exists():
    sys.exit("set MASLD_LLM_ROOT to the masld-llm Drive folder first")

SITE = Path(__file__).resolve().parent


def num(x):
    return None if x in ("", None, "None") else float(x)


rows = list(csv.DictReader(open(ROOT / "results" / "leaderboard.csv")))
for r in rows:
    r["value"] = num(r["value"]); r["ci_lo"] = num(r["ci_lo"]); r["ci_hi"] = num(r["ci_hi"])
    r["validity"] = num(r["validity"]); r["rho"] = num(r["rho"])

gates = json.load(open(ROOT / "results" / "gates_mb89xx.json"))
manifest = json.load(open(ROOT / "prompts" / "MANIFEST.json"))

out = {
    "meta": {
        "benchmark": "MASLD-Bench",
        "tagline": "The disease-specific, histology-grounded omics-LLM benchmark.",
        "freeze": manifest["version"],
        "seed": manifest["seed"],
        "updated": "2026-10-30",
        "n_rows": len(rows),
        "disclaimer": "Research benchmark only — not a diagnostic or clinical tool.",
    },
    "families": {
        "MB-20xx": {"name": "Liver transcriptomics (frozen test)", "labels": "biopsy fibrosis F0-F4, NAS", "gold": "biopsy"},
        "MB-85xx": {"name": "Progression proxy", "labels": "stable vs progressive", "gold": "biopsy stage"},
        "MB-86xx": {"name": "Blood-proxy severity", "labels": "low/medium/high", "gold": "histology-graded"},
        "MB-87xx": {"name": "Liver->plasma proteomics", "labels": "platform / masked protein z", "gold": "platform"},
        "MB-88xx": {"name": "Perturbation transfer", "labels": "FFA yes/no", "gold": "donor-grouped"},
        "MB-89xx": {"name": "Plasma cfRNA (freeze-17)", "labels": "biopsy Brunt F0-F4 (dual-reader) + clinical consensus",
                    "gold": "biopsy_brunt_uza / biopsy_brunt_amc / clinical_consensus"},
    },
    "gates": gates,
    "label_noise": {
        "uza_amc_kappa": 0.384,
        "classical_acc_uza": gates["label_noise_logreg"]["acc_vs_uza"],
        "classical_acc_amc": gates["label_noise_logreg"]["acc_vs_amc"],
        "gap_pp": round(gates["label_noise_logreg"]["gap"] * 100, 1),
    },
    "whysplit": {
        "top_genes_anchor": ["P4HA2", "ELN", "AMOTL2", "RGS5", "SREBF1"],
        "top5_oof_acc_anchor": 0.714,
        "full_panel_oof_anchor": 0.723,
        "marker_overlap": "0/20",
    },
    "leaderboard": rows,
}
out_path = SITE / "assets" / "leaderboard.json"
out_path.parent.mkdir(exist_ok=True)
json.dump(out, open(out_path, "w"), indent=1)
print(f"{len(rows)} rows -> {out_path}")
