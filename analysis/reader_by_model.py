#!/usr/bin/env python3
"""
Per-model reader sensitivity.

The AMC-variant corpora (MB-8921/8922/8925) were never queried separately: their
prompt strings are byte-identical to the anchor. The legacy plasma table
therefore scored anchor predictions against the AMC gold. This script does that
explicitly, per model, so that the reader effect is reported as a model-specific
quantity rather than a universal ceiling.

Inputs : prompts/MB-89xx_plasmacf_amcvar_test.jsonl.gz  (AMC gold)
         prompts/MB-89xx_plasmacf_test.jsonl.gz          (UZA gold)
         results/frontier_runs/*__MB-89xx.jsonl.gz       (anchor responses)
Output : analysis/reader_by_model.json
"""
from __future__ import annotations

import gzip
import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(os.environ.get(
    "MASLD_DATA_ROOT",
    os.environ.get("MASLD_LLM_ROOT", Path(__file__).resolve().parents[1]),
))
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts"))
from c2_paired import parse_yes_no  # noqa: E402


def read(p):
    with gzip.open(p, "rt") as f:
        return [json.loads(l) for l in f]


def metrics(gold, pred):
    gold = np.asarray(gold, int)
    valid = np.array([p is not None for p in pred])
    p = np.array([int(x) if x is not None else 0 for x in pred])
    tp = int(((gold == 1) & (p == 1) & valid).sum())
    fn = int(((gold == 1) & ((p == 0) | ~valid)).sum())
    tn = int(((gold == 0) & (p == 0) & valid).sum())
    fp = int(((gold == 0) & (p == 1) & valid).sum())
    n = len(gold)
    n_pos = int((gold == 1).sum())
    n_neg = int((gold == 0).sum())
    sens = tp / n_pos if n_pos else float("nan")
    spec = tn / n_neg if n_neg else float("nan")
    return dict(n=n, valid=int(valid.sum()), tp=tp, fn=fn, tn=tn, fp=fp,
                accuracy=(tp + tn) / n, sensitivity=float(sens),
                specificity=float(spec),
                balanced_accuracy=float(np.nanmean([sens, spec])))


def main():
    uza = {r["sample"]: 1 if r["answer"] == "yes" else 0
           for r in read(ROOT / "prompts/MB-89xx_plasmacf_test.jsonl.gz")
           if r.get("task") == "MB-8901"}
    amc5 = {r["sample"]: r["answer"]
            for r in read(ROOT / "prompts/MB-89xx_plasmacf_amcvar_test.jsonl.gz")
            if r.get("task") == "MB-8921"}
    amc = {s: 1 if v == "yes" else 0 for s, v in amc5.items()}
    shared = sorted(set(uza) & set(amc))
    out = {"n_shared": len(shared),
           "note": "anchor responses (UZA-prompted) scored against the UZA and AMC "
                   "binary golds on the shared samples; prompts are byte-identical, "
                   "so the difference is a pure reader-label swap",
           "models": {}}
    for arc in sorted((ROOT / "results/frontier_runs").glob("*__MB-89xx.jsonl.gz")):
        model = arc.name.replace("__MB-89xx.jsonl.gz", "")
        recs = [r for r in read(arc) if r.get("task") == "MB-8901"]
        preds = {}
        for r in recs:
            if r.get("error"):
                preds[r["sample"]] = None
                continue
            v = parse_yes_no(r.get("raw") or "")
            preds[r["sample"]] = None if v is None else (1 if v == "yes" else 0)
        g_u = [uza[s] for s in shared]
        g_a = [amc[s] for s in shared]
        p = [preds.get(s) for s in shared]
        out["models"][model] = {
            "uza": metrics(g_u, p),
            "amc": metrics(g_a, p),
            "accuracy_difference_uza_minus_amc":
                metrics(g_u, p)["accuracy"] - metrics(g_a, p)["accuracy"],
        }
    (OUT / "reader_by_model.json").write_text(json.dumps(out, indent=1))
    for m, v in out["models"].items():
        print(f"{m:42s} UZA {v['uza']['accuracy']:.3f}  AMC {v['amc']['accuracy']:.3f}  "
              f"diff {v['accuracy_difference_uza_minus_amc']:+.3f}  "
              f"n={v['uza']['n']} valid={v['uza']['valid']}")


if __name__ == "__main__":
    main()
