import { useElapsed } from "../useLane";
import type { Lane as LaneState } from "../types";
import { Badge, RecordedBadge } from "./Badge";

const title = (r: string) => r.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());
const host = (src: string) => src.replace(/^tavily:/, "").replace(/^https?:\/\//, "").split("/")[0];

/** One team in the race: light card, big clock, four small agent pills. */
export function Lane({ kind, lane }: { kind: "english" | "telepathy"; lane: LaneState }) {
  const seconds = useElapsed(lane);
  const live = lane.provider === "nebius_token_factory";
  const fake = lane.synthetic; // sample recordings carry made-up numbers, so we never show them
  const tele = kind === "telepathy";
  const idx = lane.active ? lane.roles.indexOf(lane.active) : -1;
  const progress = lane.status === "done" ? 1 : lane.status === "running" ? Math.max(0, idx) / lane.roles.length + 0.1 : 0;
  const soft = tele ? "var(--tel-soft)" : "var(--eng-soft)", mark = tele ? "var(--s-telepathy)" : "var(--s-english)", ink = tele ? "var(--tel-ink)" : "var(--eng-ink)";
  const preview = lane.status === "done" ? lane.answer ?? "" : (lane.active ? lane.texts[lane.active] ?? "" : "");

  return (
    <section aria-label={tele ? "Telepathy" : "Usual multi-agent flow"} className="rise rounded-[14px] border border-hair bg-surface p-5 sm:p-6">
      <header className="mb-4 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="h-3 w-3 rounded-full" style={{ background: mark }} aria-hidden />
          <h3 className="text-lg font-semibold">{tele ? "Telepathy" : "Usual multi-agent flow"}</h3>
        </div>
        {live ? <Badge kind="good">Live on Nebius</Badge> : lane.status !== "idle" && lane.recorded && <RecordedBadge synthetic={lane.synthetic} />}
      </header>

      <ol className="mb-5 flex flex-wrap gap-2">
        {lane.roles.map((r, i) => {
          const active = lane.status === "running" && i === idx;
          const fin = lane.status === "done" || (lane.status === "running" && i < idx);
          return (
            <li key={r} className="rounded-full px-3 py-1 text-xs font-medium"
              style={active ? { background: soft, color: ink, outline: `1.5px solid ${mark}` } : fin ? { background: "var(--ok-soft)", color: "var(--ok-ink)" } : { background: "var(--well)", color: "var(--muted)" }}>
              {fin ? "✓ " : ""}{title(r)}
            </li>
          );
        })}
      </ol>

      <div className="flex items-end gap-8">
        <div>
          <div className="text-5xl font-semibold tabular-nums tracking-tight">{fake ? "–" : seconds.toFixed(1)}<span className="ml-1 text-xl font-normal text-muted">{fake ? "" : "s"}</span></div>
          <div className="text-xs text-muted">time</div>
        </div>
        <div>
          <div className="text-3xl font-semibold tabular-nums">{fake ? "–" : Math.round(lane.tokens).toLocaleString()}</div>
          <div className="text-xs text-muted">words written</div>
        </div>
        {tele && (
          <div>
            <div className="text-3xl font-semibold tabular-nums">{fake ? "–" : lane.latentSteps}</div>
            <div className="text-xs text-muted">silent steps</div>
          </div>
        )}
      </div>

      <div className="mt-5 h-2 overflow-hidden rounded-full" style={{ background: "var(--grid)" }}>
        <div className="h-full rounded-full transition-all duration-300" style={{ width: `${Math.min(1, progress) * 100}%`, background: lane.status === "done" ? "var(--ok)" : mark }} />
      </div>

      {live && lane.status === "done" && lane.metrics && (
        <p className="mt-3 text-xs text-ink2">
          {lane.model?.replace(/^nvidia\//, "")} on Nebius Token Factory. Read {Math.round(lane.metrics.tokens_in ?? 0).toLocaleString()} tokens,
          wrote {Math.round(lane.metrics.tokens_out ?? 0).toLocaleString()}. Cost about ${(lane.metrics.cost_usd ?? 0).toFixed(4)} (an estimate at our listed prices).
        </p>
      )}
      {lane.outside && (
        <p className="mt-3 text-xs text-ink2">Read outside content ({lane.outside.count} sources: {[...new Set(lane.outside.sources.map(host))].join(", ")}), so its first handoff is written in English.</p>
      )}
      <p className="mt-4 line-clamp-2 min-h-[2.6rem] text-sm text-ink2">
        {lane.status === "idle" ? "Waiting to start…" : lane.status === "error" ? `Stopped: ${lane.error}` : preview ? preview.slice(-160) : tele ? "Thinking silently…" : "…"}
      </p>
    </section>
  );
}
