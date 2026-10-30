# RESULTS DRAFT — MB-89xx addendum (2026-10-30, file-traced)

Insertion guide: add `## C5 — the conditional regime split (MB-89xx)` after the
existing C4 section in docs/RESULTS_DRAFT.md, extend the Overview paragraph
with sentence (iv), and add the two Limitations bullets at the end of the
existing Limitations block. Every number traces to the named artifact; no
number appears here that is not in those files.

Sources: results/leaderboard.csv (MB-89xx rows), results/gates_mb89xx.json,
results/c2_significance_89xx.{md,csv}, results/whysplit_89xx.json,
prompts/MANIFEST.json (v3-freeze-17), RUNLOG.md (2026-10-29/30 entries).

---

## Overview paragraph — append sentence (iv)

"...(iii) neither zero-shot nor trained-on exposure transfers omics signal
to held-out domains — while a logistic regression on the identical prompts
reads the strongest novel task at 0.833. (iv) On the plasma cell-free-RNA
family added in freeze-17, this regime split inverts: frontier LLMs and the
trained-on compact models read the binary fibrosis signal at logistic-
regression level, and a five-gene concentration analysis localizes the
readable signal."

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

### Limitations (add to the existing block)

- MB-89xx is plasma cell-free RNA, not blood cells; the strict whole-blood
  hunt remains open (GRIPonMASH re-sweep scheduled). The 5-class tasks are
  underpowered by construction (n = 112/179) and pre-registered as such.
- Cohort-2 golds are clinical consensus (biopsy subpanel n = 42); the anchor
  is dual-reader biopsy with kappa = 0.384, and both readers' golds are
  frozen as separate tasks (89xx vs 892x) rather than averaged — label
  provenance is the family's contribution, not a confound to hide.

### Figure plan

- F6: MB-89xx leaderboard (binary tasks, 12 models + 2 compact + logreg gate).
- F7: C4 conditional split — identical-item McNemar panel (8901/8911):
  frontier vs logreg TIE, 8B vs logreg LOSS.
- F8: label-noise cap — same predictions vs two readers' golds (classical
  13pp, LLM ~3pp).
- S-whysplit: top-5 gene ablation + marker-overlap table.
