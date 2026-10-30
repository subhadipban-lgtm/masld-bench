# ANALYSIS PLAN — MB-89xx plasma-cfRNA family (S-BSST1614) — FROZEN 2026-10-29

Pre-specifies the build and evaluation of a new frozen task family from the
Ghent "Grand Challenge" plasma cell-free RNA cohort (BioStudies S-BSST1614,
Zenodo 10.5281/zenodo.19047046). Follows the C3 addendum pattern: freeze the
plan before any corpus build; any deviation goes to RUNLOG with justification.

## 0. Decision log

- 2026-10-19: blood-cohort search rejected S-BSST1614 as join-impossible
  (report: docs/blood-cohort-mb86xx-search-2026-10-19/).
- 2026-10-29: re-verification shows that rejection was wrong — the Zenodo
  annotations have been present since >= 2026-05-18; label join verified
  directly (see §2). See docs/blood-cohort-status-2026-10-29.md.
- 2026-10-29 (program decision, human): **accept plasma cell-free RNA as the
  specimen for MB-89xx** ("blood-derived cfRNA transcriptome"). The strict
  whole-blood/PBMC hunt stays open on the 6-12 month GRIPonMASH re-sweep.

## 1. Source data

| Artifact | URL | Size | License |
|---|---|---|---|
| `htseq_cohort1.txt` | https://www.ebi.ac.uk/biostudies/files/S-BSST1614/htseq_cohort1.txt (fire mirror: https://ftp.ebi.ac.uk/biostudies/fire/S-BSST/614/S-BSST1614/Files/htseq_cohort1.txt) | 12.9 MB | CC0 |
| `htseq_cohort2.txt` | same path, `htseq_cohort2.txt` | 101 MB | CC0 |
| `annotation_cohort1.csv` | https://zenodo.org/records/19047046/files/annotation_cohort1.csv | 76 KB | CC0 |
| `annotation_cohort2.csv` | https://zenodo.org/records/19047046/files/annotation_cohort2.csv | 375 KB | CC0 |
| `CodeBook_ann_cohort1.xlsx` / `_cohort2.xlsx` | Zenodo, same record | 28/22 KB | CC0 |

Matrices: space-delimited htseq counts, rows = `ensembl_gene_id`, columns =
`RNAxxxxx` sample ids. Raw reads are behind an EGA DUA — NOT needed (the
processed count matrices are open). SHA-256 (sha16) of every source file is
recorded in the MANIFEST at build time.

## 2. Label join (verified 2026-10-29; re-verified by the builder)

Join key: matrix column `RNAxxxxx` <-> annotation column `SMAPLE_RNA` (their
spelling). Verified overlap: cohort 1 **112/112** (one matrix column,
`RNA015845`, has no annotation row -> excluded with a logged warning);
cohort 2 **821/821**. The builder must re-run this check and `SystemExit` on
any mismatch — the freeze-16 off-by-one lesson applies verbatim: the matrix
header HAS a `ensembl_gene_id` label column; never assume, verify shape
explicitly (space-delimited, quoted-free ids).

## 3. Inclusion rules (frozen)

**Cohort 1 -> `MB-89xx_plasmacf_test.jsonl.gz` (biopsy-anchored test)**
- All 112 annotated samples; fibrosis Brunt (UZA) present for 112/112.
- Exclude matrix column `RNA015845` (unannotated).
- NAFLD_Diagnosis flag kept (102/112 biopsy-positive); family includes all
  112 (non-NAFLD rows are F0-2 negatives) — sensitivity analysis on the
  102-NAFLD subset is pre-registered.

**Cohort 2 -> `MB-89xx_plasmacf_ext_test.jsonl.gz` (external holdout)**
- Etiology in {Non-alcoholic fatty liver (NAFL), Metabolic syndrome,
  Diabetes mellitus, Obesity} = 285 samples -> **180 unique Subject_IDs**
  (78 subjects have repeat visits). Keep ONE sample per subject:
  Baseline preferred, else earliest Visit_Date. -> n = 180.
- Require Fibrosis in F0-F4: 179/180 (1 NA -> dropped). -> n = 179
  (planned; exact n recorded in `__meta__`).

## 4. Labels and provenance (frozen)

Gold column per record, flagged in a per-item `label_source` field:

| Family | Gold | label_source | Notes |
|---|---|---|---|
| cohort 1 | `fibrosis` (Brunt 0-4, UZA biopsy reading) | `biopsy_brunt_uza` | second reader `fibrosis_AMC` (Verheij/Doukas) stored in `__meta__`; inter-reader Cohen kappa recorded at build |
| cohort 2 | `Fibrosis` (F0-F4, **clinical consensus**, NOT pure biopsy) | `clinical_consensus` | `bps_brunt` attached per item where a biopsy score exists (44/180 subjects); BPS subpanel analyses pre-registered as verification, not headline |

Pre-registered fallback: if the cohort-1 inter-reader kappa (UZA vs AMC) is
< 0.6, restrict MB-8901/8902/8905 items to concordant samples and record the
restriction in the manifest rule text.

Task label mappings:
- MB-8901 / MB-8911 (binary advanced fibrosis): F3-F4 -> `yes`, F0-F2 -> `no`.
  Planned counts: cohort 1 yes 32 / no 80; cohort 2 yes 84 / no 95 (exact at build).
- MB-8902 / MB-8912 (5-class): `F0`-`F4`. Planned: cohort 1 34/22/24/15/17;
  cohort 2 35/26/34/24/60 (minus the 1 NA).
- MB-8905 / MB-8915 (ordinal regression): numeric 0-4.

## 5. Prompt construction (frozen)

- Panel: top-200 genes by MAD (median absolute deviation), label-free,
  computed INTERNAL to each corpus (cohort 1 panel from cohort 1 matrix;
  extension panel from extension matrix) — the MB-86xx/88xx rule.
- Normalisation (program-wide rule): CPM (counts / library size x 1e6) ->
  log1p -> per-sample z-score across the panel. Values rendered to 2 dp as
  `ENSG...=value, ...` (matches MB-86xx; no symbol mapping needed).
- Record schema: `{task, split="test", sample, source, prompt, answer,
  label_source}` (+ `bps_brunt` where present); first record = `__meta__`
  with n_records, seed 20260929, built date, builder id, join evidence,
  source sha16s, kappa, batch tests.
- Prompt text (verbalizations mirror MB-86xx):
  - verbalization: "The following data come from a plasma cell-free RNA
    (cfRNA) transcriptome profile.\n"
  - 8901/8911: "Patient: plasma cfRNA profile.\nGene expression (cfRNA):
    {genes}\nBased on this profile, does the patient have advanced liver
    fibrosis (stage F3-F4 rather than F0-F2)? Answer yes or no."
  - 8902/8912: "…Which liver fibrosis stage does this profile indicate?
    Answer with one of F0, F1, F2, F3, F4."
  - 8905/8915: "…Estimate the liver fibrosis stage on the ordinal scale
    0 to 4. Answer with a single number 0, 1, 2, 3, or 4."

## 6. Batch-confound pre-checks (build time, recorded in `__meta__`)

- cohort 2: chi-squared Fibrosis x Sequencing_run, Fibrosis x QC_hospital.
  If Fibrosis is associated with run at p < 0.05 the family is flagged
  "batch-confounded" in the manifest and downstream claims are restricted
  (reported, not buried).
- cohort 1: record UZA-vs-AMC kappa and NAFLD_Diagnosis counts.

## 7. Freeze discipline

- MANIFEST version -> **v3-freeze-17**; new rule text for MB-89xx; counts
  entries for both corpus files; sha16 of source matrices + annotation CSVs.
- Test-before-train: MB-89xx is TEST-ONLY and is never train-side (rule
  added to the manifest).
- After freeze, files are never regenerated; any correction -> new freeze
  number + quarantine of the old archives (freeze-16 precedent).

## 8. Profile registry additions (platform/profiles/masld.yaml)

```yaml
tasks:
  MB-8901: yes_no
  MB-8902: f_stage
  MB-8905: number
  MB-8911: yes_no     # suffix "11" has no rule -> explicit
  MB-8912: f_stage
  MB-8915: number
  MB-8921: yes_no     # Option C AMC-gold variant pair (added 2026-10-29)
  MB-8922: f_stage
  MB-8925: number
```

## 9. Evaluation protocol (pre-registered, reuses ANALYSIS_PLAN_v1)

- LLMs: zero-shot, single pass, temperature 0.0, top_p 1.0, max 1500
  tokens; invalid-as-error validity handling; bootstrap 95% CIs (seed
  20260929). The 12-reference frontier bracket is re-run on the 89xx
  prompts (new API spend; if budget-constrained, >= 6 models per the v1
  minimum roster). Compact models: v6-1.7B and v7-8B (existing checkpoints,
  no retraining).
- Classical gates (C3a style, frozen): logreg + HGB, StratifiedGroupKFold —
  cohort 1 grouped by sample (no patient structure), cohort 2 grouped by
  Subject_ID; 2000 bootstraps, seed 20260929. Gates: binary/5-class must
  beat chance AND majority; ordinal must beat median MAE.
- Paired statistics: McNemar exact / Wilcoxon signed-rank on identical items
  vs the frontier bracket, same conventions as results/c2_significance_v7.
- C4 regime split: classical-vs-LLM on identical prompt strings extends to a
  second blood-derived family.

## 10. Falsification and outcome mapping (pre-committed)

1. Classical null (logreg ~ majority): the family is a documented negative —
   contribution = task family + negative-control matrix (86xx precedent).
2. Classical signal, LLMs at majority: C4 strengthens on a second
   blood-derived family; capacity-independence already shown at 8B.
3. LLMs read the signal: first positive omics-in-prompt result — a new
   claim; would materially strengthen the paper (and is the surprising one).

## 11. Build deliverables

1. `scripts/build_mb89xx.py` (header-shape SystemExit check, join
   verification, visit dedupe, CPM-log1p-z, top-200 MAD panels, prompt
   generation, sha16, manifest update, `__meta__`).
2. `platform/profiles/masld.yaml` diff (§8).
3. MANIFEST v3-freeze-17 + counts.
4. RUNLOG entry (this plan's execution record).
5. Sources cached under `data/sbsst1614/` with sha16 in the manifest.

## 12. Cost and risks

- Downloads ~115 MB; no GPU. Frontier re-run on ~330 (cohort 1: 112 x 3
  tasks = 336 items) + ~537 (cohort 2: 179 x 3) items x 12 models — the only
  cash item (~$10-30; halve by subsampling cohort-2 pairwise/full bracket).
- Risks: cfRNA biology (hepatocyte deconvolution available in the deposit —
  `hepatocyte_signature_deconvolution.csv` — recorded as a per-sample
  covariate, not a label); clinical-consensus labels in cohort 2 (declared
  per item); plasma is not blood cells (accepted by decision log §0);
  batch confounds (§6 pre-checks).

---

## 13. EXECUTION ADDENDUM — dry-run 2026-10-29 (sandbox only; nothing frozen)

`scripts/build_mb89xx.py` was run end-to-end in a /tmp sandbox against the
real deposits (full matrices + annotations downloaded, cohort-2 matrix
101,133,609 bytes = BioStudies-listed size). Results:

- Join re-verified: cohort 1 112/112 (unannotated `RNA015845` excluded as
  planned), cohort 2 821/821.
- Cohort 2: 285 -> 180 subjects -> **179 labeled samples**; Fibrosis x
  Sequencing_run chi2=17.9, **p=0.332 — batch clean**; 42 subjects carry a
  BPS biopsy value (planned ~44; exact count recorded in meta).
- **Cohort 1 inter-reader kappa (UZA vs AMC) = 0.384 — the §4 fallback
  TRIGGERS.** 56/112 readings concordant. Discordance is mostly adjacent
  stages (0-1: 16, 1-2: 11, 2-3: 12, 3-4: 7), with 6 two-stage jumps and
  4 AMC NAs; a linear-weighted kappa would be materially higher.
- Fallback applied per §4: anchor restricted to the 56 concordant samples.
  Resulting corpora (dry): anchor 168 items (F0 11 / F1 14 / F2 12 / F3 6 /
  F4 13), extension 537 items. Manifest v3-freeze-17 rule text records the
  restriction and the kappa.
- The 56-sample anchor is underpowered for the §9 gates (binary advanced:
  19 yes / 37 no) — stated honestly, pre-registered as such.

**Open decision for the human (changes a frozen pre-registration — requires
a RUNLOG-documented amendment, not silent deviation):**

Option A (frozen plan as written): keep the 56-sample concordant anchor;
the family leans on the 179-sample extension + the dual-reader label-noise
finding (itself citable: inter-observer fibrosis staging variability).

Option B (amendment): keep all 112 anchor samples with UZA gold, add a
per-item `reader_agreement` flag, pre-register headline = all-112 and
sensitivity = concordant-56. Uses the full anchor; discloses the noise.

Option C (amendment): anchor gold = UZA; add an MB-89xx variant pair with
AMC gold (mirrors the masked-gene contamination-control idea) — smallest
priority.

Recommendation: B, with A's 56-sample subset retained as the pre-registered
sensitivity (it costs nothing and keeps the strongest-label claim intact).
The dry-run shows the builder handles all three without code changes beyond
the restriction flag.

### Decision and freeze (2026-10-29, same day)

**Human chose Option C.** The builder was amended accordingly and executed:

- Anchor (`MB-89xx_plasmacf_test.jsonl.gz`): **112 samples × 3 tasks = 336
  items**, UZA gold, per-item `reader_agreement` flag (56 concordant / 56
  discordant) — the kappa fallback is lifted per this amendment.
- AMC variant pair (`MB-89xx_plasmacf_amcvar_test.jsonl.gz`): **108 × 3 =
  324 items** (4 AMC-NA excluded), AMC gold; prompt strings byte-identical
  to the anchor items (gene moments frozen on the anchor) — 117/324 golds
  differ, the label-noise readout.
- Extension (`MB-89xx_plasmacf_ext_test.jsonl.gz`): **179 × 3 = 537 items**,
  clinical-consensus gold, batch-clean (Fibrosis × Sequencing_run p = 0.332),
  42 subjects with BPS biopsy flags.
- **Frozen for real on the ami Drive**: MANIFEST v3-freeze-17 (14 rules,
  22 counts), corpus + source sha16 recorded, sources cached at
  `data/sbsst1614/`, RUNLOG entry added. The concordant-56 sensitivity
  analysis remains available via the `reader_agreement` flag.
- Still pending (per §9, no data blocked): frontier-bracket re-run on the
  89xx prompts, classical gates, paired statistics — the next compute step.

