# MASLD-Bench Results Draft (v1, 2026-10-19)

Manuscript results-section skeleton. Every number is traceable to
`results/leaderboard.csv` (157 rows), `results/c2_significance.{csv,md}`
(paired McNemar/Wilcoxon, 12 frontier references), `results/c3a_gate*.json`
(grouped-CV classical gates), `results/kshot_17b.json`, and the RUNLOG.
Claims C1–C4 follow the frozen publication plan; the C2 fallback and C3
fallback were pre-specified and are the ones invoked — no post-hoc
claim-shifting.

---

## Overview paragraph (draft)

We introduce MASLD-Bench, a multi-domain omics benchmark for metabolic
dysfunction-associated steatotic liver disease comprising 15 frozen
prompt corpora (~110k items; MANIFEST v3-freeze-14): clinical liver
transcriptomics with histological endpoints, external staged cohorts
(including a newly-staged 216-biopsy cohort, GSE135251), DNAm, a
geometric-manifold compression layer, knowledge corpora (pathways,
drug–target), and four novel C3 task families (progression, blood-proxy
severity, liver→plasma proteomics, perturbation transfer). We evaluated
twelve frontier API models, two classical ML families, and six compact
fine-tuned variants (Qwen3-0.6B/1.7B × v3/v5/v6 recipes) under a single
pre-registered decoding and scoring protocol. Three findings structure
the results: (i) frontier models cannot solve fixed-panel liver-omics
tasks beyond class priors; (ii) compact models trained on the benchmark
domains win the regression tasks outright but inherit the priors
elsewhere; and (iii) neither zero-shot nor trained-on exposure transfers
omics signal to held-out domains — while a logistic regression on the
identical prompts reads the strongest novel task at 0.833. Representation
format, not scale or training, is the binding constraint. (iv) On the
plasma cell-free-RNA family added in freeze-17, this regime split
inverts: frontier LLMs and the trained-on compact models read the
binary fibrosis signal at logistic-regression level, and a five-gene
concentration analysis localizes the readable signal.

---

## C1 — Benchmark contribution (infrastructure)

- 15 frozen corpora, SHA-256 manifest, test-before-train freeze
  discipline; EPos-only frozen test after the Gubra label correction
  (freeze-6); every later corpus (85xx/86xx/87xx/88xx/12xx) frozen
  before its first evaluation.
- Novel domains added in this program: progression proxy (GSE185051,
  n=52), blood-proxy severity (GSE267032; n=21 after the freeze-16
  header fix), liver→plasma masked-
  protein + platform (MSV000094959, n=206–216), PHH FFA perturbation
  (GSE247407, n=30, donor-grouped), DRUG-seq 40-compound train pool
  (E-MTAB-15601, n=1,196), staged train pool (GSE135251 n=216 + GSE167523
  n=98).
- Table S1: corpus manifest (from prompts/MANIFEST.json).

## C2 — Compact vs frontier (paired)

Pre-specified gate: paired CI separation on ≥2 domains; the fallback
(pivot claim weight to C3/C4) was invoked because the gate was NOT met.

Paired results (McNemar exact / Wilcoxon; n=929 identical items):
- MB-2005 fibrosis MAE is the one significant family of WINS:
  1.7B-v5 1.389 vs nemotron 2.024 (p=8.7e-12), deepseek 1.778
  (p=1.9e-6), gpt-4.1-mini 1.804 (p=8.3e-8); 1.7B-v6 improves to
  1.226 — better than every frontier model (best: meta-llama 1.529)
  and the ML ElasticNet (1.76). Caveat (pre-registered): driven by
  mean-anchored prediction; rho remains ≤0.12.
- MB-2001/2002/2003: ties or losses after pairing. Neither the binary
  nor the pairwise task separates a compact model from the strongest
  frontier reference once the bracket is complete.
- The completed 12-reference bracket changes the pairwise reading:
  claude-sonnet-4.5 now leads MB-2003 at 0.610 [0.56, 0.66] (validity
  1.00), above the best compact variant (0.6B-v3, 0.593). On MB-2001 the
  best compact (1.7B-v6 0.667) and the best frontier (gpt-4.1-mini 0.661)
  are statistically indistinguishable. C2 therefore survives **only on
  regression**, and only against the reference bracket as scored.
- Full table: results/c2_significance.md (57 paired comparisons per
  candidate; 1.7B-v5: 34W/0L/23T, 0.6B: 18W/11L/28T).
- Harness note now material to interpretation: the first frontier pass
  capped output at 200 tokens, which truncated verbose reasoners before
  the verdict; a 900-token re-pass of unparsed cells and two parser
  fixes (markdown-tolerant yes/no and A/B) recovered ~1,000 records at
  no new spend. Scores reported here are post-repair; the pre-repair
  table understated Claude/Gemini/Nova by up to 0.6 accuracy.

## C3 — Novel task families (the honest ledger)

Classical gates (grouped CV, 2000 bootstraps, seed 20260929):

| Family | Task | logreg | majority | verdict |
|---|---|---|---|---|
| Progression (85xx) | 8501 / 8505 | 0.904= / MAE 0.20 | 0.904 / 0.10 | no signal (5/52 progressive) — negative control |
| Blood-proxy (86xx) | 8601/02/05 | 0.43 / 0.73 / MAE 0.73 | 0.38/0.53/0.71 | underpowered (n=21), CIs span chance — and see the freeze-16 correction |
| Plasma (87xx) | 8701 | 1.000 | 0.350 | trivial BATCH separation (not clinical) |
| Plasma (87xx) | 8705 v2 | MAE 0.814 | 0.818 | no classical win (encoder target-blind caveat) |
| **Perturbation (88xx)** | **8801** | **0.833 [0.700,0.967]** | 0.500 | **genuine signal, donor-leakage blocked** |

**freeze-16 correction (2026-10-19).** Cross-checking the independent
blood-cohort search report (docs/blood-cohort-mb86xx-search-2026-10-19/)
against our own corpus exposed a builder defect: GSE267032's TPM header
lists 35 sample names and no gene-ID column, but `build_mb86xx.py` sliced
`header[1:]`, dropping `Blood_patient_1` and pairing every remaining label
with the *previous* patient's expression. All 20 freeze-8 items were
mislabeled. The corpus is rebuilt with an explicit header-shape check
(now fails loudly on ambiguity), giving 21 patients (low 8 / medium 6 /
high 7). The four corrupted archives are quarantined under
results/quarantine/. The v6 cells were re-evaluated on freeze-16
(2026-10-19): MB-8601 0.333 = chance for both sizes; MB-8602 0.400/0.533;
MB-8605 MAE 0.95/0.81 vs the 0.714 median baseline — no blood-proxy signal
on clean labels either. The classical gate likewise still fails (no family
beats chance/majority). The row's qualitative verdict is unchanged and now
rests on corrected data; the v5-zeroshot blood cells are retired with the
quarantined archives.

LLM ledger on the same frozen tests:
- Zero-shot (v5): both sizes collapse to constants (1.7B all-"no"
  0.433; 0.6B all-"yes" 0.500 on 8801).
- **Trained-on (v6, this program's controlled experiment)**: after
  training on 40 compounds × ~8k HepG2 DRUG-seq prompts (+staged-liver
  pool), MB-8801 = 0.500 (1.7B) / 0.533 [0.367,0.700] (0.6B) — still at
  majority. Cross-model perturbation transfer does not occur at
  0.6–1.7B scale.
- k-shot ablation (BDH-CQ): demonstrations recover answer FORMAT
  (validity 0→0.77 at K=2) but not signal (all-K ≤ majority).

**C3 conclusion (per the frozen fallback):** the contribution is the
task families themselves plus a complete negative-control matrix —
no LLM evidence of omics signal transfer at compact scale.

## C4 — Representation-format regime split (the field-level lesson)

The convergent negative: across 6 compact variants, 3 training regimes,
5 test families, and K-shot conditioning, compact LLMs read omics
prompts at class-prior level wherever a linear baseline exceeds chance —
and the one novel task with strong classical signal (8801: 0.833) shows
LLM 0.500 both zero-shot AND trained-on. Conversely, on domains where
prompt text encodes the answer structurally (platform id: 0.398>v5
0.257; masked-value formats: validity 1.0), trained models learn
immediately. Structural readability, not statistical signal, is what
SFT conveys. Classical ML and LLMs occupy disjoint regimes on
fixed-panel omics — mirroring and extending the LongevityBench
observation into trained-on and cross-model transfer settings.

- v7 (Qwen3-8B QLoRA) closes the scale axis on the core family:
  MB-2005 MAE 1.208 (best in the 12-reference bracket), MB-2006 1.529
  (the v6 digit-loop resolved), MB-2002 0.208 (+4pp vs v6) — but MB-2003
  stays below claude-sonnet-4.5 (0.487 vs 0.610, paired p = 0.006) and
  gpt-5.6-luna (0.487 vs 0.570, p = 0.030), and every C3 transfer
  negative holds at 8B (8801 0.500 = chance). Scale does not rescue
  transfer (results/c2_significance_v7.md; RUNLOG 2026-10-20).
- The constraint is conditional on the data, not a property of LLMs:
  on the plasma-cfRNA family (C5) the same models read what the linear
  reader reads.

## C5 — The conditional regime split (MB-89xx plasma cfRNA, freeze-17)


### Corpus and labels (C1 extension)

Three frozen corpora from S-BSST1614 (Ghent "Grand Challenge" plasma cfRNA;
matrices htseq_cohort1/2, annotations from Zenodo 10.5281/zenodo.19047046;
join verified 112/112 and 821/821 — MANIFEST v3-freeze-17):

- **MB-89xx anchor** (336 items; 112 samples x 3 tasks): biopsy Brunt F0-F4,
  UZA reader gold; per-item `reader_agreement` flag. Second independent
  reader (Verheij/Doukas) kappa = 0.384 (56/112 concordant) — the dual-reader
  noise is the point of the variant pair below.
- **MB-892x AMC variant pair** (324 items): identical prompt strings, gold =
  the second reader; 117/324 golds differ from the anchor — a label-noise
  control with zero extra inference.
- **MB-891x extension** (537 items; 179 patients after one-sample-per-patient
  deduplication): clinical-consensus F0-F4 gold, per-item provenance flag,
  BPS biopsy subpanel (42 patients); Fibrosis x Sequencing_run p = 0.332
  (batch-clean).

Tasks: binary advanced fibrosis (F3-F4 vs F0-F2), 5-class stage, ordinal
regression. Panel: top-200 MAD genes internal per corpus; CPM -> log1p ->
per-sample z (the program-wide rule).

### Classical gates (pre-registered; gates_mb89xx.json)

| Task | logreg | majority/median | Gate |
|---|---|---|---|
| 8901 binary (anchor) | 0.723 [0.643, 0.804] | 0.304 | PASS |
| 8902 5-class (anchor) | 0.339 [0.250, 0.429] | 0.304 | FAIL |
| 8905 ordinal (anchor) | MAE 1.134 [0.955, 1.321] | 1.5 | PASS |
| 8911 binary (extension) | 0.620 [0.553, 0.687] | 0.335 | PASS |
| 8912 5-class (extension) | 0.291 | 0.335 | FAIL |
| 8915 ordinal (extension) | HGB 1.240 [1.117, 1.369] | 2.0 | PASS |

Binary advanced fibrosis carries genuine cfRNA signal; 5-class staging is a
true null at classical level — a documented negative, not an LLM failure.

### Frontier bracket (12 models, 10,476 completions; leaderboard.csv)

Headline (binary tasks, majority 0.304/0.335): gpt-4o-mini 0.670 [0.580,
0.759], qwen-2.5-72b 0.661 [0.571, 0.750], gpt-4.1-mini 0.634 on the anchor;
qwen3-235b 0.592 [0.520, 0.665] on the extension. **First LLM-positive
omics-in-prompt family in the program** — every MB-20xx/85xx/86xx/88xx task
had sat at class prior. 5-class: all models at prior (0.08-0.30),
consistent with the classical null. Ordinal: mixed — luna MAE 1.19/1.15
(rho 0.17/0.27), qwen3-235b 1.67, gpt-4.1 1.61 vs median 1.5/2.0, with the
digit-loop pathology persisting in meta-llama (2508), gpt-4.1-mini (13059),
qwen-2.5-72b (15343), gemini (31913).

### The regime split does not hold on cfRNA (C4 head-to-head, paired)

McNemar exact on identical items (c2_significance_89xx.csv):

| Task | LLM | logreg | 2x2 (both/LLM-only/lr-only/neither) | p | Verdict |
|---|---|---|---|---|---|
| 8901 | gpt-4o-mini 0.670 | 0.723 | 65/10/16/21 | 0.327 | TIE |
| 8911 | qwen3-235b 0.592 | 0.620 | 65/41/46/27 | 0.668 | TIE |
| 8901 | qwen3-8b-v7 0.589 | 0.723 | 55/11/26/20 | 0.020 | logreg WINS |
| 8911 | qwen3-8b-v7 0.525 | 0.620 | 68/26/43/42 | 0.053 | borderline |

On tissue and perturbation panels the same comparison sat at majority
(C4); on plasma cfRNA the frontier models are statistically
indistinguishable from the linear reader. The format barrier is
conditional on the data, not a property of LLMs.

### Trained-on axis (compact models, bridge-harvested)

1.7B-v6: 8901 0.634 [0.545, 0.723]; 8911 0.497; AMC variant 8921 0.648 (its
best row). 8B-v7: 8901 0.589 [0.500, 0.679]; 8911 0.525; 8921 0.583.
**Scale does not rescue** — the 8B does not beat the 1.7B on the anchor,
and loses to logreg (p = 0.020) — scale-independence now holds on both the
zero-shot and trained-on axes, mirroring the main-program v7 result.

### Label-noise control (the AMC pair; zero extra inference)

The same logistic-regression predictions score 0.389 against the UZA gold
and 0.259 against the AMC gold — a 13-point reader-noise cap on 5-class
accuracy. Frontier LLMs lose ~3 points across the same swap (8921:
gpt-4o-mini 0.639, qwen-2.5-72b 0.620). Dual-reader staging variability is
a quantifiable performance ceiling, and the benchmark is the first to
measure it directly.

### Why cfRNA is readable (post-hoc; whysplit_89xx.json)

0/20 top informative genes are cell-type Gini markers (the deposit's
hepatocyte-signature table) — the readability does not come from
deconvolution markers. Top genes are fibrosis biology (P4HA2, ELN, AMOTL2,
RGS5, SREBF1). Signal concentration: a label-informed top-5-gene panel
reaches OOF accuracy 0.714 (8901) / 0.682 (8911) vs 0.723 / 0.620 for the
full 200-gene panel — roughly five genes carry the signal, which is the
mechanistic account for the split: a few strongly deviating values are
readable by any model class, while diffuse panel-wide signal is not.

## Negative results & warts (all pre-committed in RUNLOG)

1. 0.6B-v6 degraded (empty plasma emissions, 2002 0.190 vs v5 0.202;
   MB-2006 digit-loop in 1.7B-v6, MAE 6.1e5) — mixture dilution bites
   the small model.
2. MB-8501's apparent v6 gain (0.846) is the stable PRIOR (majority
   0.904 still higher).
3. 8705 freeze-10 was degenerate (all golds saturated); rebuilt as
   masked-protein z (freeze-11) with the per-protein-z correction
   (per-sample z makes the answer arithmetic).
4. Gubra fake-label correction (freeze-6) and the unpaired-pairwise
   draw-luck correction are reported, not buried.

## Figure plan (from existing artifacts)

- F2: leaderboard heat/dot plot — models × MB-20xx tasks (leaderboard.csv).
- F3: paired C2 forest — MB-2005 MAE w/ CIs vs 9 references
  (c2_significance.csv).
- F5: C3 matrix — 5 families × {logreg, majority, 0.6B-v5/zs, 1.7B-v5/zs,
  0.6B-v6, 1.7B-v6} (leaderboard.csv + gates).
- S-kshot: demonstration-conditioning table (kshot_17b.json).
- S-geometry: raw-vs-geometry 2×2 + k-shot variants (v3_geo_ablation,
  MB-40xx rows).
- F6: MB-89xx leaderboard (binary tasks, 12 models + 2 compact + logreg gate).
- F7: C4 conditional split — identical-item McNemar panel (8901/8911):
  frontier vs logreg TIE, 8B vs logreg LOSS.
- F8: label-noise cap — same predictions vs two readers' golds (classical
  13pp, LLM ~3pp).
- S-whysplit: top-5 gene ablation + marker-overlap table.

## Limitations (draft)

Frozen test families are small (20–216 items); CIs are correspondingly
wide and several gates are underpowered by construction (pre-registered
as such). The progression family is a cross-sectional stage proxy, not
true paired-biopsy progression. The plasma platform task measures batch
separation. Frontier coverage is 9 references with partial archives for
two. The transfer experiment trains on a different cell type (HepG2)
than the test (primary hepatocytes) — negative transfer is specific to
that (biologically meaningful) axis, not to identical-domain learning,
which the format-learning results (8701, validity metrics) show does
occur.
- MB-89xx is plasma cell-free RNA, not blood cells; the strict whole-blood
  hunt remains open (GRIPonMASH re-sweep scheduled). The 5-class tasks are
  underpowered by construction (n = 112/179) and pre-registered as such.
- Cohort-2 golds are clinical consensus (biopsy subpanel n = 42); the anchor
  is dual-reader biopsy with kappa = 0.384, and both readers' golds are
  frozen as separate tasks (89xx vs 892x) rather than averaged — label
  provenance is the family's contribution, not a confound to hide.

---

## Protocol arms (2026-10-19): reasoning / graph-RAG / architecture / tool

Four pre-planned arms probe C4's boundary. Frozen user prompts stay
byte-identical; arms add compute (reasoning), context (KG system message),
architecture (diffusion LM), or tools (function calling). Full detail in
RUNLOG 2026-10-19; archives tagged `-kg` / `-reason` / `-tool` /
`inception__mercury-2.5`.

| Arm | Result | Reading |
|---|---|---|
| Reasoning ON (grok-4.7, effort low, MB-2003) | **0.697 [0.65,0.75]**, val 0.96 | **New overall best on pairwise** — above claude-sonnet (0.610) and every compact variant (0.593). Test-time reasoning PARTIALLY overcomes the format barrier; the main bracket's frontier numbers are a no-thinking lower bound. |
| Graph-RAG (Reactome/process/MASLD KG, system msg) | gpt-4.1-mini MB-2003 0.370→**0.560** (val 0.67→0.96); MB-2001 0.661→0.560 | Grounding HELPS the pairwise task substantially and HURTS the binary. Claude-KG stays truncation-bound (val 0.50 at 1,600 tokens) — reported as protocol-limited. C4 refines: format is not rescued wholesale by context, but reasoning-over-retrieved-graphs is the strongest zero-training lever found. |
| Architecture (Mercury-2.5 diffusion LM, full bracket) | MB-2003 0.437 val 0.89 (no re-pass needed); MB-2001 0.589; regression MAE degenerate (digit loops) | The format constraint is NOT autoregressive-specific — a diffusion LM lands mid-pack and inherits the same regression pathology. C4 generalizes across architecture. |
| Tool orchestration (gpt-4.1-mini + logreg tool, MB-8801) | tool acc 0.833; called 30/30; relayed 30/30; final **0.833** | The regime split resolves constructively: the LLM cannot read the profile (alone: majority 0.500) but conducts the model that can, with perfect fidelity. "LLM as orchestrator, classical ML as reader" is the deployable pattern. |

Net effect on claims: C4 stands for plain decoding across scales AND
architectures, but gains two explicit escape hatches — test-time reasoning
(grok 0.697) and retrieval-grounded reasoning (mini+KG 0.560 from 0.370) —
while tool orchestration converts the negative into a systems recipe.

## Position vs the Cell paper (LongevityBench, Zhavoronkov et al. 2026)

Their scope (per Cell + bioRxiv records): 17 tasks across ~7 biodata
domains (GTEx/TCGA transcriptomics, GEO DNAm, Olink proteomics, NHANES
clinical, SynergyAge genetics, OpenGenes text); 15–18 frontier systems
(o3 best mean rank 4.65; Gemini 3 Pro first on 6/17); zero-shot at or
near chance on omics pairwise tasks (GTEx age 0.48–0.54 ≈ random;
proteomics near-random); frontier DOES succeed on clinical/tabular tasks
(NHANES 10-yr survival 0.882, SynergyAge 0.781). The Cell version's
headline: small fine-tuned Longevity-LLMs matched or exceeded all
frontier systems.

Where we replicate them (independently, in a disease-specific domain):
- Frontier zero-shot omics failure: confirmed on every MB-20xx/86xx/88xx
  task (at/below majority; deepseek inverted 0.12 binary).
- Small-model competitiveness: confirmed on regression only — 1.7B-v6
  beats all 12 references on MB-2005 MAE (1.226 vs best 1.529). On the
  pairwise task the completed bracket puts claude-sonnet-4.5 (0.610)
  ahead of the best compact run (0.593), so the pairwise win does not
  replicate once strong references are included.

Where we extend beyond their reporting:
1. Paired significance discipline (McNemar exact / Wilcoxon on identical
   items, 929-item frame; Holm-ready) — their evaluation is rank-based;
   we show the unpaired small-model win does not survive pairing except
   on regression.
2. The controlled transfer negative: trained-on (v6, 40-compound DRUG-seq)
   still fails the held-out perturbation test (0.500 vs logreg 0.833) —
   a boundary their SFT-success headline does not map.
3. Classical-ML regime split quantified on IDENTICAL prompts (C4): the
   same items a linear model reads at 0.833 sit at majority for LLMs
   zero-shot AND trained-on.
4. Freeze/test integrity artifacts (SHA-manifested corpora, test-before-
   train, Gubra-label correction documented).

Where they are ahead of us (honest ledger):
- Scale of bracket: 15–18 frontier systems vs our 12 (credit-limited;
  the Cell-tier "6+ fully-complete bracket" item is now satisfied).
- Breadth of domains incl. proteomics-as-task (Olink) and genetics.
- Released fine-tuned models with a Cell-cover platform (toolkit).
- Their headline claim (small ≥ frontier broadly) is stronger than our
  narrower regression-family win; our paired analysis suggests their
  unpaired-style comparison may overstate breadth — testable if their
  per-item outputs are released.

NET POSITION: we are the disease-specific replication+extension: confirm
the two core phenomena, add the paired-statistics discipline and the
transfer/regime-split negatives they don't report, at the cost of a
smaller bracket and smaller test families. Realistic venue per the
pre-set ladder: Cell Metabolism / Cell Reports Medicine tier with the
current evidence; a Cell-tier resubmission would want the 9B run
(driver ready: colab/run_v7.py, Qwen3-8B QLoRA) and one large novel
cohort (e.g., a blood-proxy source with n≥200; the search brief is
docs/BLOOD_COHORT_HUNT_PROMPT.md). The 12-reference bracket is done.

Figure footnote: F2/F3 now plot all 12 references. google/gemini-2.5-pro
and gpt-5.6-luna have no parseable MB-2005 numeric predictions (scoring
skip, documented), so the regression panels show 10 of 12.
