#!/usr/bin/env python3
"""Consistency verification for the revision package.

This checks that the manuscript agrees with the analysis artifacts, that the
formats agree with each other, and that withdrawn numbers appear only in
explicitly historical context.

It deliberately does NOT assert a scientific conclusion. A corrected analysis is
allowed to change a result; a verifier that requires the extension gate to pass
or the ordinal gates to fail would be testing the expected answer rather than
the integrity of the pipeline.
"""
import json
import os
import re
import sys
from pathlib import Path

REV = Path(os.environ.get("MASLD_REVISION_DIR", Path(__file__).resolve().parents[1]))
A = REV / "analysis"


def load(n):
    return json.loads((A / n).read_text())


def main():
    manuscript = REV / "MANUSCRIPT_REVISED.md"
    if not manuscript.exists():
        print(f"Manuscript package not present at {manuscript}. "
              "The public release excludes the manuscript; run analysis/tests instead, "
              "or set MASLD_REVISION_DIR to an author-approved package.")
        return 2
    md = manuscript.read_text()
    fails, warns = [], []

    g = load("gate_recompute.json")
    v2 = load("v2_corrections.json")
    llm = load("llm_binary_metrics.json")
    rs = load("reader_sensitivity.json")
    te = load("tissue_eligible.json")

    # ---- 1. text must agree with the artifacts it cites -------------------
    # Every declared quantity: (manuscript string, JSON value, description)
    declared = []

    for task, key in [("MB-8901", "MB-8901_logreg"), ("MB-8911", "MB-8911_logreg"),
                      ("MB-8921", "MB-8921_logreg")]:
        declared.append((f'{g[key]["majority_corrected"]:.4f}', None,
                         f"{task} corrected majority"))
        declared.append((f'{g[key]["accuracy"]:.4f}', None, f"{task} logistic accuracy"))

    ext = v2["part1_inductive"]["MB-8911"]
    declared += [
        (f'{ext["gene_wise_train_moments"]["accuracy"]:.3f}', None,
         "extension inductive gene-wise accuracy"),
        (f'{ext["gene_wise_train_moments"]["ci"][0]:.3f}', None,
         "extension inductive gene-wise CI lower"),
        (f'{ext["per_sample"]["accuracy"]:.3f}', None,
         "extension inductive per-sample accuracy"),
        (f'{v2["part2_transfer"]["extension_external_accuracy"]:.3f}', None,
         "gene-aligned transfer external accuracy"),
        (f'{v2["part2_transfer"]["extension_external_ci"][0]:.3f}', None,
         "transfer CI lower"),
        (f'{v2["part2_transfer"]["extension_external_ci"][1]:.3f}', None,
         "transfer CI upper"),
        (f'{v2["part2_transfer"]["anchor_out_of_fold"]:.3f}', None,
         "anchor-fixed panel within anchor"),
    ]
    for test_key, label in (("anchor_gpt4omini", "anchor"), ("extension_qwen3235b", "extension")):
        t = v2["part4_paired"][test_key]
        declared.append((f'{t["p_exact"]:.4f}'[:5], None, f"{label} paired p"))
        declared.append((f'{t["p_holm"]:.3f}', None, f"{label} Holm p"))

    declared += [
        (f'{rs["reader_agreement"]["unweighted_kappa"]:.3f}', None, "unweighted kappa"),
        (f'{rs["reader_agreement"]["quadratic_kappa"]:.3f}', None, "quadratic kappa"),
        (f'{v2["part7_nested_topk"]["contracts"]["legacy"]["5"]["accuracy"]:.4f}', None,
         "legacy top-5 accuracy"),
        (f'{te["aligned_label_distributions"]["MB-2002"]["majority_accuracy"]:.3f}', None,
         "aligned five-class majority"),
        (f'{te["joint_valid_regression"]["qwen3_1_7b_v5_mae"]:.3f}', None,
         "joint-valid fibrosis MAE for Qwen3-1.7B v5"),
    ]

    for text, _, why in declared:
        if text not in md:
            fails.append(f"manuscript does not contain {text!r} ({why}); analysis and text disagree")

    # ---- 2. abstract numbers must be traceable ----------------------------
    abstract = md.split("## Abstract")[1].split("## 1. Introduction")[0]
    blob = json.dumps({"g": g, "v2": v2, "llm": llm, "rs": rs, "te": te})
    known = [float(x) for x in re.findall(r"-?\d+\.\d+", blob)]
    # tissue figures are carried forward from the frozen leaderboard, which is a
    # declared source for them; include it so carried-forward values stay traceable
    lb = Path(os.environ.get("MASLD_DATA_ROOT", Path(__file__).resolve().parents[1])) / "results" / "leaderboard.csv"
    if lb.exists():
        for m in re.finditer(r",(\d\.\d+),", lb.read_text()):
            known.append(float(m.group(1)))

    def traceable(num_str):
        target = float(num_str)
        tol = 0.5 * 10 ** (-len(num_str.split(".")[1]))
        return any(abs(k - target) <= tol for k in known)

    for num in sorted(set(re.findall(r"\d\.\d{3,4}", abstract))):
        if num not in md:
            fails.append(f"abstract number {num} not found elsewhere in the manuscript")
        if not traceable(num):
            fails.append(f"abstract number {num} is not within rounding distance of any "
                         f"analysis artifact value")

    # ---- 3. withdrawn claims must not appear undated ---------------------
    LEGACY_OK = ("previous", "legacy", "withdrawn", "superseded", "replaced", "earlier", "old")
    # phrase-level patterns, not bare numbers: 0.648 legitimately appears as a
    # confidence bound and inside a DOI, and bare-number banning would be noise
    banned = ["0.3036", "0.3352", "0.3056", "κ = 0.384", "0.670 against a 0.723",
              "holds across three feature representations",
              "robust across three feature representations",
              "balanced accuracy of 0.648", "Holm-adjusted p = 0.685",
              "0.609 [0.542, 0.682]", "0.705", "no conclusion changes",
              "all three lower bounds exceed 0.531",
              "the anchor estimate from 0.723 to 0.705"]
    lines = md.splitlines()
    for bad in banned:
        for i, line in enumerate(lines):
            if bad not in line:
                continue
            window = " ".join(lines[max(0, i - 6):i + 1]).lower()
            if not any(k in window for k in LEGACY_OK):
                fails.append(f"withdrawn expression {bad!r} appears without a historical marker")


    # ---- 3b. semantic variants of withdrawn claims -------------------------
    # A phrase blacklist misses paraphrases. These patterns require that any
    # affirmative use of the old framing sits near a withdrawal word.
    WITHDRAW = ("withdrawn", "does not", "no longer", "not robust", "previous",
                "superseded", "delta", "narrower", "replaced")
    semantic_patterns = [
        r"robust[^.]{0,140}(three|3)\s+(feature\s+)?representations?",
        r"lower confidence bound above the majority rate in all",
        r"survives (all|every) (three )?representation",
        r"consistent across (all )?(three )?representations",
        r"in all of them[^.]{0,60}majority",
    ]
    for pat in semantic_patterns:
        for m in re.finditer(pat, md, flags=re.IGNORECASE):
            window = md[max(0, m.start() - 260):m.end() + 260].lower()
            if not any(w in window for w in WITHDRAW):
                fails.append(f"affirmative withdrawn claim (pattern {pat!r}): "
                             f"...{md[max(0,m.start()-80):m.end()+80]}...")

    # ---- 3c. rounding and arithmetic consistency ---------------------------
    # 0.8125 must be rendered 0.813 under the stated half-up convention
    for i, line in enumerate(md.splitlines(), 1):
        if "0.812" in line:
            fails.append(f"L{i}: 0.812 present; 0.8125 must render as 0.813 half-up")

    # a non-difference claim between preprocessing methods needs a paired test,
    # which was not run; forbid the unsupported phrasing
    for phrase in ("not significantly different from each other",
                   "significantly different from each other"):
        if phrase in md:
            fails.append(f"unsupported inference: {phrase!r} without a paired comparison")

    # the 0.609 vs 0.598 gap is 1.1 points; the 0.5-point figure is the
    # lower-bound margin over the majority rate, not the gap
    if "0.609" in md and "0.598" in md:
        if "1.1 percentage points" not in md:
            fails.append("point-estimate gap (0.609 vs 0.598 = 1.1 pp) is not stated")
        for m in re.finditer(r"half a percentage point", md):
            window = md[max(0, m.start() - 200):m.end() + 120].lower()
            if "0.609" in window and "0.598" in window and "1.1" not in window:
                fails.append("'half a percentage point' used to describe the "
                             "0.609-0.598 gap (it is 1.1 points)")

    # ---- 4. structural completeness --------------------------------------
    for sec in ["## Abstract", "## 1. Introduction", "## 2. Methods", "## 3. Results",
                "## 4. Discussion", "## 5. Limitations", "## 6. Conclusions",
                "## 7. Declarations", "## 8. References", "**Figure legends**"]:
        if sec not in md:
            fails.append(f"missing section: {sec}")

    for n in range(1, 7):
        if f"**Figure {n}.**" not in md:
            fails.append(f"missing figure legend: Figure {n}")

    # ---- 5. figure coverage ---------------------------------------------
    pngs = sorted(p.name for p in (REV / "figures").glob("*.png"))
    if len(pngs) != 6:
        fails.append(f"expected 6 figure files, found {len(pngs)}: {pngs}")

    try:
        from docx import Document
        d = Document(REV / "MANUSCRIPT_REVISED.docx")
        if len(d.inline_shapes) != 6:
            fails.append(f"DOCX embeds {len(d.inline_shapes)} figures, expected 6")
        parts = [p.text for p in d.paragraphs]
        for t in d.tables:
            for row in t.rows:
                parts.extend(c.text for c in row.cells)
        docx_text = "\n".join(parts)
        if len(d.tables) < 10:
            warns.append(f"DOCX has {len(d.tables)} tables; expected at least 10")
    except Exception as e:  # noqa: BLE001
        fails.append(f"DOCX unreadable: {e}")
        docx_text = ""

    html_text = (REV / "MANUSCRIPT_REVISED.html").read_text()
    if html_text.count("<img ") != 6:
        fails.append(f"HTML embeds {html_text.count('<img ')} images, expected 6")

    pdf = REV / "MANUSCRIPT_REVISED.pdf"
    raw = pdf.read_bytes()
    if not raw.startswith(b"%PDF"):
        fails.append("PDF is not a valid PDF")
    pages = raw.count(b"/Type /Page") - raw.count(b"/Type /Pages")
    imgs = raw.count(b"/Subtype /Image")
    if pages < 20:
        fails.append(f"PDF has only {pages} pages")
    if imgs < 6:
        fails.append(f"PDF contains {imgs} images, expected at least 6")

    # cross-format agreement on a few decisive strings
    probes = ["0.7143", "0.5307", "0.400", "56/108"]
    for p in probes:
        if docx_text and p not in docx_text:
            fails.append(f"DOCX missing {p}")
        if p not in html_text:
            fails.append(f"HTML missing {p}")

    # ---- 6. deliverables ------------------------------------------------
    for f in ["MANUSCRIPT_REVISED.md", "MANUSCRIPT_REVISED.docx", "MANUSCRIPT_REVISED.html",
              "MANUSCRIPT_REVISED.pdf", "WIM_RESPONSE_MATRIX.md", "SCIENTIFIC_CORRECTIONS.md",
              "REFERENCES_VERIFIED.md", "AUTHOR_DECISIONS_REQUIRED.md",
              "REVISION_SUMMARY.md", "INVENTORY.md", "CLAIM_TRACEABILITY.md"]:
        p = REV / f
        if not p.exists() or p.stat().st_size < 200:
            fails.append(f"missing or empty deliverable: {f}")

    v2_required = ["part1_inductive", "part2_transfer", "part2b_nested_panel",
                   "part2c_transfer_paired", "part3_ordinal",
                   "part3b_amc_original_contract", "part4_paired",
                   "part5_discrimination_strict", "part6_confusion",
                   "part7_nested_topk"]
    for k in v2_required:
        if k not in v2:
            fails.append(f"v2_corrections.json missing {k}")

    ordinal_tasks = sorted(k for k in v2.get("part3_ordinal", {}) if k.startswith("MB-"))
    if ordinal_tasks != ["MB-8905", "MB-8915", "MB-8925"]:
        fails.append(f"ordinal block covers {ordinal_tasks}, expected all three cohorts")

    amc = v2.get("part3b_amc_original_contract", {})
    if amc.get("panel_source_n") != 112 or amc.get("n") != 108:
        fails.append(f"AMC original contract wrong: panel_source_n={amc.get('panel_source_n')}, n={amc.get('n')}")
    if "112" not in amc.get("feature_contract", ""):
        fails.append("AMC feature contract does not state the 112-sample panel")

    nt = v2.get("part7_nested_topk", {})
    contracts = nt.get("contracts", {})
    for key in ("legacy", "rank_nested", "fully_nested"):
        if key not in contracts:
            fails.append(f"part7 missing contract {key}")
            continue
        for k in nt.get("k", []):
            cell = contracts[key].get(str(k))
            if not cell or "accuracy" not in cell or "ci" not in cell:
                fails.append(f"part7 {key} k={k} lacks an accuracy/interval")
    # every plotted interval must span the majority rate if the text says so
    maj = nt.get("majority")
    if maj is not None and "Every interval in the table spans it" in md:
        for key, cells in contracts.items():
            for k, cell in cells.items():
                lo, hi = cell["ci"]
                if not (lo <= maj <= hi):
                    fails.append(f"text claims every interval spans {maj:.4f}, "
                                 f"but {key} k={k} is [{lo:.3f}, {hi:.3f}]")

    # the abstract must not present the nested figure as the fixed panel
    if "within the anchor the same panel shows no detectable advantage (0.723" in md:
        fails.append("abstract conflates the fixed panel with the nested procedure")

    # every transferred gene must exist in both matrices under the same identifier
    tr = v2["part2_transfer"]
    if tr.get("shared_genes") != tr.get("anchor_genes"):
        fails.append("transfer genes were dropped between anchor and extension")

    tp_ = v2["part2c_transfer_paired"]
    if tp_["model_wins"] + tp_["baseline_wins"] == 0:
        fails.append("external paired comparison has no discordant pairs")
    if tp_["p_exact"] < 0.05 and "not significant" in md:
        fails.append("text calls the external paired test non-significant but p < 0.05")
    if tp_["p_exact"] >= 0.05 and "p = 0.133" not in md and "p = 0.13" not in md:
        fails.append("external paired test is non-significant but the manuscript "
                     "does not report its p-value")

    print("=" * 70)
    print("CONSISTENCY VERIFICATION")
    print("=" * 70)
    if warns:
        print("\nWARNINGS")
        for w in warns:
            print("  •", w)
    if fails:
        print("\nFAILURES")
        for f in fails:
            print("  ✗", f)
        sys.exit(1)
    print("\nAll consistency checks passed.")
    print(f"Manuscript: {len(md.split()):,} words")
    print(f"Figures embedded: 6 | PDF pages: {pages} | PDF images: {imgs}")
    print(f"DOCX: {pdf.parent.joinpath('MANUSCRIPT_REVISED.docx').stat().st_size:,} B")
    print(f"PDF:  {pdf.stat().st_size:,} B")


if __name__ == "__main__":
    main()
