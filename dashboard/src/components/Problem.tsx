import type { TeamSize } from "../types";
import { SectionHead } from "./SectionHead";

const fmt = (n: number) => Math.round(n).toLocaleString();

/** One idea: every agent you add has to read everything written before it. Measured on Nebius. */
export function Problem({ teamSizes }: { teamSizes?: Record<string, TeamSize> }) {
  const rows = ["2", "4", "6", "8"].map((k) => [k, teamSizes?.[k]] as const).filter(([, v]) => v) as (readonly [string, TeamSize])[];
  const max = Math.max(...rows.map(([, v]) => v.tokens_in), 1);
  return (
    <div className="grid items-center gap-12 lg:grid-cols-[1fr_1.1fr]">
      <SectionHead label="The problem" title="Every agent you add has to read everything before it"
        sub="In a multi-agent system, each agent writes its thinking out and the next one reads all of it. Add agents and the reading piles up, and so do time and cost." />
      {rows.length > 0 && (
        <figure>
          <div className="space-y-4">
            {rows.map(([k, v]) => (
              <div key={k} className="grid grid-cols-[72px_1fr_64px] items-center gap-4">
                <span className="text-sm text-ink2">{k} agents</span>
                <div className="h-2 rounded-full bg-well"><div className="h-2 rounded-full" style={{ width: `${(v.tokens_in / max) * 100}%`, background: "var(--s-english)" }} /></div>
                <span className="text-right text-sm tabular-nums text-ink">{fmt(v.tokens_in)}</span>
              </div>
            ))}
          </div>
          <figcaption className="mt-5 text-xs text-muted">Tokens read per question by the usual team, measured on Nebius Token Factory with NVIDIA Nemotron 3 Super.</figcaption>
        </figure>
      )}
    </div>
  );
}
