# Telepathy

**Tagline:** AI agents that think together, without writing it all out.

## Inspiration
Multi-agent systems split a job between specialist agents: one plans, one checks, one improves, one answers. But today they hand work to each other by writing everything out, and every agent rereads everything written before it. We measured it on Nebius Token Factory with NVIDIA Nemotron 3 Super: going from a 2-agent team to an 8-agent team, the reading per question grew from 416 tokens to 12,019, about 29 times more, while accuracy stayed the same. We wanted to know what happens if agents stop writing notes and share what they are thinking instead.

## What it does
Telepathy lets the agents in a multi-agent system hand over their **working memory** (the model's KV cache) instead of writing notes. The first agents think silently and pass that memory on; only the last agent writes, and that is the answer.

The website shows it three ways:
- **How it works:** one real recorded question, answered by the usual multi-agent flow and by Telepathy on one shared clock, replaying on a loop. You watch Telepathy finish while the usual flow is still writing its second note.
- **Try it:** featured questions in maths, coding, science and real web research, each a real recording you can replay side by side.
- **Results:** tokens per question for a single agent, a usual multi-agent system and Telepathy, with accuracy and time on hover, plus every question's time and tokens.

## What we measured
Same model (NVIDIA Nemotron Nano 4B), same GPU (NVIDIA Tesla T4), same questions, three ways of working:

| Test | Single agent | Multi-agent | Telepathy | Telepathy vs multi-agent |
|---|---|---|---|---|
| School maths (150 questions) | 79.3% | 69.3% | 72.7% | 4.3× faster, 78% fewer tokens |
| Coding (60 tasks, graded by running tests) | 43.3% | 43.3% | 55.0% | 40× faster, 98% fewer tokens |
| Medical exam (60 questions) | 33.3% | 33.3% | 41.7% | 3.4× faster, 74% fewer tokens |
| Web research (3 questions) | – | 2 of 3 | 2 of 3 | 2.9× faster, 60% fewer tokens |

Against a usual multi-agent system, Telepathy was **2.9× to 40× faster** and wrote **60% to 98% fewer tokens**, with the **same or better accuracy** on every test. On coding it also beat a single agent clearly (7 problems solved that the single agent missed, none the other way; p = 0.016). On simple school maths a single agent did best, which shows a team does not always pay off; Telepathy makes a team about as cheap as one agent.

**About the setup:** we deliberately ran everything on a small model, NVIDIA Nemotron Nano 4B, on a single NVIDIA Tesla T4, an older entry-level GPU with 16 GB, because that is what we could run end to end for every test. That is why the accuracy scores are modest for all three ways of working. A bigger model clearly helps: the usual 4-agent flow on NVIDIA Nemotron 3 Super through Nebius Token Factory scored 91.3% on the same 150 maths questions, against 69.3% on Nano 4B. With a bigger Nemotron model, accuracy would likely go up for Telepathy too. The speed and token savings come from not writing and rereading notes, so we expect them to carry over, but we have not yet tested Telepathy on a bigger model.

## How we built it
- **Telepathy engine (Python, PyTorch, Hugging Face Transformers):** each silent agent feeds the model's last internal state back in as its next input for 10 steps, building up the shared KV cache; the next agent starts from that cache. This follows the published LatentMAS method (Apache-2.0); we implemented it for NVIDIA Nemotron Nano and built the measurement, safety and website around it.
- **Nebius Token Factory:** we measured the usual multi-agent flow at 2, 4, 6 and 8 agents on NVIDIA Nemotron 3 Super through Token Factory. Our server can also run the usual flow live for website visitors, with per-run, per-visitor and total spending limits, and only on the site's own questions, never free text.
- **Safety layer:** outside content such as web pages is marked untrusted by code, never by the model. Only one agent may read it, and it must hand off in plain text that is scanned for planted instructions, so nothing untrusted travels silently. Each memory belongs to one run only.
- **Benchmarks:** GSM8K (maths), MBPP+ (coding, graded by running the official tests), MedQA (medical exam) and real web research with Tavily search. Every run is greedy and repeatable, saved one row per question, and resumable.
- **Website:** React, Vite, TypeScript and Tailwind, replaying real recordings, with a FastAPI server for the live Nebius lane.

## Challenges we ran into
- **Telepathy needs the model's memory, which an API cannot give.** Token Factory takes text in and gives text out, so the silent runs happen on a GPU we control (an NVIDIA Tesla T4 on Kaggle), while the usual flow also runs live on Nebius. We never compare the two models' seconds.
- **Long GPU runs on Kaggle notebooks** kept stopping. We made every benchmark resumable and moved long runs to background jobs.
- **A cache bug** in our first team-size run served saved answers and made agents look free. We found it, fixed it so benchmarks never use the cache, and re-ran.
- **Fair grading for code** needed the official tests run safely in a separate process; we checked the grader against all the reference solutions first.

## What we learned
- Most of the saving comes from not writing and rereading notes. A self-test we ran on ourselves (giving the agents a "wrong notebook") showed the silent thinking alone does not measurably change accuracy, so we claim speed and cost, not smarter answers.
- A readable "subtitle" of the silent thinking was something we could not verify, so we dropped it rather than overclaim.
- Measuring our own claims, including the ones that did not hold, made the project stronger.

## What's next
Run Telepathy on bigger NVIDIA Nemotron models and faster GPUs, where we expect higher accuracy for every method; measure it at more team sizes; and add the LatentMAS realignment step.

## Built with
NVIDIA Nemotron (Nano 4B, 3 Super), Nebius Token Factory, Tavily, Python, PyTorch, Hugging Face Transformers, FastAPI, React, Vite, TypeScript, Tailwind CSS, Kaggle (NVIDIA Tesla T4).

## Links
- Live demo: [DEMO URL]
- Code: https://github.com/khushi-biyani/telepathy
- Video: [VIDEO URL]
