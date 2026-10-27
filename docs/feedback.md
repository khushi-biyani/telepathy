# Feedback for Nebius and NVIDIA

We built Telepathy (agent teams that hand over working memory instead of writing notes). Below is what we ran into, with what would have helped. We kept it to things we actually hit.

## Nebius Token Factory
**What worked well**
- The API is OpenAI-compatible, so our client worked after changing the base URL and key.
- Replies report token counts, which let us build a per-run cost ledger and enforce spending limits.
- Nemotron 3 Super was fast enough for a 4-agent team (about 15 seconds for a hard question).

**What would help**
1. **Prices in the API.** We had to copy per-token prices from the Prices page by hand. A price field on the model list (or in the usage block) would let apps show cost without a hand-edited table.
2. **State that can be passed between calls.** Each agent in a team re-sends all earlier notes, so tokens read grow fast (416 for 2 agents, 12,019 for 8, in our measurements). Cached-prompt pricing, or a way to continue from a previous call's state, would cut that. We would like to know whether prompt caching exists and how it is billed.
3. **Clearer rules on credits.** The hackathon credits are Token Factory only, and the AI Cloud free trial is suspended, so a project that needs a GPU for its own model has no free path. A small GPU allowance for hackathon teams (a few hours on an L40S) would make "runs on Nebius end to end" possible for projects like ours.

## NVIDIA Nemotron
**What worked well**
- Nemotron Nano 4B runs on a 16 GB NVIDIA Tesla T4 (free on Kaggle) in float16, which made real experiments possible.
- Nemotron 3 Super on Token Factory gave strong answers (91% on our 150-question maths set).

**What would help**
1. **A recipe for latent (hidden-state) use.** Nemotron Nano has untied input and output embeddings, so feeding the last hidden state back in as an input drifts into noise after about five steps. A short official note or utility for realigning hidden states to the embedding space would save every latent-reasoning project a lot of time.
2. **Notes on greedy decoding limits.** Many of our wrong answers were cut off by a 384-token cap; guidance on typical answer lengths per model size would help people pick sensible limits.

## About the hackathon
The key rule (call a Nebius-hosted NVIDIA model at runtime) was easy to meet once we found it, but the answers about Token Factory against AI Cloud, and about GPU credits, came from the Discord. Putting that FAQ on the main page would save new teams a day.

*[Add your own notes here: anything that went wrong for you personally with signup, billing or the console.]*
