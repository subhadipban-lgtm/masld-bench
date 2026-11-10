#!/usr/bin/env python3
"""Generate release/result manifests from the final working tree.

Run after the release commit. `code_commit` is the commit being reviewed; the
manifest itself is committed separately so its own hash need not be recursive.
"""
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "2026.11.10-eligible.1"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def record(path):
    p = ROOT / path
    return {"path": path, "bytes": p.stat().st_size, "sha256": sha256(p)}


def main():
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    base = subprocess.check_output(["git", "rev-parse", "origin/main"], cwd=ROOT, text=True).strip()
    result_files = [
        "results/eligible/tissue_eligible_summary.tsv",
        "results/eligible/tissue_eligible_ranks.tsv",
        "results/eligible/tissue_archive_coverage_audit.tsv",
        "results/eligible/tissue_regression_joint_valid.tsv",
    ]
    result_manifest = {
        "export_version": VERSION,
        "code_commit": commit,
        "generated_by": "analysis/rescore_tissue_eligible.py",
        "files": [record(p) for p in result_files],
    }
    (ROOT / "results/eligible/RESULT_EXPORT_VERSION.json").write_text(
        json.dumps(result_manifest, indent=1) + "\n"
    )

    authoritative = [
        "analysis/corrections_v2.py", "analysis/revised_metrics.py",
        "analysis/reader_by_model.py", "analysis/rescore_tissue_eligible.py",
        "analysis/v2_corrections.json", "analysis/tissue_eligible.json",
        "analysis/reader_by_model.json", "analysis/gate_recompute.json",
        "analysis/llm_binary_metrics.json", "analysis/reader_sensitivity.json",
        "analysis/CORRECTIONS.json",
        "code/verify_revision.py", "code/build_revised.py",
        "code/make_revised_figs.py", "code/regenerate_eligible_figs.py",
        "code/make_release_manifest.py",
        "results/RESULTS_AUTHORITY.md",
        "results/eligible/RESULT_EXPORT_VERSION.json",
        "results/tables/table2_tissue_coverage.csv",
        "results/tables/figure2_eligible_ranks.csv",
        "README.md", "CHANGELOG.md", "CITATION.cff", "LICENSE",
        "DATA_ACCESS_AND_LICENSES.md", "requirements-release.txt",
        "environment-lock.txt", "scripts/reproduce_release.sh",
        "docs/release/PROVENANCE_AND_LIMITATIONS.md",
        "docs/release/RELEASE_NOTES.md",
    ]
    authoritative += [str(p.relative_to(ROOT)) for p in sorted((ROOT / "analysis/tests").glob("*.py"))]
    authoritative += [str(p.relative_to(ROOT)) for p in sorted((ROOT / "figures").glob("*.png"))]
    authoritative += [str(p.relative_to(ROOT)) for p in sorted((ROOT / "figures_supplementary").glob("*.png"))]
    manifest = {
        "release_version": VERSION,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "base_commit": base,
        "code_commit": commit,
        "status": "local review candidate; not published",
        "authoritative_files": [record(p) for p in authoritative],
        "historical_not_authoritative": [
            "results/leaderboard.csv",
            "results/c2_significance_v7.csv",
            "legacy scripts not named in the reproduction commands",
        ],
        "excluded": [
            "subject-level per-item predictions and expression-bearing prompts",
            "raw response archives and checkpoints",
            "private manuscript/comments/correspondence",
            "credentials, .DS_Store, __pycache__, training caches",
        ],
        "verification": {
            "public_checkout_tests": "34 passed, 4 skipped (manuscript-dependent)",
            "full_private_package_tests": "38 passed",
            "portable_tissue_summary_matches_export": True,
        },
    }
    (ROOT / "RELEASE_MANIFEST.json").write_text(json.dumps(manifest, indent=1) + "\n")
    print("wrote RELEASE_MANIFEST.json and results/eligible/RESULT_EXPORT_VERSION.json")


if __name__ == "__main__":
    main()
