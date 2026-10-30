#!/usr/bin/env python3
"""Frontier bracket runner for MB-89xx (OpenRouter) — per ANALYSIS_PLAN_MB89xx §9.

Runs the 12-model frontier bracket on the anchor (MB-89xx_plasmacf_test) and
extension (MB-89xx_plasmacf_ext_test) corpora — 873 items total. The AMC
variant pair (MB-892x) needs NO API calls: its prompts are byte-identical to
the anchor, so it is scored from this archive against the AMC golds.

Mechanics mirror platform/core/masld_platform/frontier_runner.py:
- key from the environment ONLY (OPENROUTER_API_KEY)
- resume keyed by (task, sample); append-only gzip JSONL archives
- temperature 0, top_p 1, max_tokens 900 (the 200-token truncation lesson)
- retries honour 429 with backoff

Usage:
  export OPENROUTER_API_KEY=sk-or-v1-...
  python3 run_frontier_89xx.py [model...]   # default: all 12 bracket models
"""

from __future__ import annotations

import gzip
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(os.environ.get("MASLD_LLM_ROOT", Path(__file__).resolve().parents[1]))
RUNS = ROOT / "results" / "frontier_runs"
PROMPTS = ROOT / "prompts"

BRACKET = [
    "amazon/nova-pro-v1",
    "anthropic/claude-sonnet-4.5",
    "deepseek/deepseek-chat",
    "google/gemini-2.5-pro",
    "meta-llama/llama-3.3-70b-instruct",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "openai/gpt-4.1-mini",
    "openai/gpt-4.1",
    "openai/gpt-4o-mini",
    "openai/gpt-5.6-luna",
    "qwen/qwen-2.5-72b-instruct",
    "qwen/qwen3-235b-a22b-2507",
]
# Flattened archive-name form (provider__model) used by the scorer.
def archive_name(model: str) -> str:
    return model.replace("/", "__")


def load_corpora() -> list[dict]:
    records: list[dict] = []
    for f in ("MB-89xx_plasmacf_test.jsonl.gz", "MB-89xx_plasmacf_ext_test.jsonl.gz"):
        p = PROMPTS / f
        if not p.exists():
            raise SystemExit(f"missing corpus: {p}")
        with gzip.open(p, "rt") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                if "__meta__" in r:
                    continue
                records.append(r)
    return records


def load_done(path: Path) -> set[tuple[str, str]]:
    if not path.exists():
        return set()
    done = set()
    try:
        with gzip.open(path, "rt") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if r.get("task") and r.get("sample") and r.get("error") is None:
                    done.add((r["task"], r["sample"]))
    except (EOFError, OSError, gzip.BadGzipFile):
        pass
    return done


def append_record(path: Path, rec: dict):
    raw = json.dumps(rec)
    with gzip.open(path, "ab") as f:
        f.write((raw + "\n").encode())


def call_model(key: str, model: str, prompt: str) -> str:
    import urllib.request

    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0,
        "top_p": 1.0,
        "max_tokens": 900,
    }).encode()
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
    )
    backoff = 2.0
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=240) as resp:
                data = json.loads(resp.read())
            return data["choices"][0]["message"]["content"] or ""
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(backoff)
                backoff = min(backoff * 2, 60)
                continue
            if e.code >= 500:
                time.sleep(backoff)
                backoff = min(backoff * 2, 60)
                continue
            raise RuntimeError(f"HTTP {e.code}: {e.read()[:300]}") from e
        except Exception:
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)
    raise RuntimeError("retries exhausted")


def run_model(key: str, model: str, records: list[dict]):
    tag = "MB-89xx"
    out = RUNS / f"{archive_name(model)}__{tag}.jsonl.gz"
    done = load_done(out)
    todo = [r for r in records if (r["task"], r["sample"]) not in done]
    n_fail = 0
    t0 = time.time()

    def work(r):
        try:
            raw = call_model(key, model, r["prompt"])
            return r, raw, None
        except Exception as e:  # noqa: BLE001
            return r, "", f"{type(e).__name__}: {e}"

    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = [ex.submit(work, r) for r in todo]
        for i, fut in enumerate(as_completed(futs), 1):
            r, raw, err = fut.result()
            rec = dict(
                task=r["task"], sample=r["sample"], answer=r["answer"],
                raw=raw, error=err,
                model_version=model,
                parsed=None,
            )
            append_record(out, rec)
            if err:
                n_fail += 1
            if i % 100 == 0 or i == len(todo):
                print(f"  [{model}] {i}/{len(todo)} (fail {n_fail}) "
                      f"{(time.time() - t0) / 60:.1f} min", flush=True)
    print(f"  -> {out.name}: {len(todo)} new, {n_fail} failed, "
          f"{(time.time() - t0) / 60:.1f} min")


def main():
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key or key.upper().startswith("REPLACE_"):
        raise SystemExit("OPENROUTER_API_KEY not set (environment only)")
    models = sys.argv[1:] or BRACKET
    records = load_corpora()
    print(f"corpus: {len(records)} items across anchor + extension")
    for m in models:
        print(f"== {m} ==")
        run_model(key, m, records)


if __name__ == "__main__":
    main()
