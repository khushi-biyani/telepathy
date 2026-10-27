import { useEffect, useState } from "react";
import { Accordion } from "./Accordion";
import GI from "../data/gallery_index.json";

// Where each run's rows live. Kaggle runs use a small copy for the page (slim/); Nebius runs are read as they are.
const DOWNLOADS = [
  ["Raw rows, every question", ["runs/maths_single.jsonl", "runs/maths_text.jsonl", "runs/maths_latent.jsonl", "runs/coding_single.jsonl", "runs/coding_text.jsonl", "runs/coding_latent.jsonl", "runs/medical_single.jsonl", "runs/medical_text.jsonl", "runs/medical_latent.jsonl"]],
  ["Team size on Nebius", ["tokenfactory_team2_50q.jsonl", "tokenfactory_4agents_150q.jsonl", "tokenfactory_team6_50q.jsonl", "tokenfactory_team8_50q.jsonl"]],
  ["Recordings and other tests", ["animation_local.json", "animation_local_rerun.json", "animation_usual_flow.json", "mismatch_real.jsonl", "mismatch_no_thinking.jsonl", "mismatch_other_question.jsonl"]],
] as const;

type MRow = { id: string; ok: boolean; seconds: number; tokens_written: number };
const ARMS = [
  { key: "real", file: "mismatch_real.jsonl", name: "Real", what: "The normal Telepathy run: three agents think silently, the Solver answers." },
  { key: "no_thinking", file: "mismatch_no_thinking.jsonl", name: "No thinking", what: "The same team, but the silent agents take zero thinking steps." },
  { key: "other_question", file: "mismatch_other_question.jsonl", name: "Wrong notebook", what: "The silent agents think about a different question; the Solver still gets the real one." },
] as const;

// exact two-sided sign test on the questions where two arms disagree
function signP(x: number, y: number) {
  const n = x + y, k = Math.min(x, y);
  if (n === 0) return 1;
  let c = 1, tot = 0;  // c = C(n, j)
  for (let j = 0; j <= k; j++) { tot += c; c = (c * (n - j)) / (j + 1); }
  return Math.min(1, (2 * tot) / 2 ** n);
}

/** Does the silent thinking carry information? Three arms on the same 50 questions, recomputed from the raw files. */
function MismatchProof() {
  const [d, setD] = useState<Record<string, MRow[]>>({});
  useEffect(() => {
    Promise.all(ARMS.map(async (a) => {
      const t = await (await fetch(`/evidence/${a.file}`)).text();
      return [a.key, t.trim().split("\n").map((l) => JSON.parse(l) as MRow)] as const;
    })).then((e) => setD(Object.fromEntries(e))).catch(() => setD({}));
  }, []);
  const ready = ARMS.every((a) => d[a.key]?.length);
  const by = (k: string) => Object.fromEntries((d[k] ?? []).map((r) => [r.id, r]));
  const pair = (a: string, b: string) => {
    const A = by(a), B = by(b), ids = Object.keys(A).filter((i) => B[i]);
    const x = ids.filter((i) => A[i].ok && !B[i].ok).length, y = ids.filter((i) => B[i].ok && !A[i].ok).length;
    return { x, y, p: signP(x, y) };
  };
  return (
    <div>
      <p className="mb-4 text-sm text-ink2">Telepathy answers about as well as the usual team. Is that because the agents really pass useful thoughts? We tested it three ways on the same 50 questions.</p>
      <div>
        <div>
          {!ready ? <p className="text-sm text-muted">Loading the raw files…</p> : (
            <>
              <div className="grid gap-3 sm:grid-cols-3">
                {ARMS.map((a) => {
                  const r = d[a.key], ok = r.filter((x) => x.ok).length, cap = r.filter((x) => !x.ok && x.tokens_written >= 384).length;
                  return (
                    <div key={a.key} className="rounded-2xl bg-well p-4">
                      <div className="text-sm font-medium text-ink">{a.name}</div>
                      <div className="mt-1 text-3xl font-semibold tabular-nums">{ok}<span className="text-base text-muted"> / {r.length} right</span></div>
                      <div className="mt-2 h-1.5 rounded-full bg-surface"><div className="h-1.5 rounded-full" style={{ width: `${(ok / r.length) * 100}%`, background: "var(--s-telepathy)" }} /></div>
                      <p className="mt-2 text-xs text-muted">{a.what}</p>
                      <p className="mt-2 text-xs text-ink2">{r.length - ok} wrong, and {cap} of those were cut off at the 384-word-piece limit before finishing.</p>
                    </div>
                  );
                })}
              </div>
              <div className="mt-4 overflow-x-auto rounded-xl border border-hair">
                <table className="w-full text-left text-xs tabular-nums">
                  <thead className="bg-well text-muted"><tr><th className="px-3 py-2">comparison</th><th>first one only right</th><th>second one only right</th><th>chance this is luck (p)</th></tr></thead>
                  <tbody>
                    {[["real", "no_thinking", "Real vs No thinking"], ["real", "other_question", "Real vs Wrong notebook"], ["no_thinking", "other_question", "No thinking vs Wrong notebook"]].map(([a, b, l]) => {
                      const q = pair(a, b);
                      return <tr key={l} className="border-t border-hair"><td className="px-3 py-1.5">{l}</td><td>{q.x}</td><td>{q.y}</td><td>{q.p.toFixed(2)}</td></tr>;
                    })}
                  </tbody>
                </table>
              </div>
              <div className="mt-4 rounded-2xl bg-well p-4 text-sm text-ink2">
                <div className="mb-1 font-medium text-ink">What we make of it</div>
                <ul className="list-disc space-y-1 pl-4">
                  <li><b className="text-ink">The silent thinking does not measurably improve answers.</b> Taking it away changed the score by 2 questions out of 50, and a difference that small is what luck produces (p about 0.75).</li>
                  <li><b className="text-ink">A wrong notebook did a bit worse, but we can not say it is real.</b> 32 against 35 right is within luck at this size (p about 0.5). It also ran out of space more often, so it may make the model ramble.</li>
                  <li><b className="text-ink">So we do not claim the agents pass thoughts that help.</b> We claim something narrower, which we did measure: about the same accuracy, with far less time and far fewer words, because nobody writes or re-reads long notes.</li>
                  <li><b className="text-ink">Limits:</b> 50 questions is small, and many wrong answers were cut off by the word-piece limit, which hides what the thinking does. A larger test could tell a different story.</li>
                </ul>
              </div>
              <div className="mt-4 flex flex-wrap gap-4 text-xs">
                {[...ARMS.map((a) => a.file), "mismatch_summary.md"].map((f) => <a key={f} className="underline text-ink2" href={`/evidence/${f}`} download>{f}</a>)}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

/** The details behind the results: raw files, every demo recording, a self-test and what did not work. Folded by default. */
export function Details() {
  return (
    <div className="space-y-3">
            <Accordion title="Download the raw files">
        <div className="grid gap-4 text-sm sm:grid-cols-3">
          {DOWNLOADS.map(([title, files]) => (
            <div key={title}><div className="mb-1.5 font-medium text-ink">{title}</div>
              <ul className="space-y-1 text-xs">{files.map((f) => <li key={f}><a className="text-ink2 underline" href={`/evidence/${f}`} download>{f.replace("runs/", "")}</a></li>)}</ul></div>
          ))}
        </div>
        <p className="mt-4 text-xs text-muted">
          Re-run the Kaggle tests: <code>python -m bench.run_bench --task gsm8k --split test --modes single,text,latent --dtype float16 --device cuda</code> (and <code>--task mbppplus</code> or <code>--task medqa</code> with <code>--n 60 --max-new-tokens 1024</code>).
          The usual team on Nebius: <code>python -m telepathy.baseline_tf --n 150 --run --yes</code> (needs your own key).
        </p>
      </Accordion>
      <Accordion title={`All ${GI.stats.n} demo recordings, including the ones not featured`}>
        <p className="mb-3 text-sm text-ink2">The "Try it" section features a few of these. Here is every one: multi-agent got {GI.stats.usual_right} of {GI.stats.n} right, Telepathy {GI.stats.telepathy_right} of {GI.stats.n}.</p>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs tabular-nums">
            <thead className="text-muted"><tr><th className="py-1.5 pr-3">question</th><th className="pr-3">type</th><th className="pr-3">multi-agent</th><th className="pr-3">Telepathy</th><th className="pr-3">faster</th><th>file</th></tr></thead>
            <tbody>{GI.items.map((i) => (
              <tr key={i.id} className="border-t border-hair">
                <td className="py-1.5 pr-3 text-ink2">{i.title}{i.featured ? "" : <span className="ml-1 text-muted">(not featured)</span>}</td><td className="pr-3 text-muted">{i.kind}</td>
                <td className="pr-3" style={{ color: i.usual.correct ? "var(--ok)" : "#e5484d" }}>{i.usual.correct ? "right" : "wrong"}</td>
                <td className="pr-3" style={{ color: i.telepathy.correct ? "var(--ok)" : "#e5484d" }}>{i.telepathy.correct ? "right" : "wrong"}</td>
                <td className="pr-3">{(i.usual.seconds / i.telepathy.seconds).toFixed(1)}×</td>
                <td><a className="underline text-ink2" href={`/gallery/${i.id}.json`} download>json</a></td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      </Accordion>
      <Accordion title="A test we ran on ourselves: does the silent thinking carry information?"><MismatchProof /></Accordion>
      <Accordion title="What did not work">
        <ul className="list-disc space-y-1.5 pl-4 text-sm text-ink2">
          <li>Readable "subtitles" of the silent thinking could not be checked: our honesty check could not tell real ones from fake ones, so we do not claim them.</li>
          <li>On research-style questions (read a page, then calculate) the small model did badly whichever way the agents talked, and our step-by-step fix did not help.</li>
          <li>Our first team-size run reused saved answers and looked free. We found it, fixed it and re-ran; the bad files are kept, not deleted.</li>
          <li>Our first three "research" demos gave the agents fake web pages that were not needed to answer (one hid a planted instruction). The usual team got all three right and Telepathy none. We replaced them with real web-research questions; the old recordings are kept: <a className="underline" href="/evidence/retired/pens.json" download>pens</a>, <a className="underline" href="/evidence/retired/bus.json" download>bus</a>, <a className="underline" href="/evidence/retired/recipe.json" download>recipe</a>.</li>
        </ul>
      </Accordion>
    </div>
  );
}
