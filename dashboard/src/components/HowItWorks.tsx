import { SectionHead } from "./SectionHead";
import { Accordion } from "./Accordion";

const safety: [string, string][] = [
  ["Trust comes from the source", "Only the user's question and our own prompts are trusted. Web pages and files are not, and no model output can change that."],
  ["Outside content goes in the open", "An agent that reads outside content must pass its notes on in readable English, and its raw text never enters the shared memory."],
  ["Share thoughts, not everything", "Where roles differ, only the sender's silent steps are handed over."],
  ["Agents cannot act", "They only write text. Our code, not the model, calls the one read-only search."],
  ["Memory stays put", "A team's shared memory stays inside one run on one machine. It is never saved or sent."],
  ["No secrets in prompts", "Keys live in a private file. A prompt containing one is refused."],
];

export function LearnMore() {
  return (
    <div>
      <SectionHead label="Learn more" title="Questions you might have" sub="The short version is above. Open anything you want to know more about." />
      <div className="space-y-3">
        <Accordion title="How it works in 30 seconds">
          <ol className="list-decimal space-y-1 pl-5">
            <li>Normally each agent writes out its thinking and the next one reads all of it. That is slow and costs a lot of words.</li>
            <li>In Telepathy, the first agents think silently and hand their working memory straight to the next one.</li>
            <li>Only the last agent writes. That is where the time and the words are saved.</li>
          </ol>
        </Accordion>
        <Accordion title="Safety rules we follow">
          <p className="mb-3">Silent handoffs raise a fair worry. Here is what we enforce, and it is enforced in code, not by asking the model nicely.</p>
          <ul className="space-y-2">{safety.map(([t, d]) => <li key={t}><b className="font-medium text-ink">{t}.</b> {d}</li>)}</ul>
          <p className="mt-3">We do not claim to stop every leak. A silent channel can carry anything the agents saw, and we only control outside content.</p>
        </Accordion>
        <Accordion title="Something we tried that did not work">
          <p>We wrote a short plain-English summary after each silent step, and tried to check the summary was honest by giving the next agent only the summary and comparing answers. The check could not tell real summaries from fake ones: its score was about 0.5, which is chance. So we treat summaries as explanations written afterwards, not as proof of what the agents thought.</p>
        </Accordion>
        <Accordion title="What it is built with">
          <ul className="list-disc space-y-1 pl-5">
            <li>NVIDIA Nemotron Nano 4B runs the agents, on a free Kaggle GPU for our tests.</li>
            <li>Nebius Token Factory is for the written-notes cost comparison at scale (planned, not run yet).</li>
            <li>The silent-thinking method follows LatentMAS (Apache-2.0). The product around it is ours.</li>
          </ul>
        </Accordion>
      </div>
    </div>
  );
}
