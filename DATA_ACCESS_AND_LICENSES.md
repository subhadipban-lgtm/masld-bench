# Data access and license notes

## Software

Repository code is released under Apache-2.0 (`LICENSE`). This license applies
only to the software. It does not blanket-license source-derived expression
data, prompts, annotations, model responses or per-item predictions.

## Files included in this release candidate

| Path class | Access basis |
|---|---|
| `analysis/*.py`, `code/*.py`, `analysis/tests/` | Project-generated analysis and test code; Apache-2.0 |
| `analysis/*.json`, `results/eligible/*`, `results/tables/*` | Aggregate model/task metrics without sample identifiers or expression values |
| `figures/`, `figures_supplementary/` | Aggregate plots generated from those metrics |
| `docs/release/`, release metadata | Provenance, access and limitation documentation |

## Files deliberately excluded

| Artifact | Reason / required access review |
|---|---|
| Raw sequencing reads (EGA EGAD50000000775 / EGAS50000000545; SRA) | Controlled-access or source-repository terms; not redistributed |
| Processed public matrices (GEO, ArrayExpress, MassIVE) | Available from source repositories under their own terms; not included here |
| S-BSST1614 matrices and annotations | DUA-gated; derived prompt release requires confirmation from the data custodian |
| Expression-bearing prompts and subject-level per-item predictions | Artifact-specific provenance/permission review required; public sample IDs alone do not establish redistribution permission |
| Model response archives | Contain raw generated text and subject-level keys; not reviewed for public release |
| Private manuscript comments, correspondence and author decisions | Not public-release material |

## Raw-data requirements for reproduction

A private `MASLD_DATA_ROOT` must contain:

- `prompts/MB-20xx_liver_test.jsonl.gz` and the frozen MB-89xx corpora;
- `results/frontier_runs/` response archives;
- `data/sbsst1614/` matrices and annotations required by the cfRNA analysis;
- `results/leaderboard.csv` only for the optional historical panels that still
  reference it;
- `results/gates_mb89xx.json`, the legacy gate record read by
  `analysis/revised_metrics.py` for its binary-baseline comparison.

The public checkout can run its artifact tests without these data. Regenerating
the analyses requires the authorized private data above. Subject-level
per-item predictions are exported only when `MASLD_PER_ITEM_DIR` points at a
private directory. No reproduction step uploads data or changes access
permissions.
