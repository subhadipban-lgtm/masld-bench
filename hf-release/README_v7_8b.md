---
library_name: peft
license: apache-2.0
base_model: Qwen/Qwen3-8B
tags:
- masld
- liver-disease
- benchmark
- qwen3
- qlora
- adapter
- research
pipeline_tag: text-generation
---

# MASLD-Bench Qwen3-8B SFT v7

A QLoRA (4-bit NF4) adapter fine-tuning **Qwen/Qwen3-8B** on the MASLD-Bench
train corpora (the disease-specific, histology-grounded omics-LLM
benchmark). **Research artifact** — evaluated on frozen retrospective
benchmark tasks, not validated for any clinical or patient-facing use.

## What it does

Reads fixed-panel gene-expression prompts (biopsy-staged liver
transcriptomics, plasma cfRNA) and answers staged clinical questions:
binary advanced fibrosis, F0–F4 staging, ordinal regression.

## Benchmark results (MASLD-Bench, freeze v3-freeze-17, zero-shot greedy)

| Task | Metric | v7-8B | Context |
|---|---|---|---|
| MB-2001 liver binary | accuracy | 0.661 | ties best frontier |
| MB-2005 fibrosis regression | MAE | **1.208** | best across the entire 12-model bracket |
| MB-2006 regression | MAE | **1.529** | sane numerics (v6 digit-loop resolved) |
| MB-8901 cfRNA binary | accuracy | 0.589 | vs majority 0.304; logreg gate 0.723 (McNemar p=0.020) |
| MB-8911 cfRNA extension | accuracy | 0.525 | vs majority 0.335 |
| MB-8921 cfRNA AMC-gold variant | accuracy | 0.583 | |

**The scale-axis finding this model embodies:** 5x parameters over the 1.7B
buys clean numerics and ~+4pp on one task (MB-2002) — and does **not** beat
the 1.7B on the cfRNA binary task. Scale is not the binding constraint;
that negative is a result (see the benchmark paper).

## Training

- Recipe v7 = v6 mixture at Qwen3-8B, QLoRA (4-bit NF4); ~49k examples,
  all train-side corpora (staged-liver pool grew to 1,196 examples at
  freeze-15).
- LoRA r=32, alpha=32, target modules = all Q/K/V/O/gate/up/down
  projections; LLaMA-Factory on A100; tests frozen before training.

## Repositories

- **Merged weights (ready to use):** `Subhadip-igtm/masld-bench-qwen3-8b-sft-v7`
- **Adapter only (for reproducibility):** `Subhadip-igtm/masld-bench-qwen3-8b-sft-v7-adapter`

## Loading

```python
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

# merged weights — no peft needed
tok = AutoTokenizer.from_pretrained("Subhadip-igtm/masld-bench-qwen3-8b-sft-v7")
model = AutoModelForCausalLM.from_pretrained(
    "Subhadip-igtm/masld-bench-qwen3-8b-sft-v7", dtype=torch.bfloat16)

# or the bare adapter on the Qwen3 base
from peft import PeftModel
base = AutoModelForCausalLM.from_pretrained("Qwen/Qwen3-8B", dtype=torch.bfloat16)
model = PeftModel.from_pretrained(
    base, "Subhadip-igtm/masld-bench-qwen3-8b-sft-v7-adapter").merge_and_unload().eval()
```

(For 4-bit loading, add a BitsAndBytesConfig with `load_in_4bit=True`.)

## Limitations (read before using)

- Trained for benchmark-format prompts only; no chat tuning, no clinical
  knowledge claims beyond the frozen corpora.
- Standard LLM failure modes apply (hallucination, format sensitivity).
- Label provenance is disclosed per family (biopsy vs clinical consensus);
  do not treat outputs as diagnostic information.
- **Not for medical use. Not validated on patients.**

## Citation

MASLD-Bench: a disease-specific omics-LLM benchmark with histology
endpoints. Manuscript in preparation (2026).
