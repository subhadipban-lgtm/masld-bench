#!/usr/bin/env bash
# Reproduce the authoritative MASLD-Bench release outputs.
# Requires a private data root containing prompts/, data/ and results/frontier_runs/.
# No source data or subject-level output is written into the public checkout.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PYTHON:-python3}"
DATA_ROOT="${MASLD_DATA_ROOT:?Set MASLD_DATA_ROOT to the private data directory}"
export MASLD_DATA_ROOT
export MASLD_ELIGIBLE_OUTPUT_DIR="${MASLD_ELIGIBLE_OUTPUT_DIR:-$REPO_ROOT/results/eligible}"

if [[ ! -d "$DATA_ROOT/prompts" || ! -d "$DATA_ROOT/results/frontier_runs" ]]; then
  printf 'Data root must contain prompts/ and results/frontier_runs/: %s\n' "$DATA_ROOT" >&2
  exit 2
fi

cd "$REPO_ROOT"
"$PYTHON" analysis/corrections_v2.py
"$PYTHON" analysis/revised_metrics.py
"$PYTHON" analysis/reader_by_model.py
"$PYTHON" analysis/rescore_tissue_eligible.py
"$PYTHON" code/regenerate_eligible_figs.py
"$PYTHON" code/make_revised_figs.py
"$PYTHON" code/make_supplementary_schematics.py
"$PYTHON" -m pytest analysis/tests -q

printf '\nAuthoritative outputs are in analysis/ and results/eligible/.\n'
printf 'Manuscript verification is optional and requires MASLD_REVISION_DIR with an author-approved package.\n'
