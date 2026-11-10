# PR title: Authoritative cfRNA and eligible-model tissue analysis release

## Summary

Prepare a reviewable release of the corrected cfRNA analyses and the new
17-model eligible tissue analysis. This replaces the current result authority
with explicitly versioned aggregate outputs; it does not substitute either
historical leaderboard for the corrected analysis.

## Changes

- Add corrected cfRNA production analysis, supporting binary metrics and the
  fixed-prediction AMC reader comparison.
- Add eligible-model tissue analysis with explicit exposed-checkpoint
  exclusion, aligned evaluated items, pairwise manifests, cluster intervals,
  coverage/domain checks and joint-valid regression sensitivity.
- Add aggregate JSON/TSV outputs and regenerated main/supplementary figures.
- Add 38 production tests; 34 run in the public checkout and 4 require the
  private manuscript package.
- Add portable configuration, pinned dependencies and exact reproduction
  commands.
- Add release/access/provenance documentation, result-authority policy,
  citation metadata and Apache-2.0 software license.
- Exclude subject-level data, response archives, private manuscript material,
  credentials and local cache files.

## Testing

- [x] `python -m pytest analysis/tests -q` — 34 passed, 4 skipped.
- [x] Full private-package suite — 38 passed.
- [x] Portable cfRNA analysis executed with `MASLD_DATA_ROOT`.
- [x] Portable tissue analysis executed; generated summary matches the release
  export byte-for-byte.
- [x] AMC reader analysis and figure generation executed.
- [ ] Visual acceptance of figures and rendered manuscript (outstanding).

## Before publication

- Review artifact-specific data permissions and author declarations.
- Decide whether an author-approved manuscript is public-release material.
- Regenerate `RELEASE_MANIFEST.json` after any final change.
- Reconcile this branch with the then-current remote state before pushing.
