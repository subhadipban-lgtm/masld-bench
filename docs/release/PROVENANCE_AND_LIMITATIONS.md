# Provenance, eligibility and limitations

## Dataset accessions

| Family | Accession / source | Role |
|---|---|---|
| Tissue test, MB-20xx and MB-40xx | GSE135251 (Govaere et al., *Sci Transl Med* 2020;12(572):eaba4448), obtained through the Kamzolas et al. supplementary deposit | Frozen test surface; 168 of 216 staged samples |
| Staged-liver SFT pool, MB-12xx | GSE135251, GSE167523, GSE130970 | Training pool used by v6/v7 mixtures |
| Plasma cfRNA, MB-89xx | S-BSST1614; annotations at Zenodo 10.5281/zenodo.19047046 | Frozen test and reader comparison; DUA-gated |
| Other public families | GSE185051, GSE267032, MSV000094959, GSE247407, E-MTAB-15601 | Test or training families as documented in the project manifest |

The MB-20xx matrix identity was established by matching all 168 sample
identifiers to the GSE135251 GEO records and by expression agreement with the
raw counts (Pearson r = 0.999996 for one matched sample). This does not reconstruct the
complete source-file/build chain.

## Training exposure and eligibility

All 168 MB-20xx test samples occur in MB-12xx. The v6/v7 mixtures upsample
MB-12xx four-fold. Therefore Qwen3-0.6B v6, Qwen3-1.7B v6 and Qwen3-8B v7 are
excluded from the primary tissue roster and reported only as diagnostics.
Earlier v3/v5 checkpoints were not exposed through the documented project
fine-tuning mixtures. Proprietary-model pretraining content is not established.

Forty-two shared samples have different binary labels because MB-1201 uses an
F2–F4 threshold and MB-2001 uses F3–F4. They are different task definitions,
not silently interchangeable labels.

An all-corpus comparison covered 11 training files and 15 test files. It found
the expected GSE135251 overlaps and no additional exact-ID overlaps within the
inspected comparisons. This is not a universal patient-identity exclusion.
No v6/v7 MB-40xx response archives were found.

## Evaluated-item manifest rules

- Primary roster: every model with all five tissue tasks, minus the three
  exposed checkpoints (17 models).
- Common archived items: 163 binary, 163 five-class, 162 fibrosis regression
  and 163 NAS regression.
- Pairwise results are grouped by exact item-set manifest: 14 eligible models
  on 300 shared items, DeepSeek/Nemotron on 258 in-corpus items, and Gemini on
  414 items. They are not merged into one cross-manifest ranking.
- Archive absence is recorded as not archived, not silently scored as an error.
- Response archives do not contain prompt text. The verified join is
  `(task, sample, gold)`; prompt-byte identity cannot be established from the
  archives.
- Regression reports model-specific conditional denominators. The direct
  Qwen3-1.7B v5 versus Llama 3.3 70B sensitivity uses 150 jointly parsed items
  (MAE 1.127 versus 1.517) and does not replace failure-aware reporting.
- The aligned five-class gold distribution is F0=31, F1=35, F2=42, F3=43,
  F4=12. Observed majority = 43/163 = 0.264; uniform-choice chance = 0.200.

## Missing-source inventory

- `build_mb12xx.py` is not preserved in either the Drive workspace or GitHub.
- Original EPoS/Kamzolas files (`EPoS_counts.tsv.zip`, `epos_metadata.csv` and
  the Kamzolas batch-corrected CSVs) are absent locally; recorded checksums pin
  the frozen corpora.
- Some older archives contain rows from a superseded pre-rebuild corpus with
  out-of-domain stages. Current scores restrict analysis to the frozen corpus
  and report those rows in the coverage audit.
- K-shot demonstration provenance is not fully traced.
- Visual acceptance of figures and rendered manuscripts is not established by
  the release tests.

## Supersession

`analysis/v2_corrections.json` and `analysis/tissue_eligible.json` are the
current analysis artifacts. Legacy leaderboards and older analysis JSON files
are historical snapshots, not current result authority. See
`results/RESULTS_AUTHORITY.md`.
