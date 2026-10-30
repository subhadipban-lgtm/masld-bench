# C2 paired significance — MB-89xx (2026-10-29/30)

McNemar exact on identical items; verdict at p < 0.05.

## MB-8901 — best LLM openai__gpt-4o-mini (0.6696) vs the bracket

| reference | n | cand | ref | both | cand_only | ref_only | neither | mcnemar_p | verdict |
|---|---|---|---|---|---|---|---|---|---|
| amazon__nova-pro-v1 | 112 | 0.6696 | 0.4018 | 42 | 33 | 3 | 34 | 0.0 | WIN |
| anthropic__claude-sonnet-4.5 | 112 | 0.6696 | 0.1339 | 8 | 67 | 7 | 30 | 0.0 | WIN |
| deepseek__deepseek-chat | 112 | 0.6696 | 0.5089 | 50 | 25 | 7 | 30 | 0.002102 | WIN |
| google__gemini-2.5-pro | 112 | 0.6696 | 0.0000 | 0 | 75 | 0 | 37 | 0.0 | WIN |
| meta-llama__llama-3.3-70b-instruct | 112 | 0.6696 | 0.2589 | 28 | 47 | 1 | 36 | 0.0 | WIN |
| nvidia__nemotron-3-super-120b-a12b:free | 112 | 0.6696 | 0.0000 | 0 | 75 | 0 | 37 | 0.0 | WIN |
| openai__gpt-4.1-mini | 112 | 0.6696 | 0.6339 | 64 | 11 | 7 | 30 | 0.480682 | TIE |
| openai__gpt-4.1 | 112 | 0.6696 | 0.0536 | 5 | 70 | 1 | 36 | 0.0 | WIN |
| openai__gpt-5.6-luna | 112 | 0.6696 | 0.4196 | 33 | 42 | 14 | 23 | 0.000234 | WIN |
| qwen__qwen-2.5-72b-instruct | 112 | 0.6696 | 0.6607 | 70 | 5 | 4 | 33 | 1.0 | TIE |
| qwen__qwen3-235b-a22b-2507 | 112 | 0.6696 | 0.4643 | 26 | 49 | 26 | 11 | 0.010582 | WIN |

## MB-8911 — best LLM qwen__qwen3-235b-a22b-2507 (0.5922) vs the bracket

| reference | n | cand | ref | both | cand_only | ref_only | neither | mcnemar_p | verdict |
|---|---|---|---|---|---|---|---|---|---|
| amazon__nova-pro-v1 | 179 | 0.5922 | 0.2011 | 17 | 89 | 19 | 54 | 0.0 | WIN |
| anthropic__claude-sonnet-4.5 | 179 | 0.5922 | 0.3073 | 35 | 71 | 20 | 53 | 0.0 | WIN |
| deepseek__deepseek-chat | 179 | 0.5922 | 0.4358 | 44 | 62 | 34 | 39 | 0.005573 | WIN |
| google__gemini-2.5-pro | 179 | 0.5922 | 0.0168 | 2 | 104 | 1 | 72 | 0.0 | WIN |
| meta-llama__llama-3.3-70b-instruct | 179 | 0.5922 | 0.2123 | 21 | 85 | 17 | 56 | 0.0 | WIN |
| nvidia__nemotron-3-super-120b-a12b:free | 179 | 0.5922 | 0.0000 | 0 | 106 | 0 | 73 | 0.0 | WIN |
| openai__gpt-4.1-mini | 179 | 0.5922 | 0.5419 | 47 | 59 | 50 | 23 | 0.44367 | TIE |
| openai__gpt-4.1 | 179 | 0.5922 | 0.0559 | 5 | 101 | 5 | 68 | 0.0 | WIN |
| openai__gpt-4o-mini | 179 | 0.5922 | 0.5196 | 45 | 61 | 48 | 25 | 0.250282 | TIE |
| openai__gpt-5.6-luna | 179 | 0.5922 | 0.3408 | 47 | 59 | 14 | 59 | 0.0 | WIN |
| qwen__qwen-2.5-72b-instruct | 179 | 0.5922 | 0.5307 | 45 | 61 | 50 | 23 | 0.342581 | TIE |

## LLM vs logreg on identical items (C4 regime split)

| task | llm | llm_acc | logreg_acc | n | both | llm_only | logreg_only | neither | mcnemar_p | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| MB-8901 | openai__gpt-4o-mini | 0.6696 | 0.7232 | 112 | 65 | 10 | 16 | 21 | 0.32694 | TIE |
| MB-8911 | qwen__qwen3-235b-a22b-2507 | 0.5922 | 0.6201 | 179 | 65 | 41 | 46 | 27 | 0.668285 | TIE |
