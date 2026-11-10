# Script authority

The default release path uses only the analysis entry points documented in the
repository README and `scripts/reproduce_release.sh`.

Production dependencies retained here include `build_mb89xx.py` and
`c2_paired.py`. Other legacy builders, scorers, gate scripts and notebooks are
historical artifacts. Some contain defects documented in the correction record
(for example five-class majorities used as binary baselines, conditional numeric
parsing without domain checks, and non-nested feature selection). They are not
the default scoring path and must not be used to regenerate the release results
without reading `docs/release/PROVENANCE_AND_LIMITATIONS.md`.
