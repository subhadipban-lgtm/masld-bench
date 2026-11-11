#!/usr/bin/env python3
"""Regenerate Figure 6 from the corrected nested top-k analysis.

Figure 3 is generated exclusively by code/regenerate_eligible_figs.py from the
eligible-model aligned analysis; this script must not write Figure 3.
"""
import json
import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

_savefig = Figure.savefig
def _dual_save(self, fname, *a, **kw):
    _savefig(self, fname, *a, **kw)
    q = Path(str(fname))
    if q.suffix == '.png':
        _savefig(self, q.with_suffix('.pdf'), bbox_inches='tight', pad_inches=.06)
Figure.savefig = _dual_save
import numpy as np
import pandas as pd

ROOT = Path(os.environ.get(
    "MASLD_DATA_ROOT",
    os.environ.get("MASLD_LLM_ROOT", Path(__file__).resolve().parents[1]),
))
REV = Path(__file__).resolve().parents[1]
OUT = REV / "figures"
LB = ROOT / "results/leaderboard.csv"

NAVY, TEAL, RED, GREY = "#1d3557", "#2a9d8f", "#b5171f", "#8d99ae"
COMPACT = {"Qwen3-0.6B v3", "Qwen3-0.6B v5", "Qwen3-0.6B v6", "Qwen3-1.7B v3",
           "Qwen3-1.7B v5", "Qwen3-1.7B v6", "Qwen3-8B v7"}
REN = {
    "amazon__nova-pro-v1": "Nova Pro", "anthropic__claude-sonnet-4.5": "Claude Sonnet 4.5",
    "deepseek__deepseek-chat": "DeepSeek Chat", "google__gemini-2.5-pro": "Gemini 2.5 Pro",
    "meta-llama__llama-3.3-70b-instruct": "Llama 3.3 70B",
    "nvidia__nemotron-3-super-120b-a12b:free": "Nemotron 120B",
    "openai__gpt-4.1": "GPT-4.1", "openai__gpt-4.1-mini": "GPT-4.1-mini",
    "openai__gpt-4o-mini": "GPT-4o-mini", "openai__gpt-5.6-luna": "GPT-5.6 Luna",
    "qwen__qwen-2.5-72b-instruct": "Qwen2.5 72B", "qwen__qwen3-235b-a22b-2507": "Qwen3 235B",
    "qwen3-0.6b-masld": "Qwen3-0.6B v3", "qwen3-0.6b-masld-v5": "Qwen3-0.6B v5",
    "qwen3-0.6b-masld-v6": "Qwen3-0.6B v6", "qwen3-1.7b-masld": "Qwen3-1.7B v3",
    "qwen3-1.7b-masld-v5": "Qwen3-1.7B v5", "qwen3-1.7b-masld-v6": "Qwen3-1.7B v6",
    "qwen3-8b-masld-v7": "Qwen3-8B v7", "inception__mercury-2.5": "Mercury-2.5",
}

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 7, "savefig.dpi": 300,
    "savefig.bbox": "tight", "savefig.pad_inches": 0.04,
    "axes.spines.top": False, "axes.spines.right": False,
})


def fig6():
    """Signal concentration under three preprocessing contracts, with intervals."""
    nt = json.loads((REV / "analysis/v2_corrections.json").read_text())["part7_nested_topk"]
    ks = nt["k"]
    C = nt["contracts"]
    fig, ax = plt.subplots(figsize=(4.8, 3.4))
    styles = [
        ("legacy", "o-", GREY, "ranking outside CV (legacy)"),
        ("rank_nested", "s--", "#6c8ebf", "ranking nested, frozen representation"),
        ("fully_nested", "^-", NAVY, "fully nested (all preprocessing)"),
    ]
    for key, fmt, col, lab in styles:
        acc = [C[key][str(k)]["accuracy"] for k in ks]
        lo = [C[key][str(k)]["ci"][0] for k in ks]
        hi = [C[key][str(k)]["ci"][1] for k in ks]
        ax.errorbar(ks, acc, yerr=[np.array(acc) - np.array(lo), np.array(hi) - np.array(acc)],
                    fmt=fmt, color=col, ms=3.5, lw=1.1, elinewidth=0.6, capsize=1.6,
                    alpha=0.95, label=lab)
    ax.axhline(nt["majority"], ls=(0, (2, 2)), color=RED, lw=0.8)
    ax.text(200, nt["majority"] + 0.003, "majority 0.714", fontsize=5.6, color=RED,
            ha="right", va="bottom")
    ax.set_xscale("log")
    ax.set_xticks(ks)
    ax.set_xticklabels([str(k) for k in ks])
    ax.set_xlabel("Top-k genes in panel")
    ax.set_ylabel("Out-of-fold accuracy")
    ax.set_ylim(0.53, 0.85)
    ax.legend(frameon=False, fontsize=5.2, loc="lower left")
    ax.set_title("Plasma reference cohort: every contract's interval spans the majority rate",
                 loc="left", fontsize=6.8, pad=6)
    fig.savefig(OUT / "Figure_6_concentration_corrected.png")
    plt.close(fig)
    print("wrote Figure_6_concentration_corrected.png")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    fig6()
