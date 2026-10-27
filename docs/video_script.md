# Telepathy: 3-minute video script

About 470 spoken words, a little over 3 minutes at a calm pace; trim the "Try it" part if you need to. Each part lists what is on screen and what to say. Record the website at full screen; the diagram is `docs/architecture.svg`.

---

## 0:00 – 0:20 · The hook
**Screen:** the website's top section (headline and the three numbers).

**Say:**
> Multi-agent systems split a job between specialist AI agents: one plans, one checks, one improves, one answers. But they talk by writing long notes to each other, and every agent has to reread everything written before it. That makes them slow and expensive. This is Telepathy: agents that share their working memory instead of writing notes.

## 0:20 – 0:45 · The problem
**Screen:** scroll to "The problem" and its bar chart.

**Say:**
> We measured the usual way on Nebius Token Factory with NVIDIA Nemotron 3 Super. Going from 2 agents to 8, the reading per question grew from about 400 tokens to over 12,000, almost 30 times more, and accuracy did not improve. More agents means far more reading.

## 0:45 – 1:25 · How it works
**Screen:** "Watch the hand-off". Let the animation play once. Hover one of the small "i" buttons on each lane.

**Say:**
> Here is one real recorded question, answered both ways on the same clock. On top, the usual multi-agent flow: each agent writes notes and passes them on. Below, Telepathy. When an AI model reads and thinks, it builds a working memory, called the KV cache. Telepathy hands that memory straight to the next agent. The first three agents think silently and write nothing; only the last agent writes, and what it writes is the answer.
>
> Both got the right answer, 122. Telepathy was 4 times faster and wrote 80% fewer words.

## 1:25 – 1:45 · Under the hood
**Screen:** the architecture diagram, zoomed on section 3, "How the memory is passed".

**Say:**
> All four agents are the same model, loaded once on one GPU. Each agent reads its job, thinks silently on top of the shared memory, and hands it on. We built this on the published LatentMAS method and implemented it for NVIDIA Nemotron. For web research, outside pages are marked untrusted by our code, and only plain, checked text can carry them forward.

## 1:45 – 2:05 · Try it
**Screen:** "Pick a question". Click a coding question, then a web research question, and let each replay.

**Say:**
> You can replay real recordings across maths, coding, science and live web research, side by side, with the time and the words each way.

## 2:05 – 2:40 · The results
**Screen:** "Results". Hover a few bars, then open "Raw results" and expand one question.

**Say:**
> We tested three ways of working on the same questions: one agent alone, a usual multi-agent system, and Telepathy. Against the usual multi-agent system, Telepathy was 2.9 to 40 times faster and wrote 60 to 98% fewer tokens, with the same or better accuracy, on school maths, coding graded by running real tests, a medical exam, and web research. Every question's time and tokens are here, from the raw files.

## 2:40 – 3:00 · Honest setup and what's next
**Screen:** back to the top of the page, or the diagram's "What we measured" box.

**Say:**
> To be clear about our setup: we ran all of this on a small model, NVIDIA Nemotron Nano 4B, on a single NVIDIA Tesla T4, an older entry-level GPU with 16 gigabytes. That is why the accuracy scores are modest. When we ran the usual multi-agent flow on the much bigger Nemotron 3 Super through Nebius, accuracy on the same maths questions went from 69 to 91 percent, so with a bigger model Telepathy's scores would likely go up too. The saving comes from not writing and rereading notes, so we expect it to carry over, and that is the next thing we want to test. Telepathy: agents that think together, without writing it all out.

---

### Recording tips
- Use 1920 × 1080 and hide the browser's bookmarks bar.
- Before recording, scroll through the page once so the animation and charts have loaded.
- Speak slowly; if you run long, shorten the "Try it" part first.
