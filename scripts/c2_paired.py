#!/usr/bin/env python3
"""C2 paired significance for the v7 (Qwen3-8B QLoRA) candidate.

Standalone replica of platform/core/masld_platform/paired.py + answers.py +
metrics.py for the five MB-20xx tasks, so the v7 table uses the exact same
conventions as the existing c2_significance tables (McNemar exact on
discordant pairs for accuracy; Wilcoxon signed-rank on paired abs-error
deltas for MAE; verdict at p < 0.05).

Usage:
  python3 c2_paired.py <candidate_archive.jsonl.gz> <runs_dir> <out_prefix>
"""
import gzip
import json
import re
import sys
from pathlib import Path

import numpy as np
from scipy.stats import binomtest, wilcoxon

# ---- frozen task registry (platform/profiles/masld.yaml) -----------------
F_STAGE_PATTERN = re.compile(r"f([0-4])", re.IGNORECASE)

def answer_type(task: str):
    """(kind, normalize, tokens, pattern) for MB-20xx and MB-89xx tasks."""
    suffix = task[-2:]
    if suffix in ("01", "11", "21"):
        return ("yes_no", None, None, None)
    if suffix in ("02", "12", "22"):
        return ("categorical", "upper", ["F0", "F1", "F2", "F3", "F4"], F_STAGE_PATTERN)
    if suffix == "03":
        return ("letter", None, None, None)
    if suffix in ("05", "06", "15", "25"):
        return ("number", None, None, None)
    raise ValueError(f"no answer type for {task!r}")


# ---- answers.py replicas --------------------------------------------------
_YES_NO_PATTERNS = re.compile(r"answer(?:\s+is)?[:\s]\s*\**\s*(yes|no)\b")
_LETTER_PATTERN = re.compile(
    r"answer(?:\s+is)?\s*[:\-]?\s*[*\s>\"'`]*(?:patient|option|choice)?\s*"
    r"[*_\s>\"'`]*([ab])\b",
    re.IGNORECASE,
)
_LETTER_START = re.compile(r"^\s*(?:[*_`#>\-\s]+)?([ABab])\b")
_NUMBER_PATTERN = re.compile(r"-?\d+(?:\.\d+)?")
_LEAD_MARKUP = re.compile(r"^[\s*_`#>\"'(\[]+")
_ANSWER_LEAD = re.compile(r"^\s*(?:the\s+)?answer(?:\s+is)?\s*[:\-]?\s*", re.IGNORECASE)


def _clean(text: str) -> str:
    return _LEAD_MARKUP.sub("", text.strip())


def parse_yes_no(text: str):
    t = _clean(text)
    low = t.lower()
    if low.startswith(("yes", "no")):
        return "yes" if low.startswith("yes") else "no"
    stripped = _ANSWER_LEAD.sub("", t)
    low2 = _clean(stripped).lower()
    if low2.startswith(("yes", "no")):
        return "yes" if low2.startswith("yes") else "no"
    m = _YES_NO_PATTERNS.search(low)
    return m.group(1) if m else None


def parse_letter(text: str):
    t = _clean(text)
    if (m := _LETTER_START.match(t)):
        return m.group(1).upper()
    stripped = _ANSWER_LEAD.sub("", t)
    if (m := _LETTER_START.match(_clean(stripped))):
        return m.group(1).upper()
    m = _LETTER_PATTERN.search(t)
    return m.group(1).upper() if m else None


def parse_number(text: str):
    m = _NUMBER_PATTERN.search(_clean(text))
    if not m:
        return None
    v = float(m.group(0))
    if v != v or v in (float("inf"), float("-inf")):
        return None
    return v


def parse_categorical(text: str, normalize: str, tokens: list, pattern: re.Pattern):
    m = pattern.search(text)
    if not m:
        return None
    captured = (m.group(1) if m.groups() else m.group(0)).strip()
    if not captured:
        return None
    norm = captured.upper() if normalize == "upper" else captured.lower()
    canonical = [t.upper() if normalize == "upper" else t.lower() for t in tokens]
    if norm in canonical:
        return tokens[canonical.index(norm)]
    matches = [i for i, c in enumerate(canonical) if c.endswith(norm) or c.startswith(norm)]
    return tokens[matches[0]] if len(matches) == 1 else None


def parse_answer(text, at):
    if not text or not text.strip():
        return None
    kind, normalize, tokens, pattern = at
    if kind == "yes_no":
        return parse_yes_no(text.strip())
    if kind == "letter":
        return parse_letter(text.strip())
    if kind == "number":
        return parse_number(text.strip())
    return parse_categorical(text.strip(), normalize, tokens, pattern)


def gold_value(answer: str, at) -> str | float:
    kind, normalize, tokens, _ = at
    a = answer.strip()
    if kind == "number":
        return float(a)
    if kind == "categorical":
        norm = a.upper() if normalize == "upper" else a.lower()
        canonical = [t.upper() if normalize == "upper" else t.lower() for t in tokens]
        return tokens[canonical.index(norm)]
    if kind == "yes_no":
        return a.lower()
    return a.upper()


# ---- io_jsonl replicas ----------------------------------------------------
def read_jsonl(path: Path) -> list:
    rows = []
    with gzip.open(path, "rt") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def archive_model_name(path: Path):
    stem = path.name.removesuffix(".jsonl.gz")
    model, _, tag = stem.rpartition("__")
    return model, tag


# ---- paired.py replicas ---------------------------------------------------
def load_indexed(path: Path) -> dict:
    out = {}
    for r in read_jsonl(path):
        if r.get("task") and r.get("sample"):
            out[(r["task"], r["sample"])] = r
    return out


def mcnemar_exact(b: int, c: int):
    n = b + c
    if n == 0:
        return None
    return float(binomtest(b, n, 0.5).pvalue)


def wilcoxon_p(deltas: list):
    nz = [d for d in deltas if d != 0]
    if len(nz) < 3:
        return None
    try:
        return float(wilcoxon(nz).pvalue)
    except ValueError:
        return None


def paired_compare(cand_path: Path, ref_path: Path):
    cand = load_indexed(cand_path)
    ref = load_indexed(ref_path)
    keys = sorted(set(cand) & set(ref))
    by_task: dict[str, list] = {}
    for k in keys:
        by_task.setdefault(k[0], []).append(k)
    rows = []
    for task in sorted(by_task):
        at = answer_type(task)
        kept = []
        golds = []
        for k in by_task[task]:
            answer = cand[k].get("answer")
            if answer is None:
                continue
            try:
                golds.append(gold_value(str(answer), at))
            except (ValueError, IndexError):
                continue
            kept.append(k)
        if not kept:
            continue
        cand_preds = [parse_answer(cand[k].get("raw"), at) for k in kept]
        ref_preds = [parse_answer(ref[k].get("raw"), at) for k in kept]
        if at[0] == "number":
            metric = "mae"
            pairs = [(p, g) for p, g in zip(cand_preds, golds) if p is not None]
            cand_value = float(np.mean([abs(p - g) for p, g in pairs])) if pairs else None
            pairs = [(p, g) for p, g in zip(ref_preds, golds) if p is not None]
            ref_value = float(np.mean([abs(p - g) for p, g in pairs])) if pairs else None
            # item-aligned error comparison (both parseable), then deltas
            both = c_only = r_only = 0
            deltas = []
            for cp, rp, g in zip(cand_preds, ref_preds, golds):
                if cp is not None and rp is not None:
                    ce, re_ = abs(cp - g), abs(rp - g)
                    if ce < re_:
                        c_only += 1
                    elif ce > re_:
                        r_only += 1
                    else:
                        both += 1
                    deltas.append(re_ - ce)  # >0 => candidate better
            neither = len(kept) - both - c_only - r_only
            mcnemar_p = mcnemar_exact(c_only, r_only)
            wp = wilcoxon_p(deltas)
            better = cand_value < ref_value if (cand_value is not None and ref_value is not None) else None
            p_for_verdict = wp
        else:
            metric = "accuracy"
            cand_value = sum(1 for p, g in zip(cand_preds, golds) if p is not None and p == g) / len(golds)
            ref_value = sum(1 for p, g in zip(ref_preds, golds) if p is not None and p == g) / len(golds)
            c_correct = [p is not None and p == g for p, g in zip(cand_preds, golds)]
            r_correct = [p is not None and p == g for p, g in zip(ref_preds, golds)]
            both = sum(1 for c, r in zip(c_correct, r_correct) if c and r)
            c_only = sum(1 for c, r in zip(c_correct, r_correct) if c and not r)
            r_only = sum(1 for c, r in zip(c_correct, r_correct) if r and not c)
            neither = len(kept) - both - c_only - r_only
            mcnemar_p = mcnemar_exact(c_only, r_only)
            wp = wilcoxon_p([float(c) - float(r) for c, r in zip(c_correct, r_correct) if c is not r] or [])
            better = cand_value > ref_value
            p_for_verdict = mcnemar_p
        if p_for_verdict is None or better is None:
            verdict = "TIE"
        elif p_for_verdict < 0.05:
            verdict = "WIN" if better else "LOSS"
        else:
            verdict = "TIE"
        rows.append(dict(
            task=task, metric=metric, n=len(kept),
            cand=cand_value, ref=ref_value,
            both=both, cand_only=c_only, ref_only=r_only, neither=neither,
            mcnemar_p=mcnemar_p, wilcoxon_p=wp, verdict=verdict,
        ))
    return rows


def fmt_p(p):
    if p is None:
        return ""
    if p == 1 or p == 0:
        return str(int(p))
    if p < 0.001:
        return f"{p:.4g}"
    return f"{p:.4g}" if p < 0.1 else f"{p:.4f}"


def fmt_val(v, metric):
    if v is None:
        return ""
    if metric == "accuracy":
        return f"{v:.4f}"
    if abs(v) >= 10000:
        return f"{v:.3e}"
    return f"{v:.3f}"


def main():
    cand_path = Path(sys.argv[1])
    runs_dir = Path(sys.argv[2])
    out_prefix = Path(sys.argv[3])
    cand_name, _ = archive_model_name(cand_path)

    # The frozen 12-model frontier bracket (the C2 reference set).
    REFERENCE_MODELS = {
        "amazon__nova-pro-v1",
        "anthropic__claude-sonnet-4.5",
        "deepseek__deepseek-chat",
        "google__gemini-2.5-pro",
        "meta-llama__llama-3.3-70b-instruct",
        "nvidia__nemotron-3-super-120b-a12b:free",
        "openai__gpt-4.1-mini",
        "openai__gpt-4.1",
        "openai__gpt-4o-mini",
        "openai__gpt-5.6-luna",
        "qwen__qwen-2.5-72b-instruct",
        "qwen__qwen3-235b-a22b-2507",
    }
    ref_files = sorted(runs_dir.glob("*__MB-20xx.jsonl.gz"))
    ref_files = [p for p in ref_files if p.name != cand_path.name
                 and archive_model_name(p)[0] in REFERENCE_MODELS]

    all_rows = []
    for rp in ref_files:
        try:
            rows = paired_compare(cand_path, rp)
        except Exception as e:  # noqa: BLE001 - report and continue
            print(f"!! {rp.name}: {e}", file=sys.stderr)
            continue
        ref_name, _ = archive_model_name(rp)
        for r in rows:
            r["reference"] = ref_name
        all_rows += rows
        print(f"ok {rp.name}: {len(rows)} rows")

    wins = sum(1 for r in all_rows if r["verdict"] == "WIN")
    losses = sum(1 for r in all_rows if r["verdict"] == "LOSS")
    ties = sum(1 for r in all_rows if r["verdict"] == "TIE")

    md_lines = [
        "# C2 paired significance — candidate v7 (McNemar exact + Wilcoxon signed-rank)",
        "",
        "Verdicts at p < 0.05: accuracy -> McNemar, MAE -> Wilcoxon (better = lower).",
        "",
        f"## Candidate: {cand_name} (`{cand_path.name}`)",
        "",
        f"{len(all_rows)} comparisons — WIN {wins} / LOSS {losses} / TIE {ties}",
        "",
        "| reference | task | metric | n | cand | ref | both | cand_only | ref_only | neither | mcnemar_p | wilcoxon_p | verdict |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in all_rows:
        md_lines.append(
            f"| {r['reference']} | {r['task']} | {r['metric']} | {r['n']} | "
            f"{fmt_val(r['cand'], r['metric'])} | {fmt_val(r['ref'], r['metric'])} | "
            f"{r['both']} | {r['cand_only']} | {r['ref_only']} | {r['neither']} | "
            f"{fmt_p(r['mcnemar_p'])} | {fmt_p(r['wilcoxon_p'])} | {r['verdict']} |"
        )

    out_prefix.parent.mkdir(parents=True, exist_ok=True)
    (out_prefix.with_suffix(".md")).write_text("\n".join(md_lines) + "\n")
    import csv
    with open(out_prefix.with_suffix(".csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "reference", "task", "metric", "n", "cand", "ref",
            "both", "cand_only", "ref_only", "neither",
            "mcnemar_p", "wilcoxon_p", "verdict"])
        w.writeheader()
        w.writerows(all_rows)
    print(f"\n-> {out_prefix.with_suffix('.md')} / .csv  "
          f"(WIN {wins} / LOSS {losses} / TIE {ties})")


if __name__ == "__main__":
    main()
