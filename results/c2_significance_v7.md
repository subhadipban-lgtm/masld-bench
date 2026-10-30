# C2 paired significance — candidate v7 (McNemar exact + Wilcoxon signed-rank)

Verdicts at p < 0.05: accuracy -> McNemar, MAE -> Wilcoxon (better = lower).

## Candidate: qwen3-8b-masld-v7 (`qwen3-8b-masld-v7__MB-20xx.jsonl.gz`)

60 comparisons — WIN 38 / LOSS 2 / TIE 20

| reference | task | metric | n | cand | ref | both | cand_only | ref_only | neither | mcnemar_p | wilcoxon_p | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| amazon__nova-pro-v1 | MB-2001 | accuracy | 168 | 0.6607 | 0.1667 | 27 | 84 | 1 | 56 | 4.446e-24 | 2.204e-19 | WIN |
| amazon__nova-pro-v1 | MB-2002 | accuracy | 168 | 0.2083 | 0.1726 | 6 | 29 | 23 | 110 | 0.4885 | 0.4054 | TIE |
| amazon__nova-pro-v1 | MB-2003 | accuracy | 300 | 0.4867 | 0.3300 | 55 | 91 | 44 | 110 | 6.428e-05 | 5.23e-05 | WIN |
| amazon__nova-pro-v1 | MB-2005 | mae | 168 | 1.208 | 6547.220 | 29 | 101 | 38 | 0 | 8.818e-08 | 2.085e-07 | WIN |
| amazon__nova-pro-v1 | MB-2006 | mae | 168 | 1.529 | 9178.669 | 9 | 120 | 28 | 11 | 9.106e-15 | 7.839e-17 | WIN |
| anthropic__claude-sonnet-4.5 | MB-2001 | accuracy | 168 | 0.6607 | 0.0476 | 6 | 105 | 2 | 55 | 7.123e-29 | 2.341e-23 | WIN |
| anthropic__claude-sonnet-4.5 | MB-2002 | accuracy | 168 | 0.2083 | 0.0060 | 1 | 34 | 0 | 133 | 1.164e-10 | 5.511e-09 | WIN |
| anthropic__claude-sonnet-4.5 | MB-2003 | accuracy | 300 | 0.4867 | 0.6100 | 77 | 69 | 106 | 48 | 0.006338 | 0.005159 | LOSS |
| anthropic__claude-sonnet-4.5 | MB-2005 | mae | 168 | 1.208 | 2.892e+04 | 35 | 75 | 58 | 0 | 0.1651 | 0.005366 | WIN |
| anthropic__claude-sonnet-4.5 | MB-2006 | mae | 168 | 1.529 | 3.887 | 4 | 131 | 33 | 0 | 5.076e-15 | 2.326e-17 | WIN |
| deepseek__deepseek-chat | MB-2001 | accuracy | 163 | 0.6564 | 0.6319 | 98 | 9 | 5 | 51 | 0.4240 | 0.2850 | TIE |
| deepseek__deepseek-chat | MB-2002 | accuracy | 163 | 0.2025 | 0.1718 | 3 | 30 | 25 | 105 | 0.5901 | 0.5002 | TIE |
| deepseek__deepseek-chat | MB-2003 | accuracy | 10 | 0.5000 | 0.4000 | 0 | 5 | 4 | 1 | 1 | 1 | TIE |
| deepseek__deepseek-chat | MB-2005 | mae | 162 | 1.215 | 1.778 | 29 | 97 | 36 | 0 | 1.193e-07 | 1.823e-06 | WIN |
| deepseek__deepseek-chat | MB-2006 | mae | 163 | 1.523 | 3.994 | 6 | 124 | 27 | 6 | 4.686e-16 | 3.449e-18 | WIN |
| google__gemini-2.5-pro | MB-2001 | accuracy | 168 | 0.6607 | 0.3631 | 7 | 104 | 54 | 3 | 8.548e-05 | 6.956e-05 | WIN |
| google__gemini-2.5-pro | MB-2002 | accuracy | 168 | 0.2083 | 0.1548 | 0 | 35 | 26 | 107 | 0.3057 | 0.2492 | TIE |
| google__gemini-2.5-pro | MB-2003 | accuracy | 300 | 0.4867 | 0.0067 | 1 | 145 | 1 | 153 | 3.296e-42 | 9.592e-33 | WIN |
| google__gemini-2.5-pro | MB-2005 | mae | 168 | 1.208 |  | 0 | 0 | 0 | 168 |  |  | TIE |
| google__gemini-2.5-pro | MB-2006 | mae | 168 | 1.529 |  | 0 | 0 | 0 | 168 |  |  | TIE |
| meta-llama__llama-3.3-70b-instruct | MB-2001 | accuracy | 168 | 0.6607 | 0.1905 | 32 | 79 | 0 | 57 | 3.309e-24 | 6.211e-19 | WIN |
| meta-llama__llama-3.3-70b-instruct | MB-2002 | accuracy | 168 | 0.2083 | 0.1488 | 5 | 30 | 20 | 113 | 0.2026 | 0.1573 | TIE |
| meta-llama__llama-3.3-70b-instruct | MB-2003 | accuracy | 300 | 0.4867 | 0.1533 | 26 | 120 | 20 | 134 | 1.419e-18 | 2.875e-17 | WIN |
| meta-llama__llama-3.3-70b-instruct | MB-2005 | mae | 168 | 1.208 | 1.529 | 55 | 66 | 35 | 12 | 0.002654 | 0.0006777 | WIN |
| meta-llama__llama-3.3-70b-instruct | MB-2006 | mae | 168 | 1.529 | 2384.786 | 6 | 128 | 25 | 9 | 7.268e-18 | 8.648e-19 | WIN |
| nvidia__nemotron-3-super-120b-a12b:free | MB-2001 | accuracy | 168 | 0.6607 | 0.6607 | 111 | 0 | 0 | 57 |  |  | TIE |
| nvidia__nemotron-3-super-120b-a12b:free | MB-2002 | accuracy | 168 | 0.2083 | 0.2738 | 14 | 21 | 32 | 101 | 0.1690 | 0.1308 | TIE |
| nvidia__nemotron-3-super-120b-a12b:free | MB-2003 | accuracy | 10 | 0.5000 | 0.5000 | 4 | 1 | 1 | 4 | 1 |  | TIE |
| nvidia__nemotron-3-super-120b-a12b:free | MB-2005 | mae | 168 | 1.208 | 2.024 | 36 | 100 | 32 | 0 | 2.428e-09 | 3.707e-10 | WIN |
| nvidia__nemotron-3-super-120b-a12b:free | MB-2006 | mae | 168 | 1.529 | 3.814 | 7 | 126 | 34 | 1 | 1.252e-13 | 1.647e-16 | WIN |
| openai__gpt-4.1-mini | MB-2001 | accuracy | 168 | 0.6607 | 0.6607 | 111 | 0 | 0 | 57 |  |  | TIE |
| openai__gpt-4.1-mini | MB-2002 | accuracy | 168 | 0.2083 | 0.1905 | 5 | 30 | 27 | 106 | 0.7914 | 0.6911 | TIE |
| openai__gpt-4.1-mini | MB-2003 | accuracy | 300 | 0.4867 | 0.3700 | 47 | 99 | 64 | 90 | 0.007551 | 0.006118 | WIN |
| openai__gpt-4.1-mini | MB-2005 | mae | 168 | 1.208 | 1.804 | 27 | 103 | 38 | 0 | 4.098e-08 | 5.362e-07 | WIN |
| openai__gpt-4.1-mini | MB-2006 | mae | 168 | 1.529 | 4.250 | 6 | 135 | 27 | 0 | 1.787e-18 | 2.236e-21 | WIN |
| openai__gpt-4.1 | MB-2001 | accuracy | 168 | 0.6607 | 0.5774 | 97 | 14 | 0 | 57 | 0.0001221 | 0.0001828 | WIN |
| openai__gpt-4.1 | MB-2002 | accuracy | 168 | 0.2083 | 0.1905 | 5 | 30 | 27 | 106 | 0.7914 | 0.6911 | TIE |
| openai__gpt-4.1 | MB-2003 | accuracy | 300 | 0.4867 | 0.2767 | 33 | 113 | 50 | 104 | 8.858e-07 | 8.034e-07 | WIN |
| openai__gpt-4.1 | MB-2005 | mae | 168 | 1.208 | 1.815 | 27 | 103 | 38 | 0 | 4.098e-08 | 2.844e-07 | WIN |
| openai__gpt-4.1 | MB-2006 | mae | 168 | 1.529 | 4.101 | 5 | 133 | 30 | 0 | 1.116e-16 | 2.426e-19 | WIN |
| openai__gpt-4o-mini | MB-2001 | accuracy | 168 | 0.6607 | 0.5179 | 87 | 24 | 0 | 57 | 1.192e-07 | 9.634e-07 | WIN |
| openai__gpt-4o-mini | MB-2002 | accuracy | 168 | 0.2083 | 0.1845 | 7 | 28 | 24 | 109 | 0.6778 | 0.5791 | TIE |
| openai__gpt-4o-mini | MB-2003 | accuracy | 300 | 0.4867 | 0.1867 | 15 | 131 | 41 | 113 | 3.628e-12 | 6.77e-12 | WIN |
| openai__gpt-4o-mini | MB-2005 | mae | 168 | 1.208 | 2627.841 | 50 | 74 | 33 | 11 | 9.182e-05 | 5.985e-05 | WIN |
| openai__gpt-4o-mini | MB-2006 | mae | 168 | 1.529 | 4.156 | 7 | 133 | 27 | 1 | 4.976e-18 | 3.688e-20 | WIN |
| openai__gpt-5.6-luna | MB-2001 | accuracy | 168 | 0.6607 | 0.0714 | 12 | 99 | 0 | 57 | 3.155e-30 | 2.525e-23 | WIN |
| openai__gpt-5.6-luna | MB-2002 | accuracy | 168 | 0.2083 | 0.0000 | 0 | 35 | 0 | 133 | 5.821e-11 | 3.297e-09 | WIN |
| openai__gpt-5.6-luna | MB-2003 | accuracy | 300 | 0.4867 | 0.5700 | 97 | 49 | 74 | 80 | 0.03005 | 0.02419 | LOSS |
| openai__gpt-5.6-luna | MB-2005 | mae | 168 | 1.208 | 1.714 | 7 | 10 | 4 | 147 | 0.1796 | 0.2058 | TIE |
| openai__gpt-5.6-luna | MB-2006 | mae | 168 | 1.529 |  | 0 | 0 | 0 | 168 |  |  | TIE |
| qwen__qwen-2.5-72b-instruct | MB-2001 | accuracy | 168 | 0.6607 | 0.6607 | 111 | 0 | 0 | 57 |  |  | TIE |
| qwen__qwen-2.5-72b-instruct | MB-2002 | accuracy | 168 | 0.2083 | 0.1667 | 5 | 30 | 23 | 110 | 0.4101 | 0.3363 | TIE |
| qwen__qwen-2.5-72b-instruct | MB-2003 | accuracy | 300 | 0.4867 | 0.2533 | 43 | 103 | 33 | 121 | 1.42e-09 | 1.944e-09 | WIN |
| qwen__qwen-2.5-72b-instruct | MB-2005 | mae | 168 | 1.208 | 1.613 | 45 | 82 | 41 | 0 | 0.0002756 | 0.0001152 | WIN |
| qwen__qwen-2.5-72b-instruct | MB-2006 | mae | 168 | 1.529 | 4.119 | 9 | 131 | 28 | 0 | 3.951e-17 | 3.13e-19 | WIN |
| qwen__qwen3-235b-a22b-2507 | MB-2001 | accuracy | 168 | 0.6607 | 0.4702 | 31 | 80 | 48 | 9 | 0.005925 | 0.004678 | WIN |
| qwen__qwen3-235b-a22b-2507 | MB-2002 | accuracy | 168 | 0.2083 | 0.1786 | 3 | 32 | 27 | 106 | 0.6029 | 0.5151 | TIE |
| qwen__qwen3-235b-a22b-2507 | MB-2003 | accuracy | 300 | 0.4867 | 0.0400 | 12 | 134 | 0 | 154 | 9.184e-41 | 5.464e-31 | WIN |
| qwen__qwen3-235b-a22b-2507 | MB-2005 | mae | 168 | 1.208 | 13.780 | 27 | 102 | 39 | 0 | 1.104e-07 | 1.053e-07 | WIN |
| qwen__qwen3-235b-a22b-2507 | MB-2006 | mae | 168 | 1.529 | 27.696 | 11 | 126 | 31 | 0 | 8.674e-15 | 5.712e-18 | WIN |
