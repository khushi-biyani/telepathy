import { SectionHead } from "./SectionHead";
import { useState } from "react";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { perDay, type Measured } from "../savings";
import type { TeamSize } from "../types";
import { Accordion } from "./Accordion";
import { Ring, Timeline } from "./charts";

const fmt = (n: number, d = 0) => n.toLocaleString(undefined, { maximumFractionDigits: d });
const millions = (n: number) => (n >= 1e6 ? `${(n / 1e6).toFixed(1)} million` : fmt(n));

function Card({ title, sub, children }: { title: string; sub?: string; children: React.ReactNode }) {
  return (
    <figure className="rounded-[14px] border border-hair bg-surface p-5 sm:p-6">
      <figcaption className="mb-4"><div className="font-semibold">{title}</div>{sub && <div className="text-sm text-ink2">{sub}</div>}</figcaption>
      {children}
    </figure>
  );
}

function Tile({ big, label }: { big: string; label: string }) {
  return (
    <div className="flex flex-col justify-center rounded-[14px] border border-hair bg-surface p-5">
      <div className="text-3xl font-semibold tracking-tight sm:text-4xl">{big}</div>
      <div className="mt-1 text-sm text-ink2">{label}</div>
    </div>
  );
}

function Tip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-xl border border-hair bg-surface px-3 py-2 text-xs shadow-md">
      <div className="mb-1 font-semibold">{fmt(label)} tasks done</div>
      {payload.map((p: any) => <div key={p.dataKey} className="text-ink2">{p.name}: {fmt(p.value, 1)} hours</div>)}
    </div>
  );
}

function SizeTip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="rounded-xl border border-hair bg-surface px-3 py-2 text-xs shadow-md">
      <div className="mb-1 font-semibold">{label} agents</div>
      <div className="text-ink2">Read: {fmt(d.read)} tokens</div>
      <div className="text-ink2">Wrote: {fmt(d.written)} tokens</div>
      <div className="text-ink2">Time: {d.sec.toFixed(1)} s</div>
      <div className="text-ink2">Right answers: {Math.round(d.accuracy * 100)}%</div>
    </div>
  );
}

/** Measured on Nebius Token Factory (Nemotron 3 Super): what a written-notes team costs as it grows. */
function TeamGrowth({ sizes }: { sizes: Record<string, TeamSize> }) {
  const rows = Object.entries(sizes).map(([n, s]) => ({ agents: Number(n), read: Math.round(s.tokens_in), written: Math.round(s.tokens_out), sec: s.sec_avg, accuracy: s.accuracy, questions: s.questions })).sort((a, b) => a.agents - b.agents);
  return (
    <div className="mt-5 space-y-3">
      <Card title="As the team grows" sub="What a written-notes team reads and writes for one question, measured live on Nebius.">
        <div className="h-64" role="img" aria-label="Tokens read and written per question for teams of different sizes">
          <ResponsiveContainer>
            <BarChart data={rows} margin={{ top: 10, right: 12, left: 0, bottom: 4 }} barCategoryGap="30%">
              <CartesianGrid vertical={false} stroke="var(--grid)" />
              <XAxis dataKey="agents" tickFormatter={(v) => `${v} agents`} tickLine={false} axisLine={{ stroke: "var(--axis)" }} tick={{ fill: "var(--muted)", fontSize: 12 }} />
              <YAxis tickLine={false} axisLine={false} width={52} tick={{ fill: "var(--muted)", fontSize: 12 }} tickFormatter={(v) => (v >= 1000 ? `${v / 1000}k` : String(v))} />
              <Tooltip content={<SizeTip />} cursor={{ fill: "var(--grid)", opacity: 0.5 }} />
              <Bar name="Tokens read" dataKey="read" stackId="a" fill="var(--eng-soft)" stroke="var(--s-english)" strokeOpacity={0.55} isAnimationActive={false} />
              <Bar name="Tokens written" dataKey="written" stackId="a" fill="var(--s-english)" radius={[6, 6, 0, 0]} isAnimationActive={false} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="mt-2 flex gap-4 text-xs text-ink2">
          <span className="flex items-center gap-2"><i className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: "var(--eng-soft)", border: "1px solid var(--s-english)" }} />Tokens read</span>
          <span className="flex items-center gap-2"><i className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: "var(--s-english)" }} />Tokens written</span>
        </div>
        <p className="mt-2 text-xs text-muted">
          Every agent re-reads the earlier notes, so reading grows much faster than writing. Telepathy at these team sizes is not measured yet, so it is not shown.
        </p>
      </Card>
      <Accordion title="The numbers behind this chart">
        <p className="mb-3">Nemotron 3 Super on Nebius Token Factory, the same questions at every team size. This is a different, much bigger model than the one Telepathy runs, so do not compare these seconds with Telepathy's.</p>
        <div className="overflow-x-auto"><table className="w-full text-left tabular-nums">
          <thead className="text-muted"><tr>{["Agents", "Questions", "Right", "Seconds", "Read", "Wrote"].map((h) => <th key={h} className="py-1 pr-4 font-medium">{h}</th>)}</tr></thead>
          <tbody>{rows.map((r) => <tr key={r.agents} className="border-t border-hair"><td className="py-1.5 pr-4">{r.agents}</td><td className="pr-4">{r.questions}</td><td className="pr-4">{Math.round(r.accuracy * 100)}%</td><td className="pr-4">{r.sec.toFixed(1)}</td><td className="pr-4">{fmt(r.read)}</td><td>{fmt(r.written)}</td></tr>)}</tbody>
        </table></div>
      </Accordion>
    </div>
  );
}

/** Only measured numbers. The slider multiplies the measured per-question results by your number of tasks. */
export function Savings({ m, loading, teamSizes }: { m: Measured | null; loading?: boolean; teamSizes?: Record<string, TeamSize> }) {
  const [tasks, setTasks] = useState(10000);
  if (!m) return <p className="text-center text-sm text-muted">{loading ? "Loading…" : "No measured results yet."}</p>;

  const day = perDay(m, tasks);
  const fewer = 1 - m.teleTokens / m.textTokens;
  const data = Array.from({ length: 11 }, (_, i) => {
    const t = (tasks * i) / 10;
    return { tasks: Math.round(t), english: +((m.textSec * t) / 3600).toFixed(2), tele: +((m.teleSec * t) / 3600).toFixed(2) };
  });

  return (
    <div>
      <SectionHead label="The savings" title="What it saves" sub="Our measured results, scaled to how many tasks you run." />

      <div className="mb-5 rounded-[14px] border border-hair bg-surface p-6">
        <label htmlFor="tasks" className="mb-2 flex items-baseline justify-between text-sm text-ink2">Tasks per day<b className="text-lg font-semibold tabular-nums text-ink">{fmt(tasks)}</b></label>
        <input id="tasks" type="range" min={100} max={100000} step={100} value={tasks} onChange={(e) => setTasks(+e.target.value)} className="w-full accent-[var(--s-telepathy)]" />
      </div>

      <div className="mb-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="flex items-center justify-center rounded-[14px] border border-hair bg-surface p-4"><Ring value={fewer} label="fewer words written" /></div>
        <Tile big={`×${(m.textSec / m.teleSec).toFixed(1)}`} label={`faster: ${m.textSec.toFixed(0)} s down to ${m.teleSec.toFixed(0)} s per question`} />
        <Tile big={`${fmt(day.hoursSaved, 1)} h`} label={`of computer time saved a day at ${fmt(tasks)} tasks`} />
        <Tile big={millions(day.wordsSaved)} label="fewer words written a day" />
      </div>

      <div className="space-y-5">
        <Card title="One question" sub="How long each team took, measured.">
          <Timeline englishSec={m.textSec} teleSec={m.teleSec} />
        </Card>
        <Card title="Over a day" sub="Computer time used as the tasks get done. The gap between the lines is the time saved.">
          <div className="h-64" role="img" aria-label="Computer hours used as tasks are completed, written notes versus Telepathy">
            <ResponsiveContainer>
              <AreaChart data={data} margin={{ top: 10, right: 12, left: 0, bottom: 4 }}>
                <CartesianGrid vertical={false} stroke="var(--grid)" />
                <XAxis dataKey="tasks" tickFormatter={(v) => (v >= 1000 ? `${v / 1000}k` : String(v))} tickLine={false} axisLine={{ stroke: "var(--axis)" }} tick={{ fill: "var(--muted)", fontSize: 12 }} />
                <YAxis tickLine={false} axisLine={false} width={44} tick={{ fill: "var(--muted)", fontSize: 12 }} unit="h" />
                <Tooltip content={<Tip />} cursor={{ stroke: "var(--axis)" }} />
                <Area name="Usual multi-agent flow" dataKey="english" stroke="var(--s-english)" strokeWidth={2.5} fill="var(--eng-soft)" fillOpacity={1} isAnimationActive={false} />
                <Area name="Telepathy" dataKey="tele" stroke="var(--s-telepathy)" strokeWidth={2.5} fill="var(--tel-soft)" fillOpacity={1} isAnimationActive={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-2 flex gap-4 text-xs text-ink2">
            <span className="flex items-center gap-2"><i className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: "var(--s-english)" }} />Usual multi-agent flow</span>
            <span className="flex items-center gap-2"><i className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: "var(--s-telepathy)" }} />Telepathy</span>
          </div>
        </Card>
      </div>

      {teamSizes && Object.keys(teamSizes).length > 1 && <TeamGrowth sizes={teamSizes} />}

      <p className="mx-auto mt-5 max-w-2xl text-center text-xs text-muted">
        The comparison above comes from our measurement of a 4-agent team on {m.split}. The per-day figures just multiply the measured per-question
        results by the number of tasks you pick. Telepathy has not been measured at other team sizes yet, so none is shown.
        The team-size chart is for the written-notes team only.
      </p>
    </div>
  );
}
