# Written-notes team on Nebius Token Factory, by team size (2026-10-19)

Nemotron 3 Super (nvidia/nemotron-3-super-120b-a12b), GSM8K questions 50-99 (the same 50 at every size),
answers never served from the saved-answer cache. Cost is at the placeholder prices in telepathy/llm.py
(set high on purpose, NOT yet checked against the Token Factory Prices page).

| agents | right | seconds | tokens read | tokens written | $/question (placeholder prices) |
|---|---|---|---|---|---|
| 2 | 92% | 2.8  | 416    | 358  | 0.0006 |
| 4 | 92% | 8.8  | 2,661  | 1,319 | 0.0026 |
| 6 | 96% | 13.1 | 6,723  | 2,136 | 0.0053 |
| 8 | 96% | 16.4 | 12,019 | 2,487 | 0.0078 |

Reading grows about 29x from 2 to 8 agents (every agent re-reads the earlier notes); writing about 7x.
Accuracy does not improve with team size beyond noise at n=50 (a 2-agent team already gets 92%).
This is a much bigger model than the one Telepathy runs, so these seconds are not comparable with Telepathy's.
An earlier version of these numbers was wrong (the saved-answer cache served the first agents for free); those
files are kept as *.INVALID-cached-answers.
