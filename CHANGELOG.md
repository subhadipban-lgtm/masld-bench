# Changelog

## 2026.11.10-eligible.1 — local release candidate

- Added the corrected cfRNA production analyses and aggregate outputs.
- Added the 17-model eligible tissue analysis with explicit exclusion of the
  three checkpoints exposed to MB-12xx.
- Added aligned evaluated-item scoring, pairwise-manifest separation,
  biological-sample cluster intervals, conditional and joint-valid regression
  sensitivity, coverage and domain checks.
- Corrected the aligned five-class majority to 43/163 = 0.264 and distinguished
  it from uniform-choice chance 0.200.
- Added the fixed-prediction AMC reader comparison on 108 shared samples with
  verified prompt-byte identity.
- Added 38 production tests, release verification code and figure generation.
- Replaced personal absolute paths with `MASLD_DATA_ROOT`,
  `MASLD_ELIGIBLE_OUTPUT_DIR` and `MASLD_REVISION_DIR` configuration.
- Added a new explicitly versioned result export; historical 297-row and
  275-row leaderboards are not the current result authority.
- Excluded subject-level data, response archives, private correspondence,
  credentials and unapproved manuscript material.

Earlier project history is retained in the source repository, but legacy result
files are not authoritative for this release.

## 2026.11.10-eligible.1 (review fixes)

- Removed the legacy Figure 3 generation from `code/make_revised_figs.py`;
  Figure 3 is written only by `code/regenerate_eligible_figs.py` from
  eligible-model results. Added a release-integrity test for this.
- Removed the superseded classifier-based ordinal blocks from
  `gate_recompute.json`; the artifact now carries an explicit
  `ordinal_superseded_by` pointer to `v2_corrections.json` part3_ordinal.
- Documented the `PYTHON="$PWD/.venv/bin/python"` invocation and the
  `results/gates_mb89xx.json` input requirement.

## 2026.11.10-eligible.1 (fresh-checkout hygiene)

- Subject-level per-item predictions are now exported only to
  `MASLD_PER_ITEM_DIR` and are never written into the public checkout by
  default.
- Figure generation writes only the public figure directories; Supplementary
  Figure S6 regeneration requires the private per-item export and is skipped
  with a notice otherwise.
- The complete documented reproduction command was verified in a fresh clone
  with a fresh pinned environment.
