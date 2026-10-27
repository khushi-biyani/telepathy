<div align="center">

# Telepathy

**AI agents that think together, without writing it all out.**

Multi-agent systems spend much of their time writing to each other.
Telepathy lets agents share their working memory instead, on NVIDIA Nemotron.

**2.9× to 40× faster** · **60% to 98% fewer tokens** · **same or better accuracy**
<sub>than a usual multi-agent system on the same model and the same questions</sub>

</div>

---

## Contents

1. [The problem](#1-the-problem)
2. [The idea](#2-the-idea)
3. [Results](#3-results)
4. [How it works](#4-how-it-works)
5. [Project layout](#5-project-layout)
6. [Run it yourself](#6-run-it-yourself)
7. [Configuration](#7-configuration)
8. [Troubleshooting](#8-troubleshooting)
9. [What we do not claim](#9-what-we-do-not-claim)
10. [Credits](#10-credits)

---

## 1. The problem

A multi-agent system splits a job between specialist agents. In our demo team a **Planner** makes a plan, a **Critic** checks it, a **Refiner** improves it and a **Solver** writes the answer.

Today those agents hand work to each other by **writing everything out**. Each agent writes its full reasoning, and the next agent has to read all of it before it can start. Add an agent and there is more to write and far more to read, so every agent you add costs time and money.

We measured it on Nebius Token Factory with NVIDIA Nemotron 3 Super (the same 50 maths questions at every team size):

| Agents in the team | Tokens read per question | Tokens written | Seconds per question | Right answers |
|---:|---:|---:|---:|---:|
| 2 | 416 | 358 | 2.8 | 92% |
| 4 | 2,661 | 1,319 | 8.8 | 92% |
| 6 | 6,723 | 2,136 | 13.1 | 96% |
| 8 | **12,019** | 2,487 | 16.4 | 96% |

Going from 2 to 8 agents, reading grows about **29×** while accuracy stays within noise. Most of the extra cost is agents re-reading each other.

## 2. The idea

What if the agents skipped the notes and handed over what they are thinking?

When a language model reads text, it builds a working memory of what it has understood so far (technically, its **KV cache**). Normally that memory is thrown away after each answer, and the next agent rebuilds it by reading text. Telepathy keeps it and passes it on.

```
Usual multi-agent flow
  Planner ──writes notes──▶ Critic ──writes notes──▶ Refiner ──writes notes──▶ Solver ──▶ answer
           (every agent writes in full; the next one rereads everything so far)

Telepathy
  Planner ══memory══▶ Critic ══memory══▶ Refiner ══memory══▶ Solver ──▶ answer
  (thinks silently)   (thinks silently)   (thinks silently)    (the only one that writes)
```

Each of the first three agents thinks for 10 **silent steps**: instead of writing a word, the model feeds its own last internal state back in as the next input. Their thinking accumulates in the shared memory, and only the Solver writes, which is the answer.

> The silent hand-off follows the published **LatentMAS** method ([paper](https://arxiv.org/abs/2511.20639), [code](https://github.com/Gen-Verse/LatentMAS), Apache-2.0). We implemented it for NVIDIA Nemotron and built the measurement, the safety layer and the website around it.

![How Telepathy works: the usual multi-agent flow, the Telepathy flow, how the memory is passed, and what we measured](docs/architecture.svg)

A visual, end-to-end version of this flow is in [`docs/architecture.excalidraw`](docs/architecture.excalidraw) (open it at [excalidraw.com](https://excalidraw.com)).

## 3. Results

Everything below uses **one model** (NVIDIA Nemotron Nano 4B) on **one GPU** (NVIDIA Tesla T4 on Kaggle), answering the **same questions three ways**: a single agent, a usual multi-agent system (4 agents writing notes), and Telepathy (the same 4 agents sharing memory). Decoding is greedy, so every run is repeatable.

| Test | Questions | | Single agent | Multi-agent | **Telepathy** | Telepathy vs multi-agent |
|---|---:|---|---:|---:|---:|---|
| **School maths** (GSM8K) | 150 | right | 79.3% | 69.3% | **72.7%** | **4.3× faster, 78% fewer tokens** |
| | | seconds | 13.6 | 70.2 | 16.4 | |
| | | tokens | 291 | 1,267 | 283 | |
| **Coding** (MBPP+) | 60 | right | 43.3% | 43.3% | **55.0%** | **40× faster, 98% fewer tokens** |
| | | seconds | 3.8 | 188.4 | 4.7 | |
| | | tokens | 77 | 2,723 | 55 | |
| **Medical exam** (MedQA) | 60 | right | 33.3% | 33.3% | **41.7%** | **3.4× faster, 74% fewer tokens** |
| | | seconds | 17.3 | 96.5 | 28.1 | |
| | | tokens | 316 | 1,427 | 377 | |
| **Web research** | 3 | right | – | 2 of 3 | **2 of 3** | **2.9× faster, 60% fewer tokens** |
| | | seconds | – | 230.7 | 80.5 | |
| | | tokens | – | 3,045 | 1,228 | |

<sub>Seconds and tokens are averages per question. "Tokens" are tokens written. Coding answers are graded by running the official hidden tests; maths and medical answers against the known answer; research answers against a known number. Maths allowed up to 384 tokens per agent; the other tests up to 1,024.</sub>

**What this shows**

- **Speed and cost:** against the usual multi-agent system, Telepathy was faster and wrote far fewer tokens on **every** test.
- **Accuracy:** Telepathy was at least as accurate as the usual multi-agent system on every test.
- **Where it clearly won:** on coding, Telepathy solved 7 problems the single agent missed and missed none the single agent solved (sign test, p = 0.016).
- **Where it did not:** on simple school maths, **a single agent beat both teams** (79% against 73% and 69%). A team does not always pay off. Telepathy makes a team about as cheap as one agent; it does not make the model smarter.

<details>
<summary><b>Is the accuracy difference real? The statistics</b></summary>

We compare two ways question by question and count the questions only one of them got right. p is the chance a gap that size happens by luck (two-sided sign test).

| Test | Telepathy vs multi-agent | Telepathy vs single agent |
|---|---|---|
| School maths | 24 vs 19, p = 0.54 | 8 vs 18, p = 0.08 |
| Coding | 11 vs 4, p = 0.12 | **7 vs 0, p = 0.016** |
| Medical exam | 13 vs 8, p = 0.38 | 15 vs 10, p = 0.42 |

We ran several comparisons, so a single small p is strong evidence, not certainty. The honest summary is: much faster and cheaper at the same or better accuracy, with one clear accuracy win on coding.
</details>

<details>
<summary><b>A test we ran on ourselves: does the silent thinking carry information?</b></summary>

Speed alone does not prove the agents pass useful thoughts. So on 50 maths questions we ran three versions of Telepathy:

| Version | Right |
|---|---:|
| Normal (10 silent steps per agent) | 35 / 50 |
| No thinking (0 silent steps) | 37 / 50 |
| Wrong notebook (the silent agents think about a different question) | 32 / 50 |

The differences are within luck at this size. So we do **not** claim the silent thinking itself improves answers. The saving comes from not writing and re-reading notes. Files: [`bench/mismatch_bench.py`](bench/mismatch_bench.py).
</details>

<details>
<summary><b>Things that did not work</b></summary>

- **Readable "subtitles" of the silent thinking.** We tried to show a readable summary of what each silent agent passes on and check it was faithful. Our check could not tell real subtitles from fake ones, so we do not claim them.
- **Research with a step-by-step writer.** On generated read-then-calculate questions, the small model did badly whichever way the agents talked, and telling the writer to work step by step did not help ([`bench/research_bench.py`](bench/research_bench.py)).
- **Our first team-size run** reused saved answers and looked almost free. We found it, fixed it (benchmarks never use the answer cache) and re-ran. The bad files are kept as `*.INVALID-cached-answers`.
</details>

## 4. How it works

```
          question (+ web pages for research)
                         │
                         ▼
┌──────────────────────────────────────────────┐
│ Safety rules (trust.py, policy.yaml)         │  outside content is UNTRUSTED;
│                                              │  only one agent may read it,
└──────────────────────────────────────────────┘  and it must hand off in text
                         │
          ┌──────────────┴──────────────┐
          ▼                             ▼
  Usual multi-agent flow          Telepathy engine
  (baseline_tf.py on Nebius,      (engine.py + latent.py on a GPU)
   or engine.py "text" mode)        silent steps, shared KV cache
          │                             │
          └──────────────┬──────────────┘
                         ▼
          Benchmarks and recordings (bench/)
          graded by code, saved row by row
                         │
                         ▼
          Website (dashboard/) replays recordings;
          live lane (server/) calls Nebius Token Factory
```

<details open>
<summary><b>The Telepathy engine</b> · <code>telepathy/engine.py</code>, <code>telepathy/latent.py</code></summary>

- **Loading:** one NVIDIA Nemotron Nano 4B model is loaded once and shared by all four roles ([`config.py`](telepathy/config.py)).
- **Silent steps:** an agent reads its prompt, then for each silent step the model's last hidden state is rescaled to the size of a normal word embedding and fed back in as the next input ([`latent.py`](telepathy/latent.py)). No words are produced, and the KV cache grows.
- **Hand-off:** the next agent starts from that same KV cache, so it "remembers" everything the earlier agents read and thought, without reading any notes.
- **Answer:** only the final agent decodes text.
- **Modes:** `single` (one agent), `text` (usual flow: every agent writes), `latent` (Telepathy) and `auto` (Telepathy with optional checks), so all ways run on identical code paths.
- **Roles:** wording for each role and task (maths, logic, coding, science, research) lives in [`roles.py`](telepathy/roles.py). Team sizes `team2`…`team8` are defined there too.
</details>

<details>
<summary><b>The safety layer</b> · <code>telepathy/trust.py</code>, <code>scan.py</code>, <code>cache_utils.py</code>, <code>policy.yaml</code></summary>

Passing hidden memory between agents creates a new risk: a planted instruction in a web page could travel silently. So:

- **Trust is set by code, never by the model.** Every piece of content carries a source. User input is trusted; web pages are untrusted, and nothing at runtime can upgrade them.
- **One reader.** Only one agent in a team may read outside content.
- **Tainted hand-offs are in text.** That agent must hand off in plain, readable text, decoded on a copy of the memory so raw untrusted tokens never enter the shared cache.
- **Scanned.** That text is checked for planted instructions; a scan can warn or block, never clear.
- **Memory belongs to one run.** Every cache is bound to its run id and refuses to be used by another; run state cannot be pickled or saved.
- **No secrets in prompts.** Prompts are checked for keys before they reach the model.
</details>

<details>
<summary><b>Nebius Token Factory</b> · <code>telepathy/llm.py</code>, <code>telepathy/baseline_tf.py</code></summary>

- An OpenAI-compatible client for **Nebius Token Factory** (NVIDIA Nemotron 3 Super), with a per-call cost estimate, a per-check cap and a lifetime budget saved to disk.
- `baseline_tf.py` runs the usual multi-agent flow on Token Factory, either as a benchmark or as a live stream of events for the website.
- Benchmarks and live runs never use the saved-answer cache, so a cached answer can never look free.
- Telepathy itself cannot run on an API: it needs the model's internal memory, which text-in, text-out APIs do not expose. That is why the silent runs happen on a GPU we control.
</details>

<details>
<summary><b>Benchmarks and grading</b> · <code>bench/</code></summary>

- **Tests:** GSM8K (school maths), MBPP+ (Python coding, graded by running the official EvalPlus tests in a separate process with a time limit), MedQA (US medical licensing exam, 4 options) and ARC (science). Loaders in [`datasets.py`](bench/datasets.py).
- **Splits:** the first 50 items of each test are a development split (used for choosing settings); results come from items 50 onward, which we never tuned on.
- **Resumable:** every run appends one JSON row per question, and finished questions are skipped on re-run, so a stopped Kaggle session loses nothing.
- **Key scripts:** `run_bench.py` (main benchmark), `teamsize.py` (team sizes on Nebius), `mismatch_bench.py` (the self-test), `record_gallery.py` and `record_animation_local.py` (recordings for the website), `build_site_results.py` and `build_gallery_index.py` (turn results into website data).
</details>

<details>
<summary><b>The website</b> · <code>dashboard/</code> (React, Vite, TypeScript, Tailwind)</summary>

- **How it works:** a live animation of one real recorded run, both flows on one shared clock.
- **Try it:** featured questions (maths, coding, research, science), each a real recording you can replay side by side.
- **Results:** tokens per question for each way, with accuracy and time on hover, plus every question's time and tokens.
- Runs as a static site from recordings, with no GPU and no keys. When the API server runs with live mode on, each featured question can also be run live on Nebius Token Factory, within spending limits. Visitors cannot type free text to the live endpoint.
</details>

## 5. Project layout

```
telepathy/
├── telepathy/              the engine
│   ├── engine.py             teams, modes and the run loop
│   ├── latent.py             silent thinking steps
│   ├── roles.py              agent roles, task wording, team sizes
│   ├── trust.py  scan.py     the safety layer
│   ├── cache_utils.py        cache binding and copying
│   ├── llm.py                Nebius Token Factory client with budgets
│   ├── baseline_tf.py        the usual flow on Token Factory
│   └── tools/tavily.py       web search for research questions
├── bench/                  benchmarks, recordings, website data builders
│   └── results/              raw results (one JSON row per question)
├── server/                 FastAPI server: replays, live Nebius lane, limits
├── dashboard/              the website
├── tests/                  112 tests (run on CPU with a tiny model)
├── docs/                   architecture diagram, Devpost text, feedback
└── policy.yaml             safety policy, read at start-up
```

## 6. Run it yourself

Pick the path you need. Each one is independent.

| I want to… | Needs | Section |
|---|---|---|
| See the website | Node.js | [6.1](#61-the-website-no-gpu-no-keys) |
| Run the tests | Python | [6.2](#62-python-and-the-tests) |
| Use the live Nebius lane | Python, a Nebius key | [6.3](#63-the-api-server-and-the-live-nebius-lane) |
| Reproduce the Telepathy results | a GPU (a free Kaggle T4 works) | [6.4](#64-reproduce-the-results-on-a-gpu) |
| Reproduce the team-size results | Python, a Nebius key | [6.5](#65-the-usual-flow-on-nebius-token-factory) |

**Prerequisites:** Python 3.11 or newer, Node.js 20 or newer. A GPU is only needed for 6.4.

### 6.1 The website (no GPU, no keys)

```bash
cd dashboard
npm install
npm run dev
```

Open the address it prints (usually http://localhost:5173). Everything on the site is replayed from recordings in `dashboard/public/` and `dashboard/src/data/`.

To build a static copy for hosting: `npm run build`, then serve `dashboard/dist/`.

### 6.2 Python and the tests

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m pytest -q
```

The tests run on a CPU with a tiny model (SmolLM2-135M, about 270 MB, downloaded once), so they need no GPU and no keys.

### 6.3 The API server and the live Nebius lane

```bash
cp .env.example .env               # then put your NEBIUS_API_KEY in .env (never commit it)
TF_LIVE=1 uvicorn server.app:app --port 8000
```

In another terminal, run the website (6.1). It forwards `/api` to port 8000. Each "Try it" question now shows **Also run the usual flow live on Nebius**. Without `TF_LIVE=1` the server only replays recordings and spends nothing.

Live runs are capped by default at $0.03 per run, 6 per visitor per hour, 3 at once, and $3 in total. See [Configuration](#7-configuration).

### 6.4 Reproduce the results on a GPU

The Telepathy engine needs direct access to the model, so it runs on a GPU. A free **Kaggle** notebook with **GPU T4 x2** works.

1. Zip the project (without `.env`) and upload it as a private Kaggle dataset.
2. In a notebook with GPU and Internet on, add the dataset, then run:

```python
!pip install -q transformers==5.19.0 datasets==5.1.0 openai python-dotenv httpx
import glob, os, shutil, zipfile
os.makedirs('/kaggle/working/repo', exist_ok=True)
hits = glob.glob('/kaggle/input/**/bench/run_bench.py', recursive=True)
if hits:
    shutil.copytree(os.path.dirname(os.path.dirname(hits[0])), '/kaggle/working/repo', dirs_exist_ok=True)
else:
    code = [z for z in glob.glob('/kaggle/input/**/*.zip', recursive=True) if 'bench/run_bench.py' in zipfile.ZipFile(z).namelist()]
    zipfile.ZipFile(code[0]).extractall('/kaggle/working/repo')
%cd /kaggle/working/repo
```

3. Run any of these (each saves one row per question and resumes if stopped):

```bash
# school maths, all three ways (about 4 hours on a T4)
python -m bench.run_bench --task gsm8k --split test --modes single,text,latent --steps 10 --dtype float16 --device cuda --out bench/results/test_rerun

# coding and medical, 60 questions each
python -m bench.run_bench --task mbppplus --split test --n 60 --modes single,text,latent --steps 10 --max-new-tokens 1024 --dtype float16 --device cuda --out bench/results/teams
python -m bench.run_bench --task medqa    --split test --n 60 --modes single,text,latent --steps 10 --max-new-tokens 1024 --dtype float16 --device cuda --out bench/results/teams

# the self-test, and the website recordings
python -m bench.mismatch_bench --split dev --n 50 --dtype float16 --device cuda
python -m bench.record_gallery --dtype float16 --device cuda

# summary of any results folder
python -m bench.metrics bench/results/teams
```

4. For long runs use **Save Version → Save & Run All (Commit)** so the run continues with the tab closed, then download the results from the notebook's **Output**.
5. Back on your machine, refresh the website data from the result files:

```bash
python -m bench.build_site_results
python -m bench.build_gallery_index
```

### 6.5 The usual flow on Nebius Token Factory

```bash
python -m telepathy.baseline_tf --n 150 --estimate                 # cost estimate only, spends nothing
python -m telepathy.baseline_tf --n 150 --run --yes                # the 4-agent team on 150 maths questions
python -m telepathy.baseline_tf --n 50 --topology team8 --run --yes   # an 8-agent team
python -m bench.teamsize                                           # the team-size table
```

Nothing is spent without both `--run` and `--yes`, and every call is capped by `MAX_USD_PER_CHECK` and `TOTAL_BUDGET_USD`.

## 7. Configuration

<details open>
<summary><b>Environment variables</b> (put them in <code>.env</code>)</summary>

| Variable | Default | What it does |
|---|---|---|
| `NEBIUS_API_KEY` | – | Your Nebius Token Factory key. Needed only for Nebius runs. |
| `TAVILY_API_KEY` | – | Web search for new research questions. Not needed to replay. |
| `MAX_USD_PER_CHECK` | 0.50 | The most one benchmark question may cost. |
| `TOTAL_BUDGET_USD` | 20 | Lifetime spending cap, saved in `.spend.json`. |
| `LLM_PROVIDER` | nebius | `nebius`, `nvidia`, `ollama` or `openrouter` (all OpenAI-compatible). |
| `TF_LIVE` | 0 | `1` lets the website run questions live on Nebius. |
| `DEMO_BUDGET_USD` | 3.0 | The most the live website may spend in total. |
| `LIVE_USD_PER_RUN` | 0.03 | The most one live question may cost. |
| `LIVE_PER_IP_PER_HOUR` | 6 | Live questions per visitor per hour. |
| `LIVE_MAX_CONCURRENT` | 3 | Live questions running at once. |
| `REPLAY` | 1 | `1` replays recordings; `0` runs the local GPU engine. |
| `REPLAY_SPEED` | 1 | Speed-up for replayed runs. |
</details>

<details>
<summary><b>The safety policy</b> · <code>policy.yaml</code></summary>

Read once at start-up and never changed by model output. The two core rules (`tainted_handoff: text` and `agent_tools: none`) are mandatory: any other value is rejected when the policy loads. Other settings control the instruction scan (`untrusted_scan`, `scan_action`) and whether hand-offs that cross roles share only the silent steps (`share_default`).
</details>

## 8. Troubleshooting

<details>
<summary><b>My Mac slows to a crawl or runs out of memory</b></summary>

The 4B model needs about 9 GB of memory, which is too much alongside a browser on a 16 GB laptop. Run the model on a GPU (6.4). The website and the tests do not need it.
</details>

<details>
<summary><b>"bfloat16 is not supported" on a T4 or P100</b></summary>

Older GPUs cannot use bfloat16. Add `--dtype float16`, which all our recorded results use.
</details>

<details>
<summary><b>Kaggle: <code>IndexError: list index out of range</code> in the setup cell</b></summary>

The notebook cannot see your code. Open **Add Input → Datasets**, add your dataset, and check with `!find /kaggle/input -maxdepth 6 | head -30`. If the folder is empty, the dataset upload failed or is still processing: upload the zip again as a new dataset.
</details>

<details>
<summary><b>Kaggle: <code>No module named bench</code></b></summary>

The notebook is not in the project folder. Run `%cd /kaggle/working/repo` first. If that folder does not exist, the session was reset: run the setup cell again.
</details>

<details>
<summary><b>Kaggle: the run stops halfway or the results vanished</b></summary>

Interactive sessions stop when idle, and a reset wipes `/kaggle/working`. Use **Save & Run All (Commit)** for anything longer than a few minutes; it runs on Kaggle's servers with the tab closed and keeps the output. Every benchmark resumes from where it stopped, so re-running only does the missing questions.
</details>

<details>
<summary><b>Coding answers are all marked wrong</b></summary>

The grader runs each answer together with the official test script, which imports `numpy`. Make sure `numpy` is installed in the same Python. You can check the grader on its own: the official reference solutions should all pass (see `tests/test_new_tasks.py`).
</details>

<details>
<summary><b>Results look free, or show 0 tokens</b></summary>

An answer came from the saved-answer cache. Benchmarks and live runs always bypass it; for a clean start delete `.cache/llm/`. Files named `*.INVALID-cached-answers` are the old, wrong results we kept on purpose.
</details>

<details>
<summary><b><code>BudgetExceeded</code> from Token Factory</b></summary>

A call would pass `MAX_USD_PER_CHECK` or `TOTAL_BUDGET_USD`. Raise them in `.env` if you mean to spend more. The lifetime total is in `.spend.json`.
</details>

<details>
<summary><b>The website has no "run live on Nebius" button</b></summary>

The button only appears when the API server is running with `TF_LIVE=1` and the website can reach it (6.3). Check http://localhost:8000/health shows `"tf_live": true`.
</details>

<details>
<summary><b>A live run says "spending limit reached" or "questions for this hour"</b></summary>

The live limits did their job. Raise `DEMO_BUDGET_USD` or `LIVE_PER_IP_PER_HOUR`, or restart the server to reset the hourly count.
</details>

<details>
<summary><b>The website says it could not load the recordings</b></summary>

Run the website from the `dashboard/` folder so it can find `public/gallery/`. If you changed result files, rebuild the website data with `python -m bench.build_site_results` and `python -m bench.build_gallery_index`.
</details>

<details>
<summary><b>Harmless messages you can ignore</b></summary>

- Kaggle: `bigframes … requires google-cloud-bigquery-storage` during `pip install`.
- Hugging Face: "You are sending unauthenticated requests". Setting `HF_TOKEN` only makes downloads faster.
- Transformers: "Ignoring clean_up_tokenization_spaces=True for BPE tokenizer".
</details>

## 9. What we do not claim

- **Not a new method.** The silent hand-off follows LatentMAS. Our work is the Nemotron implementation, the measurements, the safety layer and the website.
- **Not smarter answers.** Telepathy matches or beats the usual multi-agent system on accuracy, but our own self-test shows the silent thinking alone does not measurably improve answers.
- **Not tested on big models.** All Telepathy results use a 4B model. Scores would likely be higher on a bigger model; we have not measured it.
- **Not running on Token Factory.** The usual flow runs live on Nebius; Telepathy needs the model's internal memory, so it runs on a GPU we control. We never compare the two models' seconds.
- **Small research sample.** The web-research results are 3 questions, a demo rather than a benchmark.

## 10. Credits

- **LatentMAS** for the latent collaboration method ([paper](https://arxiv.org/abs/2511.20639), [code](https://github.com/Gen-Verse/LatentMAS), Apache-2.0).
- **NVIDIA Nemotron** models: Nemotron Nano 4B (Telepathy) and Nemotron 3 Super (Nebius Token Factory).
- **Nebius Token Factory** for model hosting, and **Tavily** for web search.
- Test sets: **GSM8K**, **MBPP+** (EvalPlus), **MedQA** and **ARC**.
- Built for the Nebius × NVIDIA Global AI Hackathon.

Released under the [MIT License](LICENSE).
