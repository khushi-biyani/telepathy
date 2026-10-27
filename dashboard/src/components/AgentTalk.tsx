import { useEffect, useRef, useState } from "react";
import type { Measured } from "../savings";
import { Scroll } from "./charts";

const NAMES = ["Planner Agent", "Critic Agent", "Refiner Agent", "Solver Agent"];
const ROLE = ["makes a plan", "checks it", "improves it", "writes the answer"];
const X = [6, 194, 382, 570], W = 104;
import REC from "../data/animation_recording.json";
import { asset } from "../asset";

// Real recording: this question, run on the small model (Nemotron Nano 4B) on a Kaggle T4, in both modes.
// Every note, second and word count below is what that run produced (file: /gallery/<id>.json).
const EN = REC.text, TE = REC.latent;
const EN_TXT = EN.agents.map((a) => a.text.replace(/[*#]+/g, "").replace(/\s+/g, " ").trim());
const EN_WORDS = EN.agents.map((a) => a.words_written);
const EN_SEC = EN.agents.map((a) => a.seconds);
const WORDS = { english: EN_WORDS.reduce((x, y) => x + y, 0), tele: TE.agents.reduce((x, y) => x + y.words_written, 0) };
const SECS = { english: EN.seconds, tele: TE.seconds };
const ANSWER = { english: EN.boxed, tele: TE.boxed };
const RIGHT = REC.answer;
const fmt = (v: string | null) => (v ? Number(v).toLocaleString() : "no answer");
// pieces of each agent's real note that flow to the next agent (each is copied word for word from the recording)
const PHRASES: string[][] = [
  ["40 - 4 = 36 crabs", "36 + 10 = 46 crabs", "40 + 36 + 46 = 122"],
  ["No Mistakes Detected", "Final Answer Inclusion"],
  ["Revised for Clarity", "Verification", "122 crabs"],
];
const QUESTION = REC.question;
type Mode = "english" | "tele";
const secTotal = EN_SEC.reduce((x, y) => x + y, 0);
// usual flow: each step's real share of the time. Telepathy: its three silent steps took about 0.5 s each, too short to see, so they are stretched here; the real seconds are in the proof table.
const SHARES: Record<Mode, number[]> = { english: EN_SEC.map((x) => x / secTotal), tele: [0.14, 0.14, 0.14, 0.58] };
const HAND: Record<Mode, number> = { english: 0.35, tele: 0.5 };  // the first part of each step is thinking or writing, the rest is handing over

function paint(kind: "active" | "done" | "idle", tele: boolean) {
  if (kind === "active") return tele ? { fill: "var(--tel-soft)", stroke: "var(--s-telepathy)" } : { fill: "var(--eng-soft)", stroke: "var(--s-english)" };
  if (kind === "done") return { fill: "var(--ok-soft)", stroke: "var(--ok)" };
  return { fill: "var(--surface)", stroke: "var(--axis)" };
}

const ease = (x: number) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2);  // smooth start and stop

/** One flow (usual or Telepathy) drawn at progress p (0 to 1). Owns its own tooltip. */
function HandoffLane({ mode, p, playing }: { mode: Mode; p: number; playing: boolean }) {
  const [tipIdx, setTipIdx] = useState<number | null>(null);
  const [pinned, setPinned] = useState(false);
  const [tipPos, setTipPos] = useState<{ left: number; bottom: number }>({ left: 0, bottom: 0 });
  const wrap = useRef<HTMLDivElement>(null);
  const hideT = useRef(0);
  useEffect(() => { if (playing) { setTipIdx(null); setPinned(false); } }, [playing]);
  useEffect(() => () => window.clearTimeout(hideT.current), []);
  const place = (el: Element) => {
    const r = el.getBoundingClientRect(), w = wrap.current!.getBoundingClientRect();
    setTipPos({ left: Math.min(Math.max(r.left - w.left + r.width / 2, 235), Math.max(235, w.width - 235)), bottom: w.height - (r.top - w.top) + 8 });
  };
  // hover opens at once; leaving waits a moment, so moving between the "i" buttons never flickers
  const show = (el: Element, i: number) => { window.clearTimeout(hideT.current); place(el); setTipIdx(i); };
  const hide = () => { if (pinned) return; window.clearTimeout(hideT.current); hideT.current = window.setTimeout(() => setTipIdx(null), 140); };

  const tele = mode === "tele";
  const sh = SHARES[mode], hand = HAND[mode];
  const cum = [0]; sh.forEach((x) => cum.push(cum[cum.length - 1] + x));
  const done = p >= 1;
  let k = 0; for (let i = 0; i < 4; i++) if (p >= cum[i]) k = i;
  if (done) k = 3;
  const q = done ? 1 : (p - cum[k]) / (cum[k + 1] - cum[k]);
  const started = p > 0;
  const active = started && !done;
  const travel = !done && k < 3 && q >= hand;
  const f = travel ? (q - hand) / (1 - hand) : 0;
  const work = active ? Math.min(1, q / hand) : 0;  // how far the active agent is through its own thinking or writing

  let words = 0;
  if (tele) { if (k === 3 || done) words = Math.round(WORDS.tele * (done ? 1 : q)); }
  else { const before = EN_WORDS.slice(0, k).reduce((x, y) => x + y, 0); words = Math.round(done ? WORDS.english : before + EN_WORDS[k] * Math.min(q / hand, 1)); }
  const accent = tele ? "var(--s-telepathy)" : "var(--s-english)";
  const gid = `glow-${mode}`;

  return (
    <div className="relative rounded-2xl bg-well p-4 sm:p-5" style={{ ["--glow" as string]: accent } as React.CSSProperties}>
      {done && <div key={`sh${mode}`} className="shimmer" aria-hidden />}
      <div className="mb-2 flex flex-wrap items-baseline gap-x-6 gap-y-1">
        <div className="text-[15px] font-medium" style={{ color: accent }}>{tele ? "Telepathy" : "Usual multi-agent flow"}</div>
        <div className="text-xs text-muted">{tele ? "agents pass their working memory; only the last one writes" : "every agent writes notes; the next one rereads them"}</div>
        <div className="ml-auto flex gap-5 text-sm tabular-nums">
          <span><b className="font-semibold text-ink">{(SECS[mode] * Math.min(p, 1)).toFixed(1)} s</b> <span className="text-xs text-muted">time</span></span>
          <span><b className="font-semibold text-ink">{words.toLocaleString()}</b> <span className="text-xs text-muted">words</span></span>
        </div>
      </div>
      <div ref={wrap} className="relative">
      <Scroll><div><svg viewBox="0 0 680 150" width="100%" role="img" aria-label="Four agents in a row">
        <title>Planner, Critic, Refiner and Solver</title>
        <defs>
          <filter id={gid} filterUnits="userSpaceOnUse" x="0" y="0" width="680" height="150"><feGaussianBlur stdDeviation="2.6" result="b" /><feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
        </defs>
        {[0, 1, 2].map((i) => {
          const x0 = X[i] + W, x1 = X[i + 1];
          const fill = done || p >= cum[i + 1] ? 1 : k === i && travel ? ease(f) : 0;
          return (
            <g key={i}>
              <line x1={x0} y1={78} x2={x1} y2={78} stroke="var(--axis)" strokeWidth="1.5" strokeDasharray="4 5" />
              {fill > 0 && <line x1={x0} y1={78} x2={x0 + (x1 - x0) * fill} y2={78} stroke={accent} strokeWidth="2.5" strokeLinecap="round" opacity={0.85} filter={tele ? `url(#${gid})` : undefined} />}
              <text x={(x0 + x1) / 2} y={42} textAnchor="middle" fontSize="11" fill="var(--muted)">{tele ? "memory" : "notes"}</text>
            </g>
          );
        })}
        {travel && (() => {
          const x0 = X[k] + W, x1 = X[k + 1], lanes = [60, 78, 96];
          if (tele) {  // a glowing stream of working memory, each particle with a short trail
            const n = 10 * (k + 1);
            return Array.from({ length: n }, (_, d) => {
              const t = ease(Math.max(0, Math.min(1, (f - (d / n) * 0.55) / 0.45)));
              if (t <= 0 || t >= 1) return null;
              const x = x0 + (x1 - x0) * t, y = lanes[d % 3] - Math.sin(Math.PI * t) * 14, o = Math.sin(Math.PI * t);
              return (
                <g key={d} filter={`url(#${gid})`}>
                  <line x1={x - 14} y1={y + 2} x2={x} y2={y} stroke="var(--s-telepathy)" strokeWidth="2" strokeLinecap="round" opacity={o * 0.35} />
                  <circle cx={x} cy={y} r={3.6} fill="var(--s-telepathy)" opacity={o} />
                </g>
              );
            });
          }
          const chips = PHRASES.slice(0, k + 1).flat();  // notes slide straight across
          return chips.map((txt, j) => {
            const t = ease(Math.max(0, Math.min(1, (f - (j / chips.length) * 0.6) / 0.4)));
            if (t <= 0 || t >= 1) return null;
            const wd = txt.length * 5.7 + 16, cx = x0 + (x1 - x0) * t, cy = [56, 80, 104][j % 3];  // straight across, level
            const o = Math.min(1, Math.sin(Math.PI * t) * 2);
            return (
              <g key={j} opacity={o}>
                <rect x={cx - wd / 2} y={cy - 10} width={wd} height={20} rx={10} fill="var(--eng-soft)" stroke="var(--s-english)" strokeOpacity={0.7} />
                <text x={cx} y={cy + 4} textAnchor="middle" fontSize="11" fill="var(--eng-ink)">{txt}</text>
              </g>
            );
          });
        })()}
        {NAMES.map((n, i) => {
          const isActive = active && i === k;
          const fin = started && (i < k || done);
          const c = paint(isActive ? "active" : fin ? "done" : "idle", tele);
          const own = tele ? TE.agents[i] : EN.agents[i];  // this agent's real words and seconds in the recording
          const status = !started ? "" : fin
            ? (i === 3 ? `= ${fmt(ANSWER[mode])}${ANSWER[mode] === RIGHT ? "" : " ✗"}` : `${own.words_written} words · ${own.seconds.toFixed(1)} s`)
            : isActive ? (travel ? "passing on…" : tele && i < 3 ? "thinking…" : "writing…") : "";
          return (
            <g key={n + (i === 3 && done ? "-done" : "")} aria-label={`${n}: ${ROLE[i]}`} className={i === 3 && done ? "pop" : undefined}>
              {isActive && tele && <rect className="halo" x={X[i] - 5} y={25} width={W + 10} height={106} rx={20} fill="none" stroke="var(--s-telepathy)" strokeWidth="2" />}
              <rect x={X[i]} y={30} width={W} height={96} rx={16} fill="#0c0d10" />
              <rect x={X[i]} y={30} width={W} height={96} rx={16} style={{ fill: c.fill, stroke: c.stroke, strokeWidth: 1.5 }} />
              {isActive && !travel && (  // a ring traces round the agent while it thinks or writes
                <rect x={X[i] - 2} y={28} width={W + 4} height={100} rx={18} fill="none" stroke={accent} strokeWidth="2.5" strokeLinecap="round"
                  pathLength={100} strokeDasharray={`${work * 100} 100`} filter={tele ? `url(#${gid})` : undefined} />
              )}
              <text x={X[i] + W / 2} y={70} textAnchor="middle" fontSize="13.5" fontWeight="600" fill="var(--ink)">{n}</text>
              <text x={X[i] + W / 2} y={90} textAnchor="middle" fontSize="11" fill="var(--ink2)">{ROLE[i]}</text>
              <text x={X[i] + W / 2} y={112} textAnchor="middle" fontSize="11" fill={i === 3 && done ? "var(--ok)" : "var(--muted)"}>{status}</text>
            </g>
          );
        })}
        {[0, 1, 2].map((i) => {
          const cx = (X[i] + W + X[i + 1]) / 2;
          if (!(done || p >= cum[i + 1])) return null;
          return (
            <g key={`tip${i}`} className="fade" tabIndex={0} role="button" aria-label={`What ${NAMES[i]} passes to ${NAMES[i + 1]}`} style={{ cursor: "help" }}
              onMouseEnter={(e) => show(e.currentTarget, i)} onMouseLeave={hide}
              onFocus={(e) => show(e.currentTarget, i)} onBlur={hide}
              onClick={(e) => { if (pinned && tipIdx === i) { setPinned(false); setTipIdx(null); } else { setPinned(true); show(e.currentTarget, i); } }}>
              <rect x={X[i] + W - 6} y={40} width={X[i + 1] - X[i] - W + 12} height={96} fill="transparent" />
              <circle cx={cx} cy={102} r={9} fill="var(--well)" stroke={tipIdx === i ? accent : "var(--axis)"} strokeWidth="1.5" style={{ transition: "stroke .15s" }} />
              <text x={cx} y={106} textAnchor="middle" fontSize="11" fontWeight="600" fill="var(--ink2)">i</text>
            </g>
          );
        })}
      </svg>
      </div></Scroll>

      {tipIdx !== null && (
        <div role="tooltip" className="tip pointer-events-none absolute z-20 w-[460px] max-w-[94%] rounded-xl border p-3.5 text-[11.5px] leading-snug shadow-2xl"
          style={{ left: tipPos.left, bottom: tipPos.bottom, transform: "translateX(-50%)", background: "#14151a", borderColor: "var(--hair-strong, #2b2d33)" }}>
          <div className="mb-2 text-[13px] font-medium text-ink">{NAMES[tipIdx]} → {NAMES[tipIdx + 1]}: {tele ? "passes its working memory, no words" : "passes written notes"}</div>
          {tele ? (
            <p className="text-ink2">
              Nothing is written down. The {NAMES[tipIdx]} hands over the model's working memory: everything read and thought so far, passed on directly.
              It took <b className="text-ink">{TE.agents[tipIdx].seconds.toFixed(1)} s</b> and wrote <b className="text-ink">0 words</b>. In the usual flow, the same agent took {EN.agents[tipIdx].seconds.toFixed(1)} s and wrote {EN.agents[tipIdx].words_written} words.
            </p>
          ) : (
            <>
              <ul className="space-y-1 text-ink2">
                {Array.from({ length: tipIdx + 1 }, (_, j) => <li key={j}><b className="font-medium text-ink">{NAMES[j]}</b> <span className="text-muted">({EN_WORDS[j]} words, {EN_SEC[j]} s)</span>: {EN_TXT[j].slice(0, 230)}…</li>)}
              </ul>
              <p className="mt-2 text-muted">The next agent reads all of this before it starts. Real text from the recorded run, shortened here.</p>
            </>
          )}
        </div>
      )}
      </div>
    </div>
  );
}

/** Both flows on one shared clock: press play and watch the same question answered both ways. */
export function AgentTalk({ m }: { m: Measured | null }) {
  const SHOW = 14, HOLD = 3.5;  // the slower flow takes about 14 s on screen, then the result stays up for a moment
  const [t, setT] = useState(0);  // seconds of recorded time
  const [playing, setPlaying] = useState(false);
  const [showRec, setShowRec] = useState(false);
  const box = useRef<HTMLDivElement>(null);
  const end = Math.max(SECS.english, SECS.tele);

  // plays on its own, in a loop, only while it is on screen
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) { setT(end); return; }
    let visible = false, clock = 0, last = 0, raf = 0, wasPlaying = false;
    const obs = new IntersectionObserver(([e]) => { visible = e.isIntersecting; }, { threshold: 0.25 });
    if (box.current) obs.observe(box.current);
    const tick = (ts: number) => {
      const dt = last ? Math.min(0.1, (ts - last) / 1000) : 0;
      last = ts;
      if (visible) {
        clock += dt;
        if (clock > SHOW + HOLD) clock = 0;
        setT(Math.min(end, (clock / SHOW) * end));
        const now = clock < SHOW;
        if (now !== wasPlaying) { wasPlaying = now; setPlaying(now); }
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => { cancelAnimationFrame(raf); obs.disconnect(); };
  }, [end]);
  const pE = Math.min(1, t / SECS.english), pT = Math.min(1, t / SECS.tele);

  return (
    <div ref={box} className="p-5 sm:p-7" style={{ color: "var(--ink)" }}>
      <div className="mb-5 rounded-2xl border-l-[3px] bg-well px-5 py-4" style={{ borderColor: "var(--tel-ink)" }}>
        <div className="mb-1.5 text-[13px] font-medium" style={{ color: "var(--tel-ink)" }}>The question</div>
        <div className="text-[17px] font-medium leading-relaxed text-white">{QUESTION}</div>
      </div>

      <div className="space-y-3">
        <HandoffLane mode="english" p={pE} playing={playing} />
        <HandoffLane mode="tele" p={pT} playing={playing} />
      </div>

      <div className="mt-5 grid grid-cols-3 divide-x divide-hair rounded-2xl py-5 text-center" style={{ background: "var(--tel-soft)" }}>
        {[[`${(EN.seconds / TE.seconds).toFixed(1)}×`, "faster with Telepathy"], [`${Math.round((1 - WORDS.tele / WORDS.english) * 100)}%`, "fewer words written"],
          [ANSWER.english === RIGHT && ANSWER.tele === RIGHT ? fmt(RIGHT) : `${fmt(ANSWER.tele)} / ${fmt(ANSWER.english)}`, ANSWER.english === RIGHT && ANSWER.tele === RIGHT ? "both flows right" : "Telepathy / usual flow"]].map(([v, l]) => (
          <div key={l} className="px-2"><div className="text-2xl font-semibold tabular-nums sm:text-3xl" style={{ color: "var(--tel-ink)" }}>{v}</div><div className="mt-1 text-xs text-ink2">{l}</div></div>
        ))}
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-3 text-xs">
        <span className="rounded-full px-2.5 py-1 font-medium" style={{ background: "var(--ok-soft)", color: "var(--ok)" }}>Real recorded run</span>
        <span className="text-muted">Same model, same GPU. Playback is sped up; the clock shows real seconds.</span>
        <button onClick={() => setShowRec(!showRec)} aria-expanded={showRec} className="ml-auto text-ink2 underline">{showRec ? "Hide the recording" : "See the recording"}</button>
      </div>

      {showRec && (
        <div className="mt-4 rounded-2xl bg-well p-4 text-xs text-ink2">
          <div className="overflow-x-auto">
            <table className="w-full text-left tabular-nums">
              <thead className="text-muted"><tr><th className="py-2 pr-3">agent</th><th className="pr-3">usual flow: seconds</th><th className="pr-3">words</th><th className="pr-3">Telepathy: seconds</th><th>words</th></tr></thead>
              <tbody>
                {EN.agents.map((a, i) => <tr key={a.role} className="border-t border-hair"><td className="py-1.5 pr-3">{NAMES[i]}</td><td>{a.seconds}</td><td>{a.words_written}</td><td>{TE.agents[i].seconds}</td><td>{TE.agents[i].words_written}</td></tr>)}
                <tr className="border-t border-hair font-medium text-ink"><td className="py-1.5 pr-3">Total</td><td>{EN.seconds}</td><td>{WORDS.english}</td><td>{TE.seconds}</td><td>{WORDS.tele}</td></tr>
                
              </tbody>
            </table>
          </div>
          <details className="mt-3">
            <summary className="cursor-pointer text-ink2 underline">Read each agent's full note (usual flow)</summary>
            <div className="mt-2 space-y-2">{EN.agents.map((a, i) => <div key={a.role} className="rounded-xl bg-surface p-3"><b className="text-ink">{NAMES[i]}</b><div className="mt-1 whitespace-pre-wrap">{a.text}</div></div>)}</div>
          </details>
          <div className="mt-3 flex flex-wrap gap-4">
            <a className="text-ink2 underline" href={asset(`/gallery/${REC.id}.json`)} download>Download this recording</a>
            <a className="text-ink2 underline" href="#numbers">See all results</a>
          </div>
          <p className="mt-4 border-t border-hair pt-3 text-[11px] text-muted">
            Across 150 maths questions, Telepathy averaged {m ? (m.textSec / m.teleSec).toFixed(1) : "4.3"}× faster. Run on an NVIDIA Tesla T4 GPU. Technical details are in the files attached.
          </p>
        </div>
      )}
    </div>
  );
}
