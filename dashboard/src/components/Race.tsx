import { SectionHead } from "./SectionHead";
import { useEffect, useState } from "react";
import { getRecordings, postRace } from "../api";
import { raceVerdict } from "../lane";
import { useLane } from "../useLane";
import type { RunInfo } from "../types";
import { Accordion } from "./Accordion";
import { Lane } from "./Lane";
import { Subtitles } from "./Subtitles";
import { Transcript } from "./Transcript";

type Race = { text: RunInfo; latent: RunInfo } | null;
type Example = { q: string; topology: string };

export function Race() {
  const [race, setRace] = useState<Race>(null);
  const [examples, setExamples] = useState<Example[]>([]);
  const [question, setQuestion] = useState("");
  const [topology, setTopology] = useState("sequential");
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const [available, setAvailable] = useState<string[]>([]);

  const english = useLane(race?.text.run_id ?? null);
  const telepathy = useLane(race?.latent.run_id ?? null);
  const fake = english.synthetic || telepathy.synthetic;
  const liveEnglish = english.provider === "nebius_token_factory";
  // A live run on Nebius's big model and a recording of our small model are not a fair speed comparison.
  const verdict = fake || liveEnglish ? null : raceVerdict(english, telepathy);

  useEffect(() => {
    getRecordings().then((r) => {
      const seen = new Set<string>();
      const ex = r.filter((x) => !seen.has(x.topology + x.question) && seen.add(x.topology + x.question)).map((x) => ({ q: x.question, topology: x.topology }));
      setExamples(ex);
      // a link ending in ?autostart begins the first race on its own (handy for the video and for sharing)
      if (ex.length && new URLSearchParams(location.search).has("autostart")) start(ex[0].q, ex[0].topology);
    }).catch(() => setProblem("api"));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function start(q: string, topo: string) {
    setBusy(true); setProblem(null); setAvailable([]); setQuestion(q); setTopology(topo);
    try { setRace(await postRace(q, topo)); }
    catch (e: any) {
      if (e.status === 404 && e.detail?.available) { setProblem("norecording"); setAvailable([...new Set<string>(e.detail.available.map((a: any) => a.question))]); }
      else setProblem("api");
    } finally { setBusy(false); }
  }

  const inexact = race?.latent.recorded && race.latent.exact === false;

  return (
    <div>
      <SectionHead label="The race" title="Race the two teams" sub="Click a question to start. Both teams answer it and you watch." />

      <div className="mb-6 grid items-stretch gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {examples.slice(0, 3).map((ex) => (
          <button key={ex.topology + ex.q} onClick={() => start(ex.q, ex.topology)} disabled={busy}
            className="flex h-full flex-col rounded-2xl border border-hair bg-surface p-4 text-left transition-shadow hover:shadow-md disabled:opacity-60"
            style={race && question === ex.q ? { outline: "2px solid var(--s-telepathy)" } : undefined}>
            <div className="mb-1 text-xs font-medium text-telepathy">{ex.topology === "research" ? "Research team" : "Maths team"}</div>
            <div className="line-clamp-3 text-sm">{ex.q}</div>
          </button>
        ))}
        {!examples.length && !problem && <p className="text-sm text-muted sm:col-span-3">Loading examples…</p>}
      </div>

      {problem === "api" && <p role="alert" className="mb-6 rounded-2xl bg-eng-soft p-4 text-sm text-eng-ink">The race needs the API running. Start it with <code>uvicorn server.app:app --port 8000</code>.</p>}
      {problem === "norecording" && (
        <div role="alert" className="mb-6 rounded-2xl bg-eng-soft p-4 text-sm text-eng-ink">
          <p className="mb-1">No GPU is connected and nothing recorded matches. You can run one of these:</p>
          <ul className="list-disc pl-5">{available.map((q) => <li key={q}>{q}</li>)}</ul>
        </div>
      )}
      {race?.text.live_denied && <p className="mb-6 rounded-2xl bg-well p-4 text-sm text-ink2">The written-notes side is showing a recording, because {race.text.live_denied}.</p>}
      {inexact && <p className="mb-6 rounded-2xl bg-tel-soft p-4 text-sm text-tel-ink">No GPU is connected, so this is the closest recorded example, not your exact question: “{race!.latent.matched_question}”.</p>}

      <div className="grid gap-5 lg:grid-cols-2">
        <Lane kind="english" lane={english} />
        <Lane kind="telepathy" lane={telepathy} />
      </div>

      {liveEnglish && english.status === "done" && telepathy.status === "done" && (
        <p className="mt-5 rounded-[14px] bg-well p-5 text-center text-sm text-ink2">
          The written-notes side ran live on Nebius with a much bigger model, and the Telepathy side is a recording of a small model on a different machine.
          So this is not a speed comparison. For a fair one, see Numbers below, where both teams use the same model on the same machine.
        </p>
      )}
      {fake && english.status === "done" && (
        <p className="mt-5 rounded-[14px] bg-well p-5 text-center text-sm text-ink2">This is a sample animation, not a real run, so no numbers are shown. Real recorded races will appear here once they are recorded.</p>
      )}
      {verdict && (
        <div role="status" className="rise mt-5 rounded-[14px] bg-ok-soft p-6 text-center text-ok-ink">
          <p className="text-2xl font-semibold sm:text-3xl">
            {verdict.speedup && `×${verdict.speedup.toFixed(1)} faster`}
            {verdict.fewerTokens != null && ` · ${Math.round(verdict.fewerTokens * 100)}% fewer words`}
            {verdict.sameAnswer === true && ` · same answer: ${verdict.answer}`}
          </p>
          {verdict.sameAnswer === false && <p className="mt-1 text-sm">The answers differ: written notes {verdict.otherAnswer}, Telepathy {verdict.answer}. We show it as it happened.</p>}
        </div>
      )}
      {telepathy.tainted && <p className="mt-4 rounded-2xl bg-well p-4 text-sm text-ink2">This run read outside content, so its first handoff was written in English and the run is marked tainted.</p>}

      <div className="mt-6 space-y-3">
        <Accordion title="Read what the agents said">
          <div className="grid gap-6 lg:grid-cols-2">
            <div><h4 className="mb-2 font-medium text-ink">Written notes</h4><Transcript kind="english" lane={english} /></div>
            <div><h4 className="mb-2 font-medium text-ink">Telepathy</h4><Transcript kind="telepathy" lane={telepathy} /></div>
          </div>
          <div className="mt-6"><Subtitles lane={telepathy} /></div>
        </Accordion>
        <Accordion title="Ask your own question">
          <form onSubmit={(e) => { e.preventDefault(); if (question.trim()) start(question.trim(), topology); }}>
            <textarea value={question} onChange={(e) => setQuestion(e.target.value)} rows={2} aria-label="Your question"
              className="w-full resize-y rounded-xl border border-hair bg-well p-3 text-ink outline-none focus:border-telepathy" placeholder="A shop sells pens at 12 rupees each…" />
            <div className="mt-3 flex flex-wrap items-center gap-3">
              <select aria-label="Team" value={topology} onChange={(e) => setTopology(e.target.value)} className="rounded-full border border-hair bg-surface px-3 py-1.5 text-xs">
                <option value="sequential">Maths team</option><option value="research">Research team</option>
              </select>
              <button type="submit" disabled={busy || !question.trim()} className="btn-primary">Run the race</button>
              <span className="text-xs text-muted">Without a GPU connected, this plays the closest recorded example.</span>
            </div>
          </form>
        </Accordion>
      </div>
    </div>
  );
}
