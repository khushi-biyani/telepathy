import { useEffect, useState } from "react";
import R from "../data/results.json";
import { Accordion } from "./Accordion";
import { SectionHead } from "./SectionHead";
import { asset } from "../asset";

type Task = (typeof R.tasks)[number];
type M = "single" | "text" | "latent";

export const METHOD = {
  single: { name: "Single agent", color: "#4fb8a3" },
  text: { name: "Multi-agent", color: "var(--s-english)" },
  latent: { name: "Telepathy", color: "var(--s-telepathy)" },
} as const;
const ORDER: M[] = ["single", "text", "latent"];
type Meth = { right: number; acc: number; sec: number; tokens: number };
const meths = (t: Task) => t.methods as Partial<Record<M, Meth>>;
const present = (t: Task) => ORDER.filter((m) => meths(t)[m]);  // web research has no single-agent run

export const times = (x: number) => `${x >= 10 ? Math.round(x) : x}×`;

/** Headline ranges across the three tasks, for the hero. All computed from results.json. */
export function headline() {
  const sp = R.tasks.map((t) => t.speedup_vs_team), tk = R.tasks.map((t) => t.tokens_saved_vs_team);
  const asGood = R.tasks.every((t) => t.methods.latent.acc >= t.methods.text.acc);
  return { speedMin: Math.min(...sp), speedMax: Math.max(...sp), tokMin: Math.min(...tk), tokMax: Math.max(...tk), asGood, n: R.tasks.length };
}

/** Tokens written per question, three ways per test. Hover (or tap) a bar for accuracy and time. */
function TokenChart() {
  const [hover, setHover] = useState<{ t: Task; m: M; x: number; y: number } | null>(null);
  const max = Math.max(...R.tasks.flatMap((t) => present(t).map((m) => meths(t)[m]!.tokens)));
  const W = 960, H = 360, top = 36, base = 250, bw = 46, gap = 12;
  const step = W / R.tasks.length;
  return (
    <div className="relative">
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label="Tokens written per question for each way of working">
        <line x1={20} x2={W - 20} y1={base} y2={base} stroke="var(--hair-strong)" />
        {R.tasks.map((t, gi) => {
          const ms = present(t), groupW = ms.length * bw + (ms.length - 1) * gap;
          const gx = gi * step + (step - groupW) / 2;
          const tm = meths(t), sameRight = tm.text && tm.latent && tm.text.right === tm.latent.right;
          return (
            <g key={t.key}>
              {ms.map((m, i) => {
                const v = tm[m]!.tokens, h = Math.max(3, ((base - top) * v) / max), x = gx + i * (bw + gap);
                const on = hover?.t.key === t.key && hover.m === m;
                return (
                  <g key={m} style={{ cursor: "pointer" }}
                    onMouseEnter={() => setHover({ t, m, x: x + bw / 2, y: base - h })} onMouseLeave={() => setHover(null)}
                    onClick={() => setHover(on ? null : { t, m, x: x + bw / 2, y: base - h })}>
                    <rect x={x - 6} y={top - 10} width={bw + 12} height={base - top + 10} fill="transparent" />
                    <rect x={x} y={base - h} width={bw} height={h} rx={6} fill={METHOD[m].color} opacity={hover && !on ? 0.45 : 1} />
                    <text x={x + bw / 2} y={base - h - 8} textAnchor="middle" fontSize="13" fill="var(--ink)">{v.toLocaleString()}</text>
                  </g>
                );
              })}
              <text x={gx + groupW / 2} y={base + 28} textAnchor="middle" fontSize="15" fontWeight="500" fill="var(--ink)">{t.label}</text>
              {t.n < 20 && <text x={gx + groupW / 2} y={base + 46} textAnchor="middle" fontSize="12" fill="var(--muted)">{t.n} questions{sameRight ? `, ${tm.latent!.right} of ${t.n} right each` : ""}</text>}
              <text x={gx + groupW / 2} y={base + (t.n < 20 ? 68 : 50)} textAnchor="middle" fontSize="13" fill="var(--tel-ink)">Telepathy: {times(t.speedup_vs_team)} faster</text>
              <text x={gx + groupW / 2} y={base + (t.n < 20 ? 86 : 68)} textAnchor="middle" fontSize="13" fill="var(--tel-ink)">{t.tokens_saved_vs_team}% fewer tokens</text>
            </g>
          );
        })}
      </svg>
      {hover && (
        <div className="pointer-events-none absolute z-10 w-52 -translate-x-1/2 -translate-y-full rounded-xl border p-3 text-xs shadow-2xl"
          style={{ left: `${(hover.x / W) * 100}%`, top: `calc(${(hover.y / H) * 100}% - 10px)`, background: "#14151a", borderColor: "var(--hair-strong)" }}>
          <div className="mb-1.5 font-medium" style={{ color: METHOD[hover.m].color }}>{METHOD[hover.m].name} · {hover.t.label}</div>
          <div className="flex justify-between text-ink2"><span>Accuracy</span><b className="tabular-nums text-ink">{meths(hover.t)[hover.m]!.acc}%</b></div>
          <div className="flex justify-between text-ink2"><span>Time per question</span><b className="tabular-nums text-ink">{meths(hover.t)[hover.m]!.sec} s</b></div>
          <div className="flex justify-between text-ink2"><span>Tokens written</span><b className="tabular-nums text-ink">{meths(hover.t)[hover.m]!.tokens.toLocaleString()}</b></div>
        </div>
      )}
    </div>
  );
}

type Row = { id: string; seconds: number; tokens: number };

/** Every question of one test: time and tokens for each way of working. Loaded from the raw files. */
function AllQuestions() {
  const [task, setTask] = useState(R.tasks[0].key);
  const [rows, setRows] = useState<Record<M, Record<string, Row>> | null>(null);
  const [qs, setQs] = useState<Record<string, string>>({});
  const [all, setAll] = useState(false);
  const [open, setOpen] = useState<string | null>(null);
  useEffect(() => { fetch(asset("/evidence/slim/questions.json")).then((r) => r.json()).then(setQs).catch(() => {}); }, []);
  const cur = R.tasks.find((t) => t.key === task)!, ms = present(cur);
  useEffect(() => {
    setRows(null); setAll(false);
    Promise.all(present(R.tasks.find((t) => t.key === task)!).map(async (m) => [m, Object.fromEntries(((await (await fetch(asset(`/evidence/slim/${task}_${m}.json`))).json()) as Row[]).map((r) => [r.id, r]))] as const))
      .then((e) => setRows(Object.fromEntries(e) as Record<M, Record<string, Row>>)).catch(() => setRows(null));
  }, [task]);
  const ids = rows ? Object.keys(rows.latent) : [];
  return (
    <div>
      <div className="mb-3 flex flex-wrap gap-2">
        {R.tasks.map(({ key: k, label }) => (
          <button key={k} onClick={() => setTask(k)} className={`rounded-full px-3.5 py-1.5 text-sm ${task === k ? "bg-tel-soft text-tel-ink" : "bg-well text-ink2"}`}>{label}</button>
        ))}
      </div>
      {!rows ? <p className="text-sm text-muted">Loading…</p> : (
        <>
          <div className="max-h-[28rem] overflow-auto rounded-xl border border-hair">
            <table className="w-full table-fixed text-left text-xs tabular-nums">
              <thead className="sticky top-0 bg-well text-muted">
                <tr>
                  <th rowSpan={2} className="w-[26%] px-3 py-2 align-middle font-medium">Question</th>
                  {ms.map((m) => <th key={m} colSpan={2} className="border-l border-hair px-3 pt-2 text-center font-medium" style={{ color: METHOD[m].color }}>{METHOD[m].name}</th>)}
                </tr>
                <tr>
                  {ms.map((m) => [
                    <th key={`${m}t`} className="border-l border-hair px-2.5 pb-2 text-center align-bottom font-normal leading-tight">Time<br />Taken</th>,
                    <th key={`${m}k`} className="px-2.5 pb-2 text-center align-bottom font-normal leading-tight">Tokens<br />Consumed</th>,
                  ])}
                </tr>
              </thead>
              <tbody>{(all ? ids : ids.slice(0, 15)).map((id) => (
                <tr key={id} className="border-t border-hair align-top">
                  <td className="px-3 py-1.5 text-ink2">
                    <button onClick={() => setOpen(open === id ? null : id)} aria-expanded={open === id} className="flex w-full items-start gap-1.5 text-left hover:text-ink">
                      <span className={`mt-px shrink-0 text-muted transition-transform ${open === id ? "rotate-90" : ""}`} aria-hidden>›</span>
                      <span className={open === id ? "min-w-0 whitespace-normal text-ink" : "min-w-0 truncate"}>{qs[id] ?? id}</span>
                    </button>
                  </td>
                  {ms.map((m) => { const r = rows[m]?.[id]; return [
                    <td key={`${m}t`} className="whitespace-nowrap border-l border-hair px-2.5 py-1.5 text-center">{r ? `${r.seconds.toFixed(1)} s` : "–"}</td>,
                    <td key={`${m}k`} className="whitespace-nowrap px-2.5 py-1.5 text-center">{r ? r.tokens.toLocaleString() : "–"}</td>,
                  ]; })}
                </tr>
              ))}</tbody>
            </table>
          </div>
          {ids.length > 15 && <button onClick={() => setAll(!all)} className="mt-2 text-xs text-ink2 underline">{all ? "Show fewer" : `Show all ${ids.length} questions`}</button>}
        </>
      )}
    </div>
  );
}

export function Results() {
  const h = headline();
  return (
    <div>
      <SectionHead label="Results" title="Same model. Same questions. Three ways to work."
        sub={`Against a usual multi-agent system, Telepathy was ${times(h.speedMin)} to ${times(h.speedMax)} faster and wrote ${h.tokMin}% to ${h.tokMax}% fewer tokens, with the same or better accuracy.`} />
      <div className="rounded-3xl bg-surface p-6 sm:p-8">
        <div className="mb-2 flex flex-wrap items-center gap-5 text-xs text-ink2">
          {ORDER.map((m) => <span key={m} className="flex items-center gap-2"><i className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: METHOD[m].color }} />{METHOD[m].name}</span>)}
          <span className="ml-auto text-muted">Tokens written per question · hover a bar for accuracy and time</span>
        </div>
        <TokenChart />
      </div>
      <div className="mt-4">
        <Accordion title="Raw results"><AllQuestions /></Accordion>
      </div>
    </div>
  );
}
