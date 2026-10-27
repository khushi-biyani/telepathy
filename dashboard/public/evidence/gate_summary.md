# Gate result (Kaggle Tesla T4, float16, greedy) - 2026-10-11

GSM8K questions 0-49 (this is the DEV split). torch 2.11.0+cu128, transformers 5.19.0.
Model: nvidia/Llama-3.1-Nemotron-Nano-4B-v1.1, sequential team (Planner/Critic/Refiner/Solver).

| mode | accuracy | sec/question (avg) | p90 s | tokens written |
|---|---|---|---|---|
| text | 70% | 72.8 | 89.1 | 1297 |
| latent, 5 steps  | 74% | 15.9 | 21.3 | 287 |
| latent, 10 steps | 70% | 16.7 | 22.2 | 288 |
| latent, 20 steps | 68% | 18.4 | 23.7 | 292 |

Verdict: PASS (4.0-4.6x faster, ~78% fewer tokens written, accuracy -2 to +4 points).
Caveat: n=50, so one question = 2 points; the accuracy differences between modes are within noise.
First 20-question run (10 steps) read 60% vs 70% text; it was noise that closed at n=50.
The per-question .jsonl files live in the Kaggle notebook output, not in this repo.
