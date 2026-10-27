import { headline, times } from "./Results";

/** What it is, three measured numbers, one next step. */
export function Hero() {
  const h = headline();
  const stats: [string, string][] = [
    [`${h.speedMin}–${times(h.speedMax)}`, "faster than a usual multi-agent team"],
    [`${h.tokMin}–${h.tokMax}%`, "fewer tokens written"],
    ...(h.asGood ? [["Same or better", "accuracy, in maths, coding, medicine and research"] as [string, string]] : []),
  ];
  return (
    <div className="hero-band">
      <div className="mx-auto max-w-[1080px] px-5 pb-24 pt-20 sm:px-8 sm:pt-28">
        <h1 className="max-w-[860px] text-[42px] font-[520] leading-[1.04] tracking-[-0.035em] sm:text-[64px]">
          AI agents that think together, without writing it all out
        </h1>
        <p className="mt-7 max-w-[580px] text-lg leading-relaxed" style={{ color: "#8a8f98" }}>
          Multi-agent systems spend much of their time writing to each other. Telepathy lets agents share their working memory instead, on NVIDIA Nemotron.
        </p>
        <div className="mt-10 flex flex-wrap gap-3">
          <a href="#see" className="btn-primary">See how it works</a>
          <a href="#numbers" className="btn-ghost">See the results</a>
        </div>
        <dl className="mt-20 grid max-w-[860px] gap-10 border-t pt-8 sm:grid-cols-3" style={{ borderColor: "rgba(255,255,255,0.08)" }}>
          {stats.map(([big, small]) => (
            <div key={small}>
              <dt className="text-[28px] font-medium tracking-tight text-white">{big}</dt>
              <dd className="mt-1 text-sm" style={{ color: "#8a8f98" }}>{small}</dd>
            </div>
          ))}
        </dl>
      </div>
    </div>
  );
}
