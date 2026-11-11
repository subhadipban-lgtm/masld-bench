---
library_name: peft
license: apache-2.0
base_model: Qwen/Qwen3-1.7B
tags:
- masld
- liver-disease
- benchmark
- qwen3
- lora
- adapter
- research
pipeline_tag: text-generation
---

# MASLD-Bench Qwen3-1.7B SFT v6

A LoRA adapter fine-tuning **Qwen/Qwen3-1.7B** on the MASLD-Bench train
corpora (the disease-specific, histology-grounded omics-LLM benchmark).
This is a **research artifact** — evaluated on frozen retrospective
benchmark tasks, not validated for any clinical or patient-facing use.

## What it does

Reads fixed-panel gene-expression prompts (e.g., biopsy-staged liver
transcriptomics, plasma cfRNA) and answers staged clinical questions:
binary advanced fibrosis, F0–F4 staging, ordinal regression.

## Benchmark results (MASLD-Bench, freeze v3-freeze-17, zero-shot greedy)

| Task | Metric | v6-1.7B | Context |
|---|---|---|---|
| MB-2001 liver binary | accuracy | 0.667 | ties best frontier (0.661) |
| MB-2005 fibrosis regression | MAE | **1.226** | best in the 12-model frontier bracket (best frontier: 1.529) |
| MB-2006 regression | MAE | 2.162 | |
| MB-8901 cfRNA binary | accuracy | **0.634** | vs majority 0.304; logreg gate 0.723 |
| MB-8911 cfRNA extension | accuracy | 0.497 | vs majority 0.335 |
| MB-8921 cfRNA AMC-gold variant | accuracy | **0.648** | best trained-on row (label-noise control) |

Paired significance: McNemar exact / Wilcoxon signed-rank on identical
items (see MASLD-Bench `results/c2_significance_v7.csv`).

## Training

- Recipe v6 = v5 mixture + MB-12xx staged-liver pool (x4) + MB-88xx
  DRUG-seq pool (x4); ~48k examples, all train-side corpora.
- LoRA r=32, alpha=32, target modules = all Q/K/V/O/gate/up/down
  projections; LLaMA-Factory; tests frozen before training
  (test-before-train discipline).

## Repositories

- **Merged weights (ready to use):** `Subhadip-igtm/masld-bench-qwen3-1.7b-sft-v6`
- **Adapter only (for reproducibility):** `Subhadip-igtm/masld-bench-qwen3-1.7b-sft-v6-adapter`

## Loading

```python
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

# merged weights — no peft needed
tok = AutoTokenizer.from_pretrained("Subhadip-igtm/masld-bench-qwen3-1.7b-sft-v6")
model = AutoModelForCausalLM.from_pretrained(
    "Subhadip-igtm/masld-bench-qwen3-1.7b-sft-v6", dtype=torch.bfloat16)

# or the bare adapter on the Qwen3 base
from peft import PeftModel
base = AutoModelForCausalLM.from_pretrained("Qwen/Qwen3-1.7B", dtype=torch.bfloat16)
model = PeftModel.from_pretrained(
    base, "Subhadip-igtm/masld-bench-qwen3-1.7b-sft-v6-adapter").merge_and_unload().eval()
```

## Limitations (read before using)

- Trained for benchmark-format prompts only; no chat tuning, no clinical
  knowledge claims beyond the frozen corpora.
- Standard LLM failure modes apply (hallucination, format sensitivity).
- Label provenance is disclosed per family (biopsy vs clinical consensus);
  do not treat outputs as diagnostic information.
- **Not for medical use. Not validated on patients.**

## Provenance and data

- **Benchmark package (Zenodo, access restricted until publication):**
  concept DOI 10.5281/zenodo.23836159, current version
  10.5281/zenodo.23855439.
- **Retrospective registration (frozen analysis plans + run log):**
  https://osf.io/4vhbs/
- **Gated source cohort:** plasma cell-free RNA, Ghent (EGA
  EGAD50000000775 / study EGAS50000000545) under the Ghent DAC Data Usage
  Agreement. The model was trained only on train-side, non-gated corpora
  wording; no per-sample gated values ship with these repositories.
- **License:** Apache-2.0 (weights and adapters).

## Contact

Corresponding author: Wim Vanden Berghe
(wim.vandenberghe@uantwerpen.be), Department of Biomedical Sciences,
University of Antwerp. Authors: Subhadip Banerjee, Rawiwan Charoensub
(Medicinal Plant Innovation Centre, Mae Fah Luang University, Chiang Rai,
Thailand), Wim Vanden Berghe.

## Citation

Banerjee, S., Charoensub, R., Vanden Berghe, W. MASLD-Bench: a
multi-domain benchmark of language models on liver-omics tasks, with
plasma cfRNA fibrosis staging as a success case. Manuscript in preparation
(2026); benchmark package archived at 10.5281/zenodo.23836159.
