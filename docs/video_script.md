# Telepathy: demo video script (under 3 minutes)

About 400 spoken words, which is roughly 2:45 at a normal pace. Each part lists what is on screen and what to say. Record the website at full screen, with the demo link open. The diagram is `docs/architecture.svg`.

---

## 0:00 – 0:15 · The hook
**Screen:** the top of the website (headline and the three numbers).

**Say:**
> Multi-agent AI systems split a job between agents: one plans, one checks, one improves, one answers. But they work by writing long notes to each other, and every agent rereads everything before it. This is Telepathy: agents that share their working memory instead of writing notes.

## 0:15 – 0:35 · The problem
**Screen:** scroll to "The problem" and its bar chart.

**Say:**
> We measured this on Nebius Token Factory with NVIDIA Nemotron 3 Super. Going from 2 agents to 8, the reading per question grew from about 400 tokens to over 12,000, almost 30 times more, while accuracy stayed the same. More agents means far more reading.

## 0:35 – 1:10 · How it works, live
**Screen:** "Watch the hand-off". Let the animation play once; hover one of the small "i" buttons.

**Say:**
> Here is one real recorded question, answered both ways on the same clock. On top, the usual flow: each agent writes notes and passes them on. Below, Telepathy. While a model reads and thinks, it builds a working memory, the KV cache. Telepathy hands that memory straight to the next agent. The first three agents think silently and write nothing. Only the last agent writes, and that is the answer.
>
> Both got it right: 122. Telepathy was 4 times faster, with 80% fewer words.

## 1:10 – 1:30 · Under the hood
**Screen:** the architecture diagram, then the "inside the model" diagram.

**Say:**
> All four agents are the same model, loaded once on one GPU. Each agent reads its job, thinks silently on top of the shared memory, and hands it on. We built this on the published LatentMAS research, implemented for NVIDIA Nemotron. For web research, pages from the internet are marked untrusted by our code, and only plain text can carry them forward.

## 1:30 – 1:50 · Try it
**Screen:** "Pick a question". Click a coding question, then a web research question.

**Say:**
> You can replay real recordings across maths, coding, science and live web research, found with Tavily search, side by side.

## 1:50 – 2:25 · The results
**Screen:** "Results". Hover a few bars, then open "Raw results" and click a question to expand it.

**Say:**
> We tested one agent alone, a usual multi-agent system, and Telepathy, on the same questions. Against the usual multi-agent system, Telepathy was 2.9 to 40 times faster and wrote 60 to 98% fewer tokens, with the same or better accuracy, across school maths, coding graded by running real tests, a medical exam, and web research. Every question's time and tokens are here, from the raw files.

## 2:25 – 2:50 · Honest setup and what's next
**Screen:** back to the top of the page, or the "What we measured" box in the diagram.

**Say:**
> To be clear about our setup: all of this ran on a small model, NVIDIA Nemotron Nano 4B, on a single NVIDIA Tesla T4. That is why accuracy is modest. The same usual flow on the much bigger Nemotron 3 Super, through Nebius, scored 91% on the same maths questions, so a bigger model should lift Telepathy too. Telepathy: agents that think together, without writing it all out.

---

### Recording tips
- Use 1920 × 1080 and hide the browser's bookmarks bar.
- Before recording, scroll through the page once so the animation and charts have loaded.
- Time yourself once. If you run over 2:55, cut the "Try it" part first.
- The video must be **under 3 minutes** and public on YouTube.
