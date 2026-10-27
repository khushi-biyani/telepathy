import { useEffect, useMemo, useRef, useState } from "react";
import { getHealth, postLive } from "../api";
import { useLane } from "../useLane";
import { Lane } from "./Lane";
import { SectionHead } from "./SectionHead";
import { asset } from "../asset";

type Agent = { role: string; seconds: number; words_written: number; text: string; silent_steps: number };
type Run = {
  mode: "text" | "latent"; seconds: number; tokens_written: number; answer: string; agents: Agent[];
  safety_events: { type: string; flagged?: boolean; count?: number; reason?: string }[];
  pred?: string | null; correct: boolean; followed_planted_instruction?: boolean; tests_passed?: number; tests_total?: number;
};
type Rec = { id: string; title: string; kind: string; question: string; answer: string; model: string; gpu: string; recorded_at: string; runs: Run[] };
type Side = { seconds: number; tokens: number; correct: boolean; words: number; detail: string | null };
type Item = { id: string; title: string; kind: string; blurb: string; question: string; answer: string; featured: boolean; usual: Side; telepathy: Side };
type Stats = {
  n: number; usual_right: number; telepathy_right: number; usual_seconds: number; telepathy_seconds: number; median_speedup: number;
  by_kind: Record<string, { n: number; usual_right: number; telepathy_right: number }>;
  model: string; gpu: string; dtype: string; max_new_tokens: number; versions: { torch: string; transformers: string };
};

const KIND: Record<string, string> = { math: "Maths", logic: "Logic puzzle", code: "Coding", science: "Science", research: "Research: real web search" };
const NAME: Record<string, string> = { planner: "Planner Agent", critic: "Critic Agent", refiner: "Refiner Agent", solver: "Solver Agent", researcher: "Reader Agent", analyst: "Analyst Agent", research_critic: "Critic Agent", writer: "Writer Agent" };
const sum = (a: number[]) => a.reduce((x, y) => x + y, 0);

function Verdict({ ok }: { ok: boolean }) {
  return <span style={{ color: ok ? "var(--ok)" : "#e5484d" }} className="font-medium">{ok ? "✓ right" : "✗ wrong"}</span>;
}

/** One team's run, drawn on a shared clock `t` (recorded seconds). */
function LaneView({ run, t, kind, tele }: { run: Run; t: number; kind: string; tele: boolean }) {
  const total = run.seconds, done = t >= total;
  let start = 0, words = 0;
  const rows = run.agents.map((a) => {
    const s = start; start += a.seconds;
    const f = done ? 1 : Math.max(0, Math.min(1, (t - s) / a.seconds)), active = !done && t > s && t < s + a.seconds;  // done: avoid a rounding gap at the very end
    words += a.words_written * f;
    return { a, f, active };
  });
  const accent = tele ? "var(--s-telepathy)" : "var(--s-english)";
  return (
    <div className="rounded-2xl bg-well p-5">
      <div className="mb-3 flex items-baseline justify-between">
        <div className="text-sm font-medium" style={{ color: accent }}>{tele ? "Telepathy" : "Usual multi-agent flow"}</div>
        <div className="text-xs text-muted">{tele ? "silent thinking, only the last agent writes" : "every agent writes notes"}</div>
      </div>
      <div className="space-y-2">
        {rows.map(({ a, f, active }) => (
          <div key={a.role}>
            <div className="mb-1 flex justify-between text-xs">
              <span className="text-ink2">{NAME[a.role] ?? a.role}</span>
              <span className="tabular-nums text-muted">{f >= 1 ? `${a.seconds.toFixed(1)} s${a.words_written ? ` · ${a.words_written} words` : ""}` : active ? "working…" : ""}</span>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-surface">
              <div className="h-1.5 rounded-full" style={{ width: `${f * 100}%`, background: f >= 1 ? "var(--ok)" : accent, transition: "background .2s" }} />
            </div>
          </div>
        ))}
      </div>
      <div className="mt-4 grid grid-cols-3 gap-2 text-center">
        <div className="rounded-xl bg-surface px-2 py-2"><div className="text-lg font-semibold tabular-nums">{Math.min(t, total).toFixed(1)} s</div><div className="text-[11px] text-muted">time</div></div>
        <div className="rounded-xl bg-surface px-2 py-2"><div className="text-lg font-semibold tabular-nums">{Math.round(words).toLocaleString()}</div><div className="text-[11px] text-muted">words written</div></div>
        <div className="rounded-xl bg-surface px-2 py-2">
          <div className="text-sm font-semibold">{done ? <Verdict ok={run.correct} /> : "…"}</div>
          <div className="text-[11px] text-muted">{!done ? "result" : kind === "code" ? `${run.tests_passed}/${run.tests_total} tests` : kind === "research" ? "checked against the answer" : run.pred ? `answer: ${run.pred}` : "no answer reached"}</div>
        </div>
      </div>
    </div>
  );
}

export function Gallery() {
  const [data, setData] = useState<{ stats: Stats; items: Item[] } | null>(null);
  const [failed, setFailed] = useState(false);
  const [sel, setSel] = useState("gsm8k-181");
  const [rec, setRec] = useState<Rec | null>(null);
  const [t, setT] = useState(0);
  const [playing, setPlaying] = useState(false);
  const raf = useRef(0);
  const [liveOk, setLiveOk] = useState(false);
  const [liveRun, setLiveRun] = useState<string | null>(null);
  const [liveErr, setLiveErr] = useState<string | null>(null);
  const [liveBusy, setLiveBusy] = useState(false);
  const live = useLane(liveRun);

  useEffect(() => {
    getHealth().then((h) => setLiveOk(!!h.tf_live)).catch(() => setLiveOk(false));  // the button only appears when the server can run live
    fetch(asset("/gallery/index.json")).then((r) => r.json()).then(setData).catch(() => setFailed(true));
    return () => cancelAnimationFrame(raf.current);
  }, []);
  useEffect(() => {
    cancelAnimationFrame(raf.current); setPlaying(false); setT(0); setRec(null); setLiveRun(null); setLiveErr(null);
    fetch(asset(`/gallery/${sel}.json`)).then((r) => r.json()).then(setRec).catch(() => setFailed(true));
  }, [sel]);

  const text = rec?.runs.find((r) => r.mode === "text"), latent = rec?.runs.find((r) => r.mode === "latent");
  const end = rec ? Math.max(text!.seconds, latent!.seconds) : 0;
  const speed = end / 14;  // the slower team takes about 14 s on screen; both share one clock, so the speed gap is real

  function play() {
    if (!rec) return;
    cancelAnimationFrame(raf.current); setT(0); setPlaying(true);
    let last = performance.now();
    const tick = (now: number) => {
      const dt = (now - last) / 1000; last = now;
      let done = false;
      setT((cur) => { const nx = Math.min(end, cur + dt * speed); done = nx >= end; return nx; });
      if (!done) raf.current = requestAnimationFrame(tick); else setPlaying(false);
    };
    raf.current = requestAnimationFrame(tick);
  }
  async function runLive() {
    setLiveBusy(true); setLiveErr(null);
    try { setLiveRun((await postLive(sel)).run_id); } catch (e: any) { setLiveErr(e.message); } finally { setLiveBusy(false); }
  }
  function skip() { cancelAnimationFrame(raf.current); setPlaying(false); setT(end); }

  const items = data?.items ?? [];
  const shown = useMemo(() => items.filter((i) => i.featured), [items]);
  const cur = items.find((i) => i.id === sel);
  const finished = rec && t >= end && end > 0;
  const speedup = rec ? text!.seconds / latent!.seconds : 0;
  const wordsU = text ? sum(text.agents.map((a) => a.words_written)) : 0, wordsT = latent ? sum(latent.agents.map((a) => a.words_written)) : 0;
  const tainted = latent?.safety_events.find((e) => e.type === "outside_content");
  const followed = !!(text?.followed_planted_instruction || latent?.followed_planted_instruction);

  return (
    <div>
      <SectionHead label="Try it" title="Pick a question: multi-agent vs Telepathy"
        sub={<>Featured examples, replayed from real recordings on the same model and GPU. The full test results are in the <a href="#numbers" className="text-ink underline underline-offset-4">Results</a> section below.</>} />

      {failed && <p role="alert" className="mb-4 rounded-2xl bg-eng-soft p-4 text-sm text-eng-ink">Could not load the recordings.</p>}

      <div className="mb-8 flex flex-wrap gap-2">
        {shown.map((i) => (
          <button key={i.id} onClick={() => setSel(i.id)} aria-pressed={sel === i.id}
            className="rounded-full border px-3.5 py-1.5 text-sm transition-colors"
            style={sel === i.id ? { borderColor: "var(--s-telepathy)", color: "var(--ink)", background: "var(--tel-soft)" } : { borderColor: "var(--hair-strong)", color: "var(--ink2)" }}>
            {i.title}
          </button>
        ))}
      </div>

      {cur && (
        <div className="rounded-3xl bg-surface">
          <div className="p-6 sm:p-8">
            <div className="mb-3 flex flex-wrap items-start gap-3">
              <div className="min-w-0 flex-1 rounded-xl border border-hair bg-well px-4 py-3">
                <div className="label mb-1">{KIND[cur.kind]}</div>
                <div className="whitespace-pre-line text-sm text-ink">{cur.question}</div>
              </div>
              <div className="flex gap-2">
                <button onClick={play} disabled={!rec || playing} className={`btn-play ${playing || finished ? "" : "idle"}`} style={{ ["--play" as string]: "var(--s-telepathy)" } as React.CSSProperties}>
                  {playing ? "Playing…" : finished ? "Replay" : "Play both"}
                </button>
                {!finished && <button onClick={skip} disabled={!rec} className="btn-ghost">Show result</button>}
              </div>
            </div>
            {rec && text && latent && (
              <>
                <div className="grid gap-4 lg:grid-cols-2">
                  <LaneView run={text} t={t} kind={cur.kind} tele={false} />
                  <LaneView run={latent} t={t} kind={cur.kind} tele />
                </div>

                {finished && (
                  <div role="status" className="rise mt-5 grid grid-cols-3 gap-3 rounded-2xl p-5" style={{ background: "var(--tel-soft)" }}>
                    {[[`${speedup.toFixed(1)}×`, "faster with Telepathy"],
                      [wordsU ? `${Math.round((1 - wordsT / wordsU) * 100)}%` : "–", "fewer words written"],
                      [text.correct && latent.correct ? "Both ✓" : `${latent.correct ? "✓" : "✗"} / ${text.correct ? "✓" : "✗"}`, text.correct && latent.correct ? "both teams right" : "Telepathy / usual flow"]].map(([v, l]) => (
                      <div key={l}><div className="text-2xl font-semibold tabular-nums sm:text-3xl" style={{ color: "var(--tel-ink)" }}>{v}</div><div className="mt-0.5 text-xs text-ink2">{l}</div></div>
                    ))}
                  </div>
                )}

                {cur.kind === "research" && tainted && (
                  <p className="mt-3 text-xs text-muted">
                    The Reader searched the web and read {tainted.count} real pages (saved when we recorded). Outside pages are untrusted, so it handed its findings on in plain text, which was scanned, before the others worked silently.
                    {followed && <span style={{ color: "var(--eng-ink)" }}> An answer repeated text planted in a page.</span>}
                  </p>
                )}

                <details className="mt-4">
                  <summary className="cursor-pointer text-xs text-ink2 underline">Read what each agent wrote</summary>
                  <div className="mt-3 grid gap-4 lg:grid-cols-2">
                    {[text, latent].map((r) => (
                      <div key={r.mode} className="space-y-2">
                        <div className="text-sm font-medium text-ink">{r.mode === "text" ? "Usual multi-agent flow" : "Telepathy"}</div>
                        {r.agents.map((a) => (
                          <div key={a.role} className="rounded-xl bg-well p-3 text-xs text-ink2">
                            <b className="text-ink">{NAME[a.role] ?? a.role}</b> <span className="text-muted">({a.seconds.toFixed(1)} s)</span>
                            <div className="mt-1 max-h-48 overflow-auto whitespace-pre-wrap">{a.silent_steps > 0 ? "Passed on its working memory and wrote nothing." : a.text}</div>
                          </div>
                        ))}
                      </div>
                    ))}
                  </div>
                </details>
                {liveOk && (
                  <div className="mt-4 rounded-2xl border border-hair p-4">
                    <div className="flex flex-wrap items-center gap-3">
                      <button onClick={runLive} disabled={liveBusy || live.status === "running"} className="btn-ghost">
                        {live.status === "running" ? "Running on Nebius…" : "Also run the usual flow live on Nebius"}
                      </button>
                      <span className="text-xs text-muted">Calls Nemotron 3 Super through Nebius Token Factory right now. It is a much bigger model on different hardware, so do not compare its seconds with the recordings above.</span>
                    </div>
                    {liveErr && <p role="alert" className="mt-3 text-sm text-eng-ink">{liveErr}</p>}
                    {liveRun && <div className="mt-4"><Lane kind="english" lane={live} /></div>}
                  </div>
                )}

                <p className="mt-3 text-xs text-muted">
                  <a className="underline" href={asset(`/gallery/${cur.id}.json`)} download>Download this recording</a> · {rec.model.split("/").pop()} · {rec.gpu.startsWith("NVIDIA") ? rec.gpu : `NVIDIA ${rec.gpu}`}
                </p>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
