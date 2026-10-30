#!/usr/bin/env python3
"""Score the MB-89xx frontier archives -> leaderboard rows + AMC-variant readout.

- Leaderboard rows for 8901/8902/8905 (anchor, UZA gold), 8911/8912/8915
  (extension, clinical-consensus gold), and 8921/8922/8925 (AMC-gold variant
  pair scored from the SAME anchor archive outputs — zero extra API calls).
- Schema matches results/leaderboard.csv:
  model,task,n,metric,value,ci_lo,ci_hi,validity,rho
- Bootstrap 95% CI (10,000 resamples, seed 20260929), invalid-as-error.
"""

from __future__ import annotations

import gzip
import json
import os
import sys
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parent))
from c2_paired import answer_type, archive_model_name, gold_value, parse_answer, read_jsonl  # noqa: E402

ROOT = Path(os.environ.get("MASLD_LLM_ROOT", Path(__file__).resolve().parents[1]))
RUNS = ROOT / "results" / "frontier_runs"
PROMPTS = ROOT / "prompts"
OUT = ROOT / "results" / "leaderboard.csv"
SEED = 20260929

BASE_TO_VAR = {"MB-8901": "MB-8921", "MB-8902": "MB-8922", "MB-8905": "MB-8925"}


def bootstrap_ci(vals, n=10000):
    rng = np.random.default_rng(SEED)
    vals = np.asarray(vals, dtype=float)
    if len(vals) == 0:
        return None, None
    idx = rng.integers(0, len(vals), size=(n, len(vals)))
    means = vals[idx].mean(axis=1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def score_items(items):
    """items: list of dicts with task/sample/answer(gold)/raw. Per-task metrics."""
    by_task: dict[str, list] = {}
    for r in items:
        by_task.setdefault(r["task"], []).append(r)
    out = []
    for task, rows in sorted(by_task.items()):
        at = answer_type(task)
        golds, preds = [], []
        for r in rows:
            try:
                g = gold_value(str(r["answer"]), at)
            except (ValueError, IndexError):
                continue
            golds.append(g)
            preds.append(parse_answer(r.get("raw"), at))
        n = len(golds)
        validity = sum(1 for p in preds if p is not None) / n if n else 0.0
        if at[0] == "number":
            pairs = [(p, g) for p, g in zip(preds, golds) if p is not None]
            if not pairs:
                continue
            errs = np.array([abs(p - g) for p, g in pairs])
            mae = float(errs.mean())
            lo, hi = bootstrap_ci(errs)
            rho = None
            if len(set(g for _, g in pairs)) > 1 and len(set(p for p, _ in pairs)) > 1:
                rho = float(spearmanr([p for p, _ in pairs], [g for _, g in pairs]).statistic)
            out.append(dict(task=task, n=n, metric="mae", value=round(mae, 6),
                            ci_lo=round(lo, 6) if lo else None,
                            ci_hi=round(hi, 6) if hi else None,
                            validity=round(validity, 6), rho=round(rho, 6) if rho else None))
        else:
            correct = np.array([1.0 if p is not None and p == g else 0.0
                                for p, g in zip(preds, golds)])
            acc = float(correct.mean())
            lo, hi = bootstrap_ci(correct)
            out.append(dict(task=task, n=n, metric="accuracy", value=round(acc, 6),
                            ci_lo=round(lo, 6), ci_hi=round(hi, 6),
                            validity=round(validity, 6), rho=None))
    return out


def main():
    archives = sorted(RUNS.glob("*__MB-89xx.jsonl.gz"))
    if not archives:
        raise SystemExit("no MB-89xx archives found")
    amcvar_path = PROMPTS / "MB-89xx_plasmacf_amcvar_test.jsonl.gz"
    amc_golds: dict[tuple[str, str], str] = {}
    if amcvar_path.exists():
        for r in read_jsonl(amcvar_path):
            if "__meta__" in r:
                continue
            amc_golds[(r["task"], r["sample"])] = r["answer"]

    rows = []
    # idempotency: skip (model, task) pairs already scored in the leaderboard
    existing = set()
    if OUT.exists():
        import csv as _csv
        with open(OUT) as f:
            for r in _csv.DictReader(f):
                existing.add((r["model"], r["task"]))

    for p in archives:
        model, _ = archive_model_name(p)
        items = [r for r in read_jsonl(p) if "__meta__" not in r]
        rows += [{**r, "model": model} for r in score_items(items)]

        # AMC-variant readout: re-score the anchor outputs vs AMC golds.
        anchor_idx = {(r["task"], r["sample"]): r for r in items}
        var_items = []
        for (var_task, sample), gold in amc_golds.items():
            base_task = next(b for b, v in BASE_TO_VAR.items() if v == var_task)
            rec = anchor_idx.get((base_task, sample))
            if rec is not None:
                var_items.append(dict(task=var_task, sample=sample,
                                      answer=gold, raw=rec.get("raw")))
        rows += [{**r, "model": model} for r in score_items(var_items)]
        # keep only rows not already in the leaderboard
        keep = [r for r in rows if (r["model"], r["task"]) not in existing]
        rows[:] = keep

    if not rows:
        raise SystemExit("nothing scored")
    header = "model,task,n,metric,value,ci_lo,ci_hi,validity,rho"
    with open(OUT, "a") as f:
        for r in rows:
            f.write(",".join(str(r.get(k, "")) for k in header.split(",")) + "\n")
    print(f"appended {len(rows)} rows -> {OUT}")
    for r in rows:
        print(" ", r["model"], r["task"], r["metric"], r["value"],
              f"[{r['ci_lo']},{r['ci_hi']}]", "val", r["validity"], "rho", r["rho"])


if __name__ == "__main__":
    main()
