# Telepathy: demo video script (target 2:55, limit 3:00)

About 400 spoken words: a steady pace (about 150 words a minute) fits just under 3:00. Time a read-through; if it runs long, shorten the "Try it" shot first. **VO** = voice-over. **SCREEN** = what is recorded. Record the real website and say so. No music with lyrics or copyrighted tracks.

Four beats: **the hook** (the cost of agents writing notes, then what we built) → **how it works** (one real question, both ways, on one clock) → **proof** (the results, including where Telepathy did not win) → **how it is built** (the small model, the GPU, Nebius, Tavily), then a one-line close. Judging criteria in brackets.

---

### 1 · The hook: 0:00 to 0:30  *(Quality of the idea, Potential impact)*

**SCREEN:** Three plain title cards, one after another, white text on dark: "2 agents · 416 tokens read per question" → "4 agents · 2,661" → "8 agents · 12,019".

**VO:**
> Multi-agent AI is everywhere: one agent plans, one checks, one improves, one answers. But they work by writing notes to each other, and every agent rereads everything written before it. We measured it on Nebius Token Factory: going from two agents to eight, the reading grew almost thirty times, with no gain in accuracy.

**SCREEN:** The website's top section (headline and the three numbers).

**VO:**
> So we built Telepathy: agents that share their working memory instead of writing notes.

---

### 2 · How it works: 0:30 to 1:20  *(Technological implementation, Design)*

**SCREEN:** "Watch the hand-off". Let the animation play once. Caption in a corner: "Real recorded run".

**VO:**
> Here is one real question, answered both ways on the same clock. On top, the usual flow: every agent writes notes and passes them on. Below, Telepathy. While a model reads and thinks, it builds a working memory, called the KV cache. Telepathy hands that memory straight to the next agent. Three agents think silently; only the last one writes the answer.

**SCREEN:** The result box under the animation: 4.0×, 80%, 122.

**VO:**
> Same answer, 122. Four times faster, with eighty percent fewer words.

**SCREEN:** The "inside the model" diagram. Slow zoom: the words it reads → the silent thoughts → the KV cache → the hand-over to the next agent.

**VO:**
> Under the hood, all four agents are one NVIDIA Nemotron model on one GPU. Each reads its job and thinks silently, and the next agent starts from the same memory, with nothing to reread.

---

### 3 · Proof: 1:20 to 2:10  *(Potential impact)*

**SCREEN:** "Results". Hover the coding bars: accuracy, time and tokens appear.

**VO:**
> We tested one agent alone, the usual multi-agent system, and Telepathy, on the same questions: school maths, coding graded by running real tests, a medical exam, and web research. Against the usual system, Telepathy was 2.9 to 40 times faster, wrote 60 to 98 percent fewer tokens, and was as accurate or better. On coding it also solved seven problems the single agent missed, and missed none.

**SCREEN:** Open "Raw results", click a question to expand it.

**VO:**
> It didn't always win: on simple maths, one agent alone beat both teams. Every question's time and tokens are here, from the raw files.

**SCREEN:** "Pick a question": click the web research example (Eiffel Tower and Burj Khalifa) and let it replay.

**VO:**
> Research questions use real web pages, found with Tavily.

---

### 4 · How it is built: 2:10 to 2:50  *(Technological implementation, Design)*

**SCREEN:** The architecture diagram, full view for a second, then a slow zoom on the "Why it runs on a GPU" box.

**VO:**
> To be clear about our setup: Telepathy ran on a small model, Nemotron Nano 4B, on a single NVIDIA Tesla T4. That is why accuracy is modest. Nebius Token Factory ran the usual flow on the much bigger Nemotron 3 Super, about eighteen hundred calls for under a dollar fifty. On the same maths questions it scored 91 percent, so a bigger model should lift Telepathy too.

**SCREEN:** Zoom on the "Keeping it safe" box.

**VO:**
> And web pages are marked untrusted by our code, so nothing from the internet travels hidden in the memory.

---

### Close: 2:50 to 2:58

**SCREEN:** The website's top section, then the repo link on screen.

**VO:**
> Telepathy: agents that think together, without writing it all out.

---

## Recording checklist

- [ ] Record from the **published demo link**, not localhost, once the site is live.
- [ ] **Beat 1:** make the three title cards (text only, no screenshots) and put the real numbers on them: 416, 2,661 and 12,019.
- [ ] **Beat 2:** wait for the animation to start from the beginning, so you capture the whole run (about 14 seconds), then the result box.
- [ ] **Beat 3:** hover the coding bars, then open "Raw results" and click the egg-farm question; for the research shot, pick the Eiffel Tower and Burj Khalifa question in "Pick a question".
- [ ] **Beat 4:** have `docs/architecture.svg` and `docs/inside_the_model.svg` open in full-screen tabs.
- [ ] Scroll through the page once before recording so the charts and animation have loaded.
- [ ] Use 1920 × 1080, zoom the browser to 110–125%, and move the cursor slowly and deliberately.
- [ ] Hide bookmarks, notifications and any `.env` or key windows.
- [ ] Upload to YouTube as **Public**, **under 3:00**, and paste the link into Devpost.
