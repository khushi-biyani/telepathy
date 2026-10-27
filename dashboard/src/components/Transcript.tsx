import type { Lane } from "../types";
import { DEFAULT_ROLES } from "../lane";

const title = (r: string) => r.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());

const whyText = (reason?: string) =>
  reason === "tainted" ? "read outside content, so written in English"
    : reason === "unfaithful" ? "subtitle failed the check, so redone in English"
    : reason === "high_stakes" ? "high-stakes role, written in English" : "written in English";

function Bubble({ who, accent, children, dashed }: { who: string; accent: string; children: React.ReactNode; dashed?: boolean }) {
  return (
    <li className="flex gap-3">
      <span className="mt-1 h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: accent }} aria-hidden />
      <div className={`min-w-0 flex-1 rounded-xl border p-3 text-sm ${dashed ? "border-dashed" : ""} border-hair bg-well`}>
        <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted">{who}</div>
        {children}
      </div>
    </li>
  );
}

/** The whole conversation, so nothing about how the agents talked is hidden. */
export function Transcript({ kind, lane }: { kind: "english" | "telepathy"; lane: Lane }) {
  const tele = kind === "telepathy";
  const accent = tele ? "var(--s-telepathy)" : "var(--s-english)";
  const roles = lane.roles.length ? lane.roles : DEFAULT_ROLES;
  const final = roles[roles.length - 1];

  if (lane.status === "idle") return <p className="text-sm text-muted">The conversation appears here once a race runs.</p>;

  return (
    <div>
      <p className="mb-3 text-sm text-ink2">
        {tele
          ? "No words pass between the first agents. What a human can read are the subtitles below, written afterwards."
          : "Every word the agents wrote to each other, in order."}
      </p>
      <ol className="space-y-3">
        {roles.map((r, i) => {
          const isFinal = r === final;
          const text = lane.texts[r] ?? "";
          const steps = lane.steps[r] ?? 0;
          const h = lane.handoffs.find((x) => x.idx === i);
          if (tele && !isFinal && (h?.mode ?? "latent") === "latent") {
            return (
              <Bubble key={r} who={title(r)} accent={accent}>
                <div className="flex items-center gap-2 text-ink2">
                  <span aria-hidden className="font-mono tracking-widest">▮▮▮▮▮▮</span>
                  <span>{steps > 0 ? `${steps} silent thought steps, 0 words written` : "thinking silently…"}</span>
                </div>
                {h?.subtitle && (
                  <div className="mt-2 rounded-lg border border-dashed border-hair p-2">
                    <div className="mb-0.5 text-xs text-muted">Subtitle: a plain-English summary written afterwards. It is not what the next agent received.</div>
                    <p className="text-ink">“{h.subtitle}”</p>
                  </div>
                )}
              </Bubble>
            );
          }
          return (
            <Bubble key={r} who={`${title(r)}${isFinal ? " (final answer)" : tele ? ` (${whyText(h?.reason)})` : ""}`} accent={accent}>
              {text ? <p className="whitespace-pre-wrap text-ink">{text}</p> : <span className="text-muted">{lane.status === "running" ? "…" : "nothing recorded"}</span>}
            </Bubble>
          );
        })}
      </ol>
    </div>
  );
}
