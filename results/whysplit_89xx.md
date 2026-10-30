# Why is the MB-89xx binary signal readable? (post-hoc explanation, 2026-10-30)

Post-hoc analysis (not pre-registered) of why frontier LLMs read the
plasma-cfRNA binary advanced-fibrosis signal (8901: gpt-4o-mini 0.670 vs
logreg 0.723, McNemar p=0.33 TIE) while every tissue/perturbation family
sat at class prior. Artifacts: results/whysplit_89xx.json;
script scripts/whysplit_89xx.py.

## Finding 1 — the hepatocyte-marker hypothesis is REJECTED

Cross-referenced the top-20 informative genes per task against the deposit's
own cell-type Gini marker table (`hepatocyte_signature_deconvolution.csv`,
152 genes: EPCAM+ bile duct / Hepatocytes / LSEC / MVEC):

- 8901 anchor: **0/20** top genes are strong (Gini >= 0.9) cell-type markers.
- 8911 extension: **0/20**.

The signal does not ride on the deconvolution markers. Top genes instead
include bona-fide fibrosis-relevant biology (post-hoc, descriptive):
AMOTL2, RGS5, P4HA2 (collagen prolyl 4-hydroxylase), ELN (elastin), SREBF1,
XAF1, HID1. Direction: P4HA2/ELN/AMOTL2 higher in advanced fibrosis.

## Finding 2 — the signal is highly concentrated: top-5 genes ~ full panel

Label-informed ablation (post-hoc: top-k genes by |AUC-0.5|, NOT a new
frozen panel), OOF logreg:

| top-k | 8901 anchor | 8911 extension |
|---|---|---|
| 5 | **0.714** | **0.682** |
| 10 | 0.679 | 0.654 |
| 20 | 0.652 | 0.637 |
| 50 | 0.688 | 0.687 |
| 200 (frozen panel) | 0.723 | 0.620 |

~5 genes carry the binary signal; the remaining 195 genes add ~1pp (anchor)
or noise (extension). Readability explanation: a handful of strongly
deviating values in a 200-gene prompt are trivially extractable by both a
linear model and an LLM — unlike the diffuse, panel-wide signal of the
tissue families.

## Finding 3 — item contrast (descriptive)

LLM-vs-logreg agreement by item max|z|: 0.923 on low-contrast items vs
0.679 on high-contrast items (spearman -0.32). The models diverge where the
values are most extreme — the LLM is NOT simply reading the outliers; if
anything it differs from the linear model exactly there.

## Caveats

- Top-k selection is label-informed (post-hoc explanation only; the frozen
  panel and gates are unchanged).
- n=112 anchor limits confidence on Finding 2; extension (n=179) agrees.
- Hepatocyte Gini table covers 152 genes; "no marker overlap" is within
  that table's scope.

## Follow-up candidates

- Direction/effect-size table for the top-5 genes (symbols + fold-change)
  for the manuscript supplement.
- Compact models (v6-1.7B, v7-8B) on 89xx via Colab: does the trained-on
  scale axis also read the signal? (notebook prepared: colab/
  10_compact_89xx_eval.ipynb)
- Same concentration analysis for 8905 ordinal (the second LLM-positive
  task class).
