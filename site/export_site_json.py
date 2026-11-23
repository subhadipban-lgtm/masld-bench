#!/usr/bin/env python3
"""Export the eligible-analysis results to assets/leaderboard.json for the site.

Source of truth is results/eligible/ in this repository. This script copies
aggregate statistics only — no subject-level data, no prompt corpora.
Run from the repository root:

    python3 site/export_site_json.py
"""
import csv
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
ELIGIBLE = ROOT / "results" / "eligible"
OUT = ROOT / "site" / "assets" / "leaderboard.json"

EXPORT_VERSION = json.loads((ELIGIBLE / "RESULT_EXPORT_VERSION.json").read_text())["export_version"]

MODEL_LABELS = {
    "amazon__nova-pro-v1": "Amazon Nova Pro",
    "anthropic__claude-sonnet-4.5": "Claude Sonnet 4.5",
    "deepseek__deepseek-chat": "DeepSeek Chat",
    "google__gemini-2.5-pro": "Gemini 2.5 Pro",
    "inception__mercury-2.5": "Mercury 2.5",
    "meta-llama__llama-3.3-70b-instruct": "Llama 3.3 70B Instruct",
    "nvidia__nemotron-3-super-120b-a12b:free": "Nemotron 3 Super 120B A12B",
    "openai__gpt-4.1": "GPT-4.1",
    "openai__gpt-4.1-mini": "GPT-4.1 mini",
    "openai__gpt-4o-mini": "GPT-4o mini",
    "openai__gpt-5.6-luna": "GPT-5.6 Luna",
    "qwen3-0.6b-masld": "Qwen3-0.6B MASLD (v3)",
    "qwen3-0.6b-masld-v5": "Qwen3-0.6B MASLD v5",
    "qwen3-1.7b-masld": "Qwen3-1.7B MASLD (v3)",
    "qwen3-1.7b-masld-v5": "Qwen3-1.7B MASLD v5",
    "qwen__qwen-2.5-72b-instruct": "Qwen2.5 72B Instruct",
    "qwen__qwen3-235b-a22b-2507": "Qwen3 235B A22B 2507",
    "qwen3-0.6b-masld-v6": "Qwen3-0.6B MASLD v6",
    "qwen3-1.7b-masld-v6": "Qwen3-1.7B MASLD v6",
    "qwen3-8b-masld-v7": "Qwen3-8B MASLD v7",
}
TASKS = {
    "MB-2001": {"name": "Advanced fibrosis vs non-advanced (F3–F4 vs F0–F2)",
                "kind": "binary", "metric": "accuracy",
                "majority": 0.656, "chance": None, "n": 163},
    "MB-2002": {"name": "Five-stage fibrosis classification (F0–F4)",
                "kind": "multiclass", "metric": "accuracy",
                "majority": 0.264, "chance": 0.2, "n": 163},
    "MB-2003": {"name": "Pairwise case-comparison (item sets differ per model)",
                "kind": "pairwise", "metric": "accuracy",
                "majority": None, "chance": None, "n": None},
    "MB-2005": {"name": "Fibrosis-stage regression (0–4)",
                "kind": "regression", "metric": "mae",
                "majority": None, "chance": None, "n": 162},
    "MB-2006": {"name": "NAS regression",
                "kind": "regression", "metric": "mae",
                "majority": None, "chance": None, "n": 163},
}
PAIRWISE_NOTE = ("MB-2003 item sets differ per model family (14 models on 300 shared items; "
                 "DeepSeek and Nemotron on 258 in-corpus items; Gemini 2.5 Pro on 414 items). "
                 "Cells are not comparable across the three manifest groups.")

def num(x):
    if x is None or x == "":
        return None
    try:
        v = float(x)
    except ValueError:
        return None
    import math
    return v if math.isfinite(v) else None

rows = list(csv.DictReader(open(ELIGIBLE / "tissue_eligible_summary.tsv"), delimiter="\t"))
by_roster_task = {}
for r in rows:
    key = (r["roster"], r["task"])
    by_roster_task.setdefault(key, []).append(r)

def shape(r):
    return {
        "model": r["model"], "label": MODEL_LABELS.get(r["model"], r["model"]),
        "task": r["task"],
        "n": int(r["n"]), "valid": int(r["valid"]), "in_domain": int(r["in_domain"]),
        "correct": int(r["correct"]) if r["correct"] else None,
        "accuracy": num(r["accuracy"]), "ci_lo": num(r["ci_lo"]), "ci_hi": num(r["ci_hi"]),
        "mae": num(r["mae"]), "mae_in_domain": num(r["mae_in_domain"]),
        "mae_failure_aware": num(r["mae_failure_aware"]), "spearman": num(r["spearman"]),
    }

ranking = {}
for line in open(ELIGIBLE / "tissue_eligible_ranks.tsv"):
    pass
ranks = list(csv.DictReader(open(ELIGIBLE / "tissue_eligible_ranks.tsv"), delimiter="\t"))
ranking = ranks

site = {
    "meta": {
        "title": "MASLD-Bench",
        "tagline": "Disease-specific, histology-grounded omics language-model benchmark for MASLD.",
        "export_version": EXPORT_VERSION,
        "source": "results/eligible (aggregate, eligible-model tissue analysis)",
        "scope": "Liver tissue task roster. cfRNA and blood-cohort families are reported in the manuscript, not on this page.",
        "disclaimer": "Research benchmark only — not a diagnostic or clinical tool.",
        "n_eligible_models": len({r["model"] for r in rows if r["roster"] == "eligible"}),
        "task_defs": TASKS,
        "pairwise_note": PAIRWISE_NOTE,
        "correction_note": "Qwen3-0.6B v6, Qwen3-1.7B v6 and Qwen3-8B v7 were trained on mixtures containing the GSE135251 test split and are excluded from the primary roster; they appear below as exposed-data diagnostics only.",
    },
    "eligible": [shape(r) for r in rows if r["roster"] == "eligible"],
    "exposed_diagnostic": [shape(r) for r in rows if r["roster"] == "exposed_diagnostic"],
    "pairwise_by_manifest": {
        m: [shape(r) for r in rows if r["roster"] == m]
        for m in sorted({r["roster"] for r in rows if r["roster"].startswith("pairwise_manifest_")})
    },
    "ranking": ranking,
}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(site, indent=1, allow_nan=False))
print(f"wrote {OUT}")
