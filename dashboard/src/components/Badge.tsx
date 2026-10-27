import type { ReactNode } from "react";

type Kind = "good" | "crit" | "warn" | "idle" | "info";
const tone: Record<Kind, string> = {
  good: "text-good", crit: "text-crit", warn: "text-warn", idle: "text-muted", info: "text-telepathy",
};
const icons: Record<string, ReactNode> = {
  good: <path d="M3.5 8.5l3 3 6-7" />,
  crit: <path d="M8 3v6M8 12v.5" />,
  warn: <path d="M3 8a5 5 0 1 1 1.5 3.5M3 12V8h4" />,
  idle: <path d="M4 8h8" />,
  info: <circle cx="8" cy="8" r="3" />,
};

/** Status chip. Icon + label always: colour is never the only signal. */
export function Badge({ kind, children }: { kind: Kind; children: ReactNode }) {
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border border-hair px-2.5 py-0.5 text-xs font-medium ${tone[kind]}`}
      style={{ background: "color-mix(in srgb, currentColor 9%, transparent)" }}>
      <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8"
        strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{icons[kind]}</svg>
      <span className="text-ink">{children}</span>
    </span>
  );
}

export function RecordedBadge({ synthetic }: { synthetic?: boolean }) {
  return synthetic
    ? <Badge kind="warn">Synthetic sample, not a real run</Badge>
    : <Badge kind="info">Recorded run</Badge>;
}
