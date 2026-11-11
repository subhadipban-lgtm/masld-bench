# MASLD-Bench — authoritative analysis release

**Release candidate:** `2026.11.10-eligible.1`  
**Status:** local review candidate; not yet published or pushed.  
**Research use only — not a diagnostic or clinical tool.**

This branch contains the corrected cfRNA analysis and the eligible-model tissue
analysis. It does not treat the historical 297-row or 275-row leaderboards as
the current result export.

## Authoritative outputs

| Analysis | Production entry point | Aggregate output |
|---|---|---|
| Corrected cfRNA analyses | `analysis/corrections_v2.py` | `analysis/v2_corrections.json` |
| Supporting cfRNA binary metrics | `analysis/revised_metrics.py` | `analysis/gate_recompute.json`, `analysis/llm_binary_metrics.json`, `analysis/reader_sensitivity.json` |
| Fixed-prediction reader comparison | `analysis/reader_by_model.py` | `analysis/reader_by_model.json` |
| Eligible-model tissue analysis | `analysis/rescore_tissue_eligible.py` | `analysis/tissue_eligible.json`, `results/eligible/` |

The tissue roster contains 17 models with all five tissue tasks and explicitly
excludes Qwen3-0.6B v6, Qwen3-1.7B v6 and Qwen3-8B v7 because their fine-tuning
mixtures contained the GSE135251 test samples. Single-sample tasks use common
archived items. Pairwise results are grouped by exact evaluation manifest.
Regression reports conditional and joint-valid MAE, coverage, in-domain counts
and failure-aware sensitivity. The exposed checkpoints are diagnostics, not
primary generalization evidence.

## What is not included

- Frozen expression-bearing prompts, source matrices, subject-level per-item
  predictions, model response archives, checkpoints or training caches.
- Private manuscript comments, author-decision drafts, correspondence or
  unapproved manuscript versions.
- Credentials, `.DS_Store`, `__pycache__` or local audit directories.

Public sample identifiers and per-item outputs require artifact-specific
permission/provenance review before any future release. Source-derived data are
not covered by the software license; see `DATA_ACCESS_AND_LICENSES.md`.

## Portable reproduction

Python >=3.10 is required. Install the pinned dependencies, then point
`MASLD_DATA_ROOT` at a private data directory containing `prompts/`, `data/`
and `results/frontier_runs/`:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-release.txt
export MASLD_DATA_ROOT=/path/to/private/masld-data
.venv/bin/python -m pytest analysis/tests -q
PYTHON="$PWD/.venv/bin/python" bash scripts/reproduce_release.sh
```

The private data root must also contain `results/gates_mb89xx.json`, which the
supporting binary-gate analysis reads unconditionally as its legacy comparison
record. Without it, `analysis/revised_metrics.py` fails with a clear
file-not-found error.

Subject-level per-item predictions are never written into the public checkout.
To regenerate Supplementary Figure S6 from its source data, export them
privately first:

```bash
export MASLD_PER_ITEM_DIR=/path/to/private/per-item-export
```

Without that variable, the reproduction regenerates every other figure and
skips S6 with a notice.

The reproduction script writes aggregate outputs into this checkout and never
requires the author's local audit folder. Raw-data access requirements are
listed in `DATA_ACCESS_AND_LICENSES.md`.

Optional manuscript build/verification is available only with an author-approved
private package:

```bash
export MASLD_REVISION_DIR=/path/to/private/manuscript-package
.venv/bin/python code/build_revised.py
.venv/bin/python code/verify_revision.py
```

## Release documents

- `CHANGELOG.md` — correction and release history.
- `docs/release/PROVENANCE_AND_LIMITATIONS.md` — dataset accessions, exposure
  map, evaluated-item rules, prompt-identity limits and missing-source inventory.
- `DATA_ACCESS_AND_LICENSES.md` — file-specific data/access notes.
- `RELEASE_MANIFEST.json` — commit and artifact hashes, regenerated for this
  release candidate.
- `results/RESULTS_AUTHORITY.md` — result-version and supersession policy.
- `CITATION.cff`, `LICENSE`, `environment-lock.txt`.

Legacy scripts remain only as historical artifacts with warnings in
`scripts/README.md`; they are not the default scoring path.
