/** On a narrow screen, keep chart text readable and let the chart scroll sideways instead of shrinking. */
export function Scroll({ children }: { children: React.ReactNode }) {
  return <div className="-mx-1 overflow-x-auto px-1"><div className="min-w-[560px]">{children}</div></div>;
}

/** A ring showing a share, with the number in the middle. */
export function Ring({ value, label }: { value: number; label: string }) {
  const r = 54, c = 2 * Math.PI * r;
  return (
    <div className="flex flex-col items-center">
      <svg viewBox="0 0 140 140" className="h-40 w-40" role="img" aria-label={`${Math.round(value * 100)} percent ${label}`}>
        <circle cx="70" cy="70" r={r} fill="none" stroke="var(--grid)" strokeWidth="16" />
        <circle cx="70" cy="70" r={r} fill="none" stroke="var(--ok)" strokeWidth="16" strokeLinecap="round"
          strokeDasharray={`${c * value} ${c}`} transform="rotate(-90 70 70)" />
        <text x="70" y="76" textAnchor="middle" fontSize="30" fontWeight="600" fill="var(--ink)">{Math.round(value * 100)}%</text>
      </svg>
      <div className="-mt-1 text-sm text-ink2">{label}</div>
    </div>
  );
}

/** One task, measured: how long each team took, side by side. */
export function Timeline({ englishSec, teleSec }: { englishSec: number; teleSec: number }) {
  const x0 = 100, x1 = 650, sc = (x1 - x0) / englishSec;
  const step = englishSec > 120 ? 40 : englishSec > 60 ? 20 : 10;
  const ticks: number[] = []; for (let t = 0; t <= englishSec + 0.1; t += step) ticks.push(t);
  return (
    <Scroll>
      <svg viewBox="0 0 680 200" width="100%" role="img" aria-label={`One question: the written-notes team takes ${englishSec.toFixed(0)} seconds, Telepathy ${teleSec.toFixed(0)} seconds`}>
        <text x="0" y="56" fontSize="13" fontWeight="600" fill="var(--ink)">Usual multi-agent flow</text>
        <text x="0" y="116" fontSize="13" fontWeight="600" fill="var(--ink)">Telepathy</text>
        <rect x={x0} y={36} width={englishSec * sc} height={34} rx={9} fill="var(--s-english)" opacity="0.85"><title>{`Usual multi-agent flow: ${englishSec.toFixed(1)} s`}</title></rect>
        <text x={x0 + englishSec * sc - 12} y={58} textAnchor="end" fontSize="13" fontWeight="600" fill="var(--on-mark)">{englishSec.toFixed(0)} s</text>
        <rect x={x0} y={96} width={teleSec * sc} height={34} rx={9} fill="var(--s-telepathy)"><title>{`Telepathy: ${teleSec.toFixed(1)} s`}</title></rect>
        <text x={x0 + teleSec * sc - 12} y={118} textAnchor="end" fontSize="13" fontWeight="600" fill="var(--on-mark)">{teleSec.toFixed(0)} s</text>
        <line x1={x0 + teleSec * sc} y1={146} x2={x1} y2={146} stroke="var(--ok)" strokeWidth="2" strokeDasharray="5 4" />
        <text x={(x0 + teleSec * sc + x1) / 2} y={166} textAnchor="middle" fontSize="13" fontWeight="600" fill="var(--ok-ink)">{(englishSec - teleSec).toFixed(0)} seconds saved per question</text>
        <line x1={x0} y1={180} x2={x1} y2={180} stroke="var(--axis)" />
        {ticks.map((t) => (
          <g key={t}>
            <line x1={x0 + t * sc} y1={180} x2={x0 + t * sc} y2={185} stroke="var(--axis)" />
            <text x={x0 + t * sc} y={198} textAnchor="middle" fontSize="11" fill="var(--muted)">{t}s</text>
          </g>
        ))}
      </svg>
    </Scroll>
  );
}

export interface DumbRow {
  label: string; note: string; a: number; b: number; max: number; min?: number; fmt: (v: number) => string;
  rangeA?: [number, number]; rangeB?: [number, number];
}

/** Two dots per measurement joined by a line: how far apart the two teams are. */
export function Dumbbell({ rows }: { rows: DumbRow[] }) {
  const x0 = 190, x1 = 650, H = 92;
  return (
    <Scroll><svg viewBox={`0 0 680 ${rows.length * H + 8}`} width="100%" role="img" aria-label="English team versus Telepathy on time, words written and accuracy">
      {rows.map((r, i) => {
        const lo = r.min ?? 0, at = (v: number) => x0 + ((v - lo) / (r.max - lo)) * (x1 - x0);
        const y = i * H + 44, xa = at(r.a), xb = at(r.b);
        const whisk = (rg: [number, number] | undefined, color: string) => rg && (
          <g stroke={color} strokeWidth="2" opacity="0.55">
            <line x1={at(rg[0])} x2={at(rg[1])} y1={y} y2={y} />
            <line x1={at(rg[0])} x2={at(rg[0])} y1={y - 7} y2={y + 7} />
            <line x1={at(rg[1])} x2={at(rg[1])} y1={y - 7} y2={y + 7} />
          </g>
        );
        return (
          <g key={r.label}>
            <text x="0" y={y - 2} fontSize="14" fontWeight="600" fill="var(--ink)">{r.label}</text>
            <text x="0" y={y + 16} fontSize="12" fill="var(--muted)">{r.note}</text>
            <line x1={x0} x2={x1} y1={y} y2={y} stroke="var(--grid)" strokeWidth="2" />
            {whisk(r.rangeA, "var(--s-english)")}{whisk(r.rangeB, "var(--s-telepathy)")}
            <line x1={xa} x2={xb} y1={y} y2={y} stroke="var(--axis)" strokeWidth="5" strokeLinecap="round" />
            <circle cx={xa} cy={y} r="10" fill="var(--s-english)" stroke="var(--surface)" strokeWidth="3"><title>{`English team: ${r.fmt(r.a)}`}</title></circle>
            <circle cx={xb} cy={y} r="10" fill="var(--s-telepathy)" stroke="var(--surface)" strokeWidth="3"><title>{`Telepathy: ${r.fmt(r.b)}`}</title></circle>
            <text x={xa} y={y - 20} textAnchor="middle" fontSize="13" fontWeight="600" fill="var(--ink)">{r.fmt(r.a)}</text>
            <text x={xb} y={y + 32} textAnchor="middle" fontSize="13" fontWeight="600" fill="var(--ink)">{r.fmt(r.b)}</text>
          </g>
        );
      })}
    </svg></Scroll>
  );
}
