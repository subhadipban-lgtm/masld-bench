# Migration from `masld-llm-bench` (2026-11-23)

`subhadipban-lgtm/masld-llm-bench` (public, no license, ~71 MB, 102 commits)
was the original build workspace for the MASLD-LLM program. It republished
subject-level data and failed gates without context, and carried absolute
local paths and personal email addresses. This document records what was
merged into `masld-bench`, what was deliberately excluded, and why.

**Nothing in this merge changes the published release.** The annotated tag
`v2026.11.10-eligible.1` remains pinned to commit `490d116`; this merge adds a
commit on top of `main` and does not move the tag. The authoritative release
files listed in `RELEASE_MANIFEST.json` were not modified by this merge; the
verification in `results/RESULTS_AUTHORITY.md` and `analysis/tests` still
applies to the tagged release unchanged.

## Imported

| Area | Path in this repo | Notes |
|---|---|---|
| Evaluation platform | `platform/` | FastAPI/Typer/Next.js platform: `masld_platform`, `masld_api`, `masld_agents`, `masld_persistence`. License metadata corrected `Proprietary` → `Apache-2.0`. Frontend `node_modules/` ignored. |
| Corrected corpus builder | `scripts/build_mb86xx.py` | Freeze-16, supersedes the freeze-8 version previously in this repo (header off-by-one misalignment, caught 2026-10-19). |
| Corpus builders | `scripts/build_mb12xx*`, `build_mb85xx.py`, `build_mb87xx.py`, `build_mb88xx*.py`, `c3a_gate_85_87.py`, `make_figures.py` | Same code as in `masld-llm-bench`, with local absolute paths (including a Drive path containing a personal email) replaced by environment-variable defaults. `c2_significance.py` replaces the standalone copy with the platform-library version (`masld_platform.paired`). |
| Aggregate result summaries | `results/{baselines,c3a_gate_85_87,kshot_17b,kshot_ablation,maxgpu_run_manifest,v6_run_manifest}.json` | Task-level n/accuracy/MAE/CI only; no subject-level content. |
| Frozen corpus metadata | `prompts/MANIFEST_freeze16_historical.json` | Freeze-16 manifest (superseded by freeze-17) kept for provenance. The gated corpora themselves are **not** included. |
| Cohort acquisition manifest | `docs/external_cohorts_v3.csv` | 62 GEO/ArrayExpress accessions, public metadata. |
| Blood-cohort search record | `docs/blood-cohort-mb86xx-search-2026-10-19/` | GEO accessions and public per-sample characteristics only. |

## Deliberately excluded

| Content | Why |
|---|---|
| `prompts/*.jsonl.gz` (frozen corpora) | Release policy excludes expression-bearing prompts and subject-level data; access is via artifact-specific review (see `DATA_ACCESS_AND_LICENSES.md`). |
| `data/GSE267032_*`, `data/ensembl_to_symbol_cache.csv` | GEO-derived, third-party, not covered by this repo's license. |
| `results/frontier_runs/**` (per-sample archives) | Subject-level predictions + `sample` identifiers; policy requires private handling. |
| `results/leaderboard.csv.bak-pre-frontier12`, `first_compact_model_scores.json`, `v3_model_scores.json`, `v3_geo_ablation.json` | Pre-correction numbers with degenerate MAE values; would be mistaken for current results. |
| `results/quarantine/**` | Corrupted freeze-8 archives; must not be resurrected. |
| `logs/**` | Machine logs; not source of truth, contain local paths. |
| `drug-discovery/**` | Docking campaign, out of scope for the benchmark release; 26 MB of large binaries (.sdf, .pdb) would bloat the repo permanently. |
| `docs/MASLD-LLM_{cell_publication_plan,master_plan,roadmap}.html`, `master-plan.pdf`, internal Cell-submission target | Internal strategy, not code; also carries pre-correction claims. |
| `docs/RESULTS_DRAFT.md`, `*.html` concept plans | Superseded by `results/RESULTS_AUTHORITY.md`; carries failed-gate narrative without release context. |
| `.openclaw/**`, `COLAB_GPU_PLAN.md`, `NEXT_STEPS.md`, `ZCODE_TASKS.md`, `RUNLOG.md` | Personal workflow state, local paths and personal email; not software. The research history is preserved in the Drive archive and in the `masld-llm-bench` mirror. |
| `platform/frontend/` | Imported; it is the platform UI. No secrets, no subject data. |

## Test status after merge

- `analysis/tests`: 36 passed, 4 skipped (unchanged from the tagged release).
- `platform`: 86 passed. One pre-existing assertion in
  `test_archive_model_name_decoding` was corrected: the archive convention
  splits on the **last** `__` (flattened provider ids contain `__`), which is
  what `archive_model_name` implements; the test had asserted the opposite.

## Known residual items

- `results/leaderboard.csv` retains the retired `qwen3-8b-masld-v7` rows
  (trained-on-test diagnostic) and is declared historical in
  `results/RESULTS_AUTHORITY.md`. It is still present because
  `code/verify_revision.py` and `RELEASE_MANIFEST.json` reference it.
- Legacy scripts in `scripts/` still reference the environment variables
  `MASLD_DATA_ROOT` / `MASLD_REVISION_DIR` / `MASLD_PLATFORM_ROOT`; they are
  not part of the reproduction path (`scripts/reproduce_release.sh`).
- This repo is **not** the venue for the withdrawn claims. They are absent by
  design; see `CHANGELOG.md` and `docs/release/PROVENANCE_AND_LIMITATIONS.md`.
