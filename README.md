# MASLD-Bench

The disease-specific, histology-grounded omics-LLM benchmark for metabolic
dysfunction-associated steatotic liver disease. Frozen prompt corpora with
biopsy endpoints, a paired-significance evaluation discipline, and the first
LLM-positive (and first label-noise-controlled) disease family.

**Research use only** — not a diagnostic or clinical tool.

## What's here

| Path | Contents |
|---|---|
| `scripts/` | corpus builders, scorers, gates, paired statistics, frontier runner, whysplit attribution |
| `colab/` | the numbered pipeline notebooks (01–11): prompt construction, baselines, fine-tuning, evals, the Drive-bridge worker, HF merge/push |
| `analysis-plan/` | the frozen pre-registrations (v1, C3 addendum, MB-89xx) |
| `docs/` | results draft (C1–C5), whitespace/positioning analysis, blood-cohort hunt, HF landscape, MASLD-Claw agent spec |
| `results/` | leaderboard (297 rows), paired significance tables, classical gates, whysplit — the evidence layer |
| `prompts/MANIFEST.json` | freeze state (v3-freeze-17), rules, corpus counts |
| `hf-release/` | model cards + the v7 training pipeline for the HF repos |
| `site/` | the static benchmark site (`masldbenchmarks-site`) |

**Not in this repo (on the Drive, by design):** the frozen prompt corpora
(`prompts/MB-*.jsonl.gz`), source data (`data/`), model checkpoints
(`checkpoints/`), and evaluation archives (`results/frontier_runs/`).
They stay on the Google Drive workspace; the corpora and checkpoints will be
mirrored publicly with the preprint.

## Models

- `Subhadip-igtm/masld-bench-qwen3-1.7b-sft-v6` (+`-adapter`)
- `Subhadip-igtm/masld-bench-qwen3-8b-sft-v7` (+`-adapter`)

## Headline results

- C4 regime split: frontier LLMs sit at class-prior on fixed-panel omics
  wherever a linear model reads signal — **except on plasma cfRNA (MB-89xx)**,
  where they are statistically tied with the logistic regression.
- Scale axis: the 8B does not beat the 1.7B where it matters; scale is not
  the binding constraint.
- Label noise: dual-reader biopsy staging (κ = 0.384) caps classical accuracy
  by ~13 points — measured directly, for the first time in any benchmark.

## Reproducibility

Every scored number traces to `results/`. Freeze discipline: corpora are
SHA-256-manifested and never regenerated; corrections get new freeze numbers
with quarantine. Seed 20260929 everywhere. Colab notebooks must keep torchao
**absent** (see the dependency cells).

## Status

Manuscript in preparation. Preprint, corpus mirrors, and public model
repos land together.
