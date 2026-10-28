# Report split result (Kaggle Tesla T4, float16, greedy) - 2026-10-11

GSM8K questions 50-199 (150 questions; the dev split 0-49 was used for choosing the step count).
torch 2.11.0+cu128, transformers 5.19.0. Model: nvidia/Llama-3.1-Nemotron-Nano-4B-v1.1,
sequential team (Planner/Critic/Refiner/Solver). Latent = 10 silent steps per agent.

| mode | n | accuracy | sec/question (avg) | p90 s | tokens written |
|---|---|---|---|---|---|
| text   | 150 | 69.3% | 71.4 | 89.6 | 1267 |
| latent | 150 | 72.7% | 16.6 | 22.4 | 283 |

latent vs text: 4.30x faster, 77.7% fewer tokens written, accuracy +3.3 points.
The accuracy difference is not statistically meaningful at n=150 (95% ranges overlap widely); the honest
claim is "same accuracy", not "better". Latent steps were chosen on the dev split (see gate_summary.md).
The per-question .jsonl files live in the Kaggle notebook output, not in this repo.
