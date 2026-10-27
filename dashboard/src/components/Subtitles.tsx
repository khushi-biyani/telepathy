import { useState } from "react";
import type { Lane } from "../types";
import { Badge } from "./Badge";

const title = (r: string) => r.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());

function Verdict({ faithful, fallback, reason }: { faithful?: boolean; fallback?: string; reason?: string }) {
  if (reason === "tainted") return <Badge kind="warn">Read outside content: English</Badge>;
  if (reason === "high_stakes") return <Badge kind="warn">High-stakes role: English</Badge>;
  if (fallback) return <Badge kind="warn">Switched to English</Badge>;
  if (faithful === true) return <Badge kind="good">Answer unchanged</Badge>;
  if (faithful === false) return <Badge kind="crit">Answer changed</Badge>;
  return <Badge kind="idle">Not audited</Badge>;
}

/** The silent handoffs, with the plain-English subtitle and honesty verdict for each. */
export function Subtitles({ lane }: { lane: Lane }) {
  const [sel, setSel] = useState(0);
  const hs = lane.handoffs;
  if (!hs.length) {
    return <p className="text-sm text-muted">Handoffs appear here as the agents pass work on.</p>;
  }
  const h = hs.find((x) => x.idx === sel) ?? hs[0];
  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-2" role="tablist" aria-label="Handoffs">
        {hs.map((x, i) => (
          <div key={x.idx} className="flex items-center gap-2">
            {i === 0 && <span className="text-sm font-medium">{title(x.from)}</span>}
            <button role="tab" aria-selected={h.idx === x.idx} onClick={() => setSel(x.idx)}
              className="flex items-center gap-1.5 rounded-full border border-hair px-3 py-1 text-xs font-medium hover:bg-well"
              style={h.idx === x.idx ? { borderColor: "var(--s-telepathy)", background: "color-mix(in srgb, var(--s-telepathy) 12%, transparent)" } : undefined}>
              {x.mode === "latent" ? "silent" : "English"} →
              {x.faithful === false && <span className="text-crit" aria-label="flagged">!</span>}
              {x.faithful === true && <span className="text-good" aria-label="faithful">✓</span>}
            </button>
            <span className="text-sm font-medium">{title(x.to)}</span>
          </div>
        ))}
      </div>

      <div className="rounded-xl border border-hair bg-well p-4">
        <div className="mb-2 flex flex-wrap items-center gap-2">
          <span className="text-sm font-semibold">{title(h.from)} → {title(h.to)}</span>
          <Verdict faithful={h.faithful} fallback={h.fallback} reason={h.reason} />
          {h.js != null && <span className="text-xs text-muted tabular-nums">divergence {h.js.toFixed(3)}</span>}
          {h.share === "thoughts_only" && <Badge kind="info">Thoughts only</Badge>}
        </div>
        {h.reason === "tainted" && (
          <div className="mb-3 text-sm">
            <p className="mb-2 text-ink2">
              {title(h.from)} read outside content, which is untrusted. So this handoff is written in English
              where a human can read it, and the raw outside text never enters the team's shared memory.
            </p>
            <p className="whitespace-pre-wrap text-ink">{lane.texts[h.from] || "(no text recorded)"}</p>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              {h.scan
                ? h.scan.flagged
                  ? <Badge kind="crit">Instruction scan: flagged</Badge>
                  : <Badge kind="idle">Scan: nothing found</Badge>
                : <Badge kind="idle">Scan not run</Badge>}
              {h.scan?.flagged && <span className="text-xs text-ink2">{h.scan.reasons.join(", ")}. {h.scan.action === "block" ? "Handoff blocked." : "Shown as a warning; the run continued."}</span>}
              {h.scan && !h.scan.flagged && <span className="text-xs text-muted">A clean scan does not make content trusted.</span>}
            </div>
          </div>
        )}
        {h.reason === "tainted" ? null : h.subtitle
          ? <p className="text-ink">“{h.subtitle}”</p>
          : <p className="text-sm text-muted">{h.mode === "text" ? "This handoff was written in English, so the notes themselves are the record." : "No subtitle was generated for this handoff."}</p>}
        {h.fallback && (
          <p className="mt-3 text-sm text-ink2">
            The honesty check found that the next agent answered differently when given only this subtitle, so
            auto mode redid this handoff in English and carried on from there.
          </p>
        )}
        {h.faithful === true && !h.fallback && (
          <p className="mt-3 text-sm text-ink2">
            When the later agents read only this summary instead of the real memory, they reached the same final answer. That does not prove the summary matches the hidden thinking.
          </p>
        )}
      </div>
    </div>
  );
}
