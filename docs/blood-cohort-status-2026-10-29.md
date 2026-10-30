# Cell-tier blood cohort — status re-check (2026-10-29)

Follow-up to the 2026-10-19 blood-cohort search
(`docs/blood-cohort-mb86xx-search-2026-10-19/`). Two fresh facts:

## 1. Strict blood cohort (whole blood / PBMC bulk + histology, n >= 200): STILL BLOCKED

Fresh checks on 2026-10-29:

- GEO `db=gds` esearch, (MASLD|MASH|NAFLD|NASH) AND (whole blood|PBMC|peripheral
  blood|leukocyte), modified 2026-10-19..2026-10-29 -> **0 new series**.
- PubMed GRIPonMASH since 2026-10-19 -> **0 new publications/deposits** (still accruing).
- The anchor remains GSE267032 (bulk WBC, n=35, 21 graded).

Nothing changed on this axis since the search report.

## 2. S-BSST1614 "phenotype table": EXISTS — the 2026-10-19 report was wrong

The search report rejected S-BSST1614 as *"deposit contains ONLY two count
matrices ... zero sample-level metadata — no phenotype file, no histology,
no scores; join impossible from deposit."* **Every part of that is incorrect.**
The Zenodo record (10.5281/zenodo.19047046, published 2026-03-16, modified
2026-05-18) has carried the annotations since before the search ran:

- `annotation_cohort1.csv` (112 rows, 168 cols)
- `annotation_cohort2.csv` (821 rows, 69 cols)
- `CodeBook_ann_cohort1.xlsx` / `CodeBook_ann_cohort2.xlsx` (column definitions)

### Label join — verified directly on 2026-10-29

| Matrix (BioStudies S-BSST1614) | Sample cols | Annotation IDs matched | Unmatched |
|---|---|---|---|
| `htseq_cohort1.txt` (12.9 MB) | 113 | **112 / 112** | 1 matrix col `RNA015845` has no annotation row |
| `htseq_cohort2.txt` (101 MB) | 821 | **821 / 821** | none |

Join key: matrix column `RNAxxxxx` <-> annotation column `SMAPLE_RNA`
(their spelling). Matrices are space-delimited; headers fetched via
`https://ftp.ebi.ac.uk/biostudies/fire/S-BSST/614/S-BSST1614/Files/`.

### Label content (from the codebooks)

**Cohort 1 (the NAFLD/NASH biomarker arm), n = 112 plasma cfRNA samples:**
- `fibrosis` / `fibrosis_AMC` = *"Fibrosis (Brunt) stage from [UZA / Verheij &
  Doukas] biopsy reading (0-4)"* — **liver biopsy, two independent readers**.
  Distribution: F0 34 / F1 22 / F2 24 / F3 15 / F4 17 (112/112 scored).
- `NAFLD_Diagnosis` = biopsy-based NAFLD dx: **102 / 112 positive**.
- `NASH_Diagnosis` = biopsy-based NASH dx: 62 NASH / 37 not / 13 NA.
- Also per-sample biopsy `BPS_NAS`, `BPS_fibrosisBrunt`, `BPS_AMC_fibrosisEPOS`
  (EPOS 0-6), steatosis/ballooning/inflammation SAF components.

**Cohort 2, n = 821 samples / ~601 patients, mixed chronic liver disease:**
- `Fibrosis` (F0-F4) = *"clinical consensus based on different sources of
  information"* — NOT pure biopsy. Per-sample and nearly complete
  (20 NA of 821).
- `NASH` = clinical-consensus NAFL/NASH/No-NAFLD.
- Biopsy (`BPS_*`) scores present for only **62 / 821 rows** (31 + 20 + 11
  across cohort tags); clinical-vs-biopsy agreement is imperfect (e.g.
  clinical F1 with BPS Brunt 2 in 11 rows) — declare provenance per column
  when used.
- NAFLD-ish etiology subset (Etiology in {NAFL, Metabolic syndrome, Diabetes
  mellitus, Obesity}): **285 samples**; Fibrosis F0 60 / F1 31 / F2 49 /
  F3 44 / F4 95 / NA 6; NASH 188 / NAFL 77 / No-NAFLD 12 / NA 8.

### What this means for the Cell-tier ladder

The whitespace doc named "S-BSST1614 phenotype table" as one of three
acceptable Cell-tier cohort options. That option is now **unblocked** —
downloadable today, CC0-licensed, label join verifiable from the deposit
itself (the GSE126848-trap test passes).

Caveats that remain (unchanged from the Oct 19 report):
1. **Specimen**: plasma cell-free RNA, not blood cells — fails the hunt
   brief's criterion 1 strictly. The report's own recommendation anticipated
   this: *"the relaxation with the best yield is specimen (accept plasma
   cfRNA)."* This is a program decision, not a data-availability block.
2. Cohort 2 is mixed-etiology (HCC-heavy); cohort 1 is the clean NAFLD arm.
3. Raw reads are behind an EGA DUA — irrelevant for using the deposited
   count matrices; only needed for re-quantitation.
4. One cohort-1 matrix column (RNA015845) lacks an annotation row.

### Sizing against the Cell-tier ask (n >= 200)

- Cohort 1 alone: n = 112 biopsy-staged NAFLD (meets the n >= 100 floor,
  not 200). Dual-reader biopsy labels are a quality feature no competitor
  benchmark has.
- Cohort 1 + cohort 2 NAFLD-etiology subset: 397 samples with F0-F4
  (112 biopsy + 285 clinical-consensus; ~45 of the 285 also have BPS
  biopsy scores). Meets n >= 200 only if clinical-consensus fibrosis is
  accepted for the extension set — declare the label source per row.

### Recommendation

If the program accepts plasma cfRNA (or re-brands the family as "blood-derived
cfRNA"), S-BSST1614 cohort 1 is the strongest new frozen family available
today: build it as `MB-89xx` (plasma cfRNA, histology-anchored) with
cohort 1 = train/test anchor (112, biopsy Brunt 0-4, two readers) and the
cohort 2 NAFLD subset as an external holdout (285, clinical-consensus F0-F4,
BPS subpanel flagged). Follow the existing freeze discipline (manifest +
SHA + test-before-train). Otherwise: keep the 6-12 month GRIPonMASH re-sweep
as the pure-blood path.

Verified 2026-10-29; artifacts: /tmp/ann1.csv, /tmp/ann2.csv, /tmp/cb1.xlsx,
/tmp/cb2.xlsx (codebook extracts), matrix header fetches.
