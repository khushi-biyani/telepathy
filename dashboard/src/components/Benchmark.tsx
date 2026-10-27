import { SectionHead } from "./SectionHead";
import { Accordion } from "./Accordion";
import { Dumbbell, type DumbRow } from "./charts";
import type { Benchmarks, ModeStats } from "../types";

type Row = ModeStats & { key: string };

function wilson(p: number, n: number): [number, number] {
  const z = 1.96, d = 1 + (z * z) / n, c = (p + (z * z) / (2 * n)) / d;
  const h = (z * Math.sqrt((p * (1 - p)) / n + (z * z) / (4 * n * n))) / d;
  return [Math.max(0, c - h) * 100, Math.min(1, c + h) * 100];
}

/** Group results by folder so two splits are never mixed in one comparison. */
function groups(data: Benchmarks) {
  const g: Record<string, Record<string, Row>> = {};
  for (const [key, v] of Object.entries(data.modes)) {
    const [folder, stem] = key.split("/");
    (g[folder] ??= {})[stem.replace(/^[a-z0-9]+_(all|dev|test)_/, "")] = { key, ...v };
  }
  return g;
}

function Dot({ c, label }: { c: string; label: string }) {
  return <span className="flex items-center gap-2"><i className="inline-block h-3 w-3 rounded-full" style={{ background: c }} />{label}</span>;
}

export function Numbers({ data }: { data: Benchmarks | null }) {
  if (!data) return <p className="text-center text-sm text-muted">Loading…</p>;
  const g = groups(data);
  const main = g.test?.text && g.test?.latent_s10 ? "test" : Object.keys(g).find((k) => g[k].text && g[k].latent_s10);
  if (!main) return <p className="text-center text-sm text-muted">No measured results yet.</p>;
  const t = g[main].text, l = g[main].latent_s10;
  const sweep = g.gate ?? g.dev;
  const split = main === "test" ? "150 grade-school maths questions we never tuned on" : "50 grade-school maths questions";

  const rows: DumbRow[] = [
    { label: "Time per question", note: "lower is better", a: t.sec_avg!, b: l.sec_avg!, max: t.sec_avg! * 1.18, fmt: (v) => `${v.toFixed(0)} s` },
    { label: "Words written", note: "lower is better", a: t.tokens_written!, b: l.tokens_written!, max: t.tokens_written! * 1.18, fmt: (v) => Math.round(v).toLocaleString() },
    { label: "Right answers", note: "whiskers: likely range (scale starts at 40%)", a: t.accuracy! * 100, b: l.accuracy! * 100, min: 40, max: 100, fmt: (v) => `${Math.round(v)}%`,
      rangeA: wilson(t.accuracy!, t.n), rangeB: wilson(l.accuracy!, l.n) },
  ];

  return (
    <div>
      <SectionHead label="The evidence" title="Same answers, a fraction of the time" sub={`Measured on ${split}, with one model on one GPU.`} />
      <div className="rounded-[14px] border border-hair bg-surface p-5 sm:p-8">
        <div className="mb-3 flex justify-center gap-6 text-sm text-ink2"><Dot c="var(--s-english)" label="Usual multi-agent flow" /><Dot c="var(--s-telepathy)" label="Telepathy" /></div>
        <Dumbbell rows={rows} />
      </div>
      <div className="mt-5 space-y-3">
        <Accordion title="How we tested it">
          <ul className="list-disc space-y-1 pl-5">
            <li>The same four agents (Planner, Critic, Refiner, Solver) answered the same questions both ways.</li>
            <li>Model: NVIDIA Nemotron Nano 4B, on a free Kaggle T4 GPU, always picking the most likely word so runs repeat.</li>
            <li>We picked the number of silent steps (10) on a separate set of 50 questions, then measured on the other 150.</li>
            <li>Accuracy is about the same. At this size, a few points either way is noise, so we say "same", not "better".</li>
          </ul>
        </Accordion>
        {sweep?.text && (
          <Accordion title="How many silent steps?">
            <p className="mb-3">Tried on the 50 tuning questions. Differences in accuracy here are within noise; more steps cost a little more time.</p>
            <div className="overflow-x-auto"><table className="w-full text-left tabular-nums">
              <thead className="text-muted"><tr>{["Team", "Right", "Seconds", "Words"].map((h) => <th key={h} className="py-1 pr-4 font-medium">{h}</th>)}</tr></thead>
              <tbody>{[["Usual multi-agent flow", sweep.text], ...[5, 10, 20].filter((s) => sweep[`latent_s${s}`]).map((s) => [`Telepathy, ${s} steps`, sweep[`latent_s${s}`]] as [string, Row])].map(([name, r]) => (
                <tr key={name as string} className="border-t border-hair"><td className="py-1.5 pr-4">{name as string}</td>
                  <td className="pr-4">{Math.round((r as Row).accuracy! * 100)}%</td><td className="pr-4">{(r as Row).sec_avg!.toFixed(1)}</td><td>{Math.round((r as Row).tokens_written!)}</td></tr>))}</tbody>
            </table></div>
          </Accordion>
        )}
        <Accordion title="What these numbers do not show">
          <ul className="list-disc space-y-1 pl-5">
            <li>Only maths questions. We have not measured writing, coding or research tasks.</li>
            <li>Only one team shape and one model, on one kind of GPU.</li>
            <li>We have not yet compared against a single agent working alone.</li>
          </ul>
        </Accordion>
      </div>
    </div>
  );
}
