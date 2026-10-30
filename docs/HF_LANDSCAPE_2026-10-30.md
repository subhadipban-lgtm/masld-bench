# Hugging Face landscape for disease-specific LLMs — 2026-10-30

Dated, keyword-level search of the HF Hub for comparable disease-specific
models (MASLD / NAFLD / MASH / liver disease / hepatology / fibrosis),
run 2026-10-30 via the public search API. Not proof of absence — HF search
is keyword-based, so a liver fine-tune under a generic name would not
surface. Phrase claims accordingly.

## Findings

| Query | Result |
|---|---|
| MASLD | 1 model: `ccfwwm/masldhepa` (Qwen3-15B GGUF, Apache-2.0, Nov 2025, ~5 downloads, **empty model card** — no training data, no benchmarks, no intended use) |
| NAFLD | 1 model: `mahendarbyra132/nafld_detection` — sklearn tabular classifier (GPL), not an LLM |
| liver disease | 3 models: Florence-2 vision fine-tune (0 downloads); skops tabular (0); unclassified (0) — **no text LLMs** |
| hepatology | **0 models** |
| MASH | 25 hits, all false positives (merge "mashups", NSFW character models) |
| fibrosis | 3 hits, all vision/segmentation (ViT liver fibrosis, kidney histology U-Net, Sirius U-Net) |

## Interpretation

- There is **no benchmarked, documented MASLD or liver-disease fine-tuned
  LLM on the Hub** as of 2026-10-30. The single MASLD-named LLM has an
  empty card and zero evaluation.
- Liver-disease ML on HF is populated on the classical/vision side
  (tabular classifiers, ViT, U-Nets) and empty on the text-LLM side.
- Our repos (`Subhadip-igtm/masld-bench-qwen3-1.7b-sft-v6`,
  `Subhadip-igtm/masld-bench-qwen3-8b-sft-v7`, plus adapter repos) are the
  first documented, benchmarked MASLD fine-tunes with published
  leaderboard rows, training recipe, and label provenance.

## Suggested wording (paper related-work)

"At the time of writing (October 2026), a search of the Hugging Face Hub
for MASLD/NAFLD/MASH/liver-disease/hepatology models returns no documented
or evaluated fine-tuned language model for liver disease: the sole
MASLD-named LLM (ccfwwm/masldhepa) carries an empty model card, and the
remaining liver-disease artifacts are tabular classifiers or
vision/segmentation models. General-purpose medical LLMs (e.g., BioMistral,
Meditron) exist but are not disease-specific and have not been evaluated on
histology-grounded omics prompts."
