import { useEffect, useState } from "react";
import { AgentTalk } from "./components/AgentTalk";
import { Results } from "./components/Results";
import { Problem } from "./components/Problem";
import { Hero } from "./components/Hero";
import { Gallery } from "./components/Gallery";
import { SectionHead } from "./components/SectionHead";
import { useBench } from "./useBench";

const LINKS = [["see", "How it works"], ["race", "Try it"], ["numbers", "Results"]] as const;

function useSpy() {
  const [active, setActive] = useState("");
  useEffect(() => {
    const obs = new IntersectionObserver((es) => es.forEach((e) => e.isIntersecting && setActive(e.target.id)), { rootMargin: "-40% 0px -55% 0px" });
    LINKS.forEach(([id]) => { const el = document.getElementById(id); if (el) obs.observe(el); });
    return () => obs.disconnect();
  }, []);
  return active;
}

const NOTES: [string, string][] = [
  ["Built on research", "The silent hand-off follows the published LatentMAS method (Apache-2.0). We implemented it for NVIDIA Nemotron and added the measurement and safety around it."],
];

export default function App() {
  const bench = useBench();
  const active = useSpy();

  return (
    <div>
      <header className="sticky top-0 z-20 backdrop-blur" style={{ background: "rgba(8,9,10,0.82)", color: "#f7f8f8" }}>
        <div className="mx-auto flex h-14 max-w-[1080px] items-center gap-8 px-5 sm:px-8">
          <a href="#top" className="flex items-center gap-2.5 text-[15px] font-medium tracking-tight">
            <span className="relative inline-block h-4 w-6" aria-hidden><i className="absolute left-0 top-0 h-4 w-4 rounded-full" style={{ background: "#7c7cff" }} /><i className="absolute left-2 top-0 h-4 w-4 rounded-full opacity-80" style={{ background: "#f5a524" }} /></span>
            Telepathy
          </a>
          <nav className="ml-auto hidden gap-1 sm:flex" aria-label="Sections">
            {LINKS.map(([id, label]) => (
              <a key={id} href={`#${id}`} className="rounded-full px-3 py-1.5 text-sm transition-colors" style={{ color: active === id ? "#f7f8f8" : "#8a8f98", background: active === id ? "rgba(255,255,255,0.06)" : "transparent" }}>{label}</a>
            ))}
          </nav>
        </div>
      </header>

      <div id="top"><Hero /></div>

      <main className="on-page mx-auto max-w-[1080px] space-y-40 px-5 py-32 sm:px-8">
        <section id="problem"><Problem teamSizes={bench?.data.team_sizes} /></section>
        <section id="see">
          <SectionHead label="How it works" title="Watch the hand-off" />
          <div className="rounded-3xl bg-surface"><AgentTalk m={bench?.m ?? null} /></div>
        </section>
        <section id="race"><Gallery /></section>
        <section id="numbers" className="!mb-0"><Results /></section>
        <section className="mx-auto !mt-16 max-w-xl border-t border-hair pt-10 text-center">
          {NOTES.map(([t, d]) => (
            <div key={t}><div className="mb-2 text-[15px] font-medium text-ink">{t}</div><p className="text-sm leading-relaxed text-muted">{d}</p></div>
          ))}
        </section>
      </main>
      <div className="h-16" aria-hidden />
    </div>
  );
}
