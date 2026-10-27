import type { Ev, Handoff, Lane } from "./types";

export const DEFAULT_ROLES = ["planner", "critic", "refiner", "solver"];

export const emptyLane = (): Lane => ({
  status: "idle", recorded: false, synthetic: false, roles: DEFAULT_ROLES, texts: {}, steps: {},
  handoffs: [], tokens: 0, latentSteps: 0, t: 0, tainted: false,
});

const upsert = (hs: Handoff[], idx: number, patch: Partial<Handoff>): Handoff[] => {
  const i = hs.findIndex((h) => h.idx === idx);
  if (i < 0) {
    const fresh: Handoff = { idx, from: "", to: "", mode: "latent", ...patch };
    return [...hs, fresh].sort((a, b) => a.idx - b.idx);
  }
  const out = hs.slice();
  out[i] = { ...hs[i], ...patch };
  return out;
};

/** Pure reducer: one engine event in, the next lane state out. */
export function reduce(lane: Lane, ev: Ev): Lane {
  const next: Lane = { ...lane, t: ev.t ?? lane.t, recorded: ev.recorded ?? lane.recorded };
  switch (ev.type) {
    case "run_started":
      return { ...emptyLane(), status: "running", recorded: !!ev.recorded, synthetic: !!ev.synthetic,
        mode: ev.mode, roles: ev.roles ?? DEFAULT_ROLES, question: ev.question, model: ev.model, provider: ev.provider, t: ev.t ?? 0 };
    case "agent_started":
      // a re-run after a fallback restarts this agent's text and steps
      return { ...next, active: ev.role, texts: { ...lane.texts, [ev.role]: "" }, steps: { ...lane.steps, [ev.role]: 0 } };
    case "token": {
      const add = ev.bulk ? Math.ceil(String(ev.text).length / 4) : 1;
      return { ...next, active: ev.role, tokens: lane.tokens + add,
        texts: { ...lane.texts, [ev.role]: (lane.texts[ev.role] ?? "") + ev.text } };
    }
    case "latent_step":
      return { ...next, active: ev.role, latentSteps: lane.latentSteps + 1,
        steps: { ...lane.steps, [ev.role]: (lane.steps[ev.role] ?? 0) + 1 } };
    case "handoff":
      return { ...next, handoffs: upsert(lane.handoffs, ev.handoff, {
        from: ev.from, to: ev.to, mode: ev.mode_used === "text" ? "text" : "latent",
        reason: ev.reason, taint: ev.taint, share: ev.share, cacheLen: ev.cache_len }) };
    case "outside_content":
      return { ...next, tainted: true, outside: { role: ev.role, sources: ev.sources ?? [], count: ev.count ?? 0 } };
    case "scan":
      return { ...next, handoffs: upsert(lane.handoffs, ev.handoff, { scan: { flagged: !!ev.flagged, reasons: ev.reasons ?? [], action: ev.action ?? "warn" } }) };
    case "subtitle":
      return { ...next, handoffs: upsert(lane.handoffs, ev.handoff, { subtitle: ev.text }) };
    case "honesty":
      return { ...next, handoffs: upsert(lane.handoffs, ev.handoff, { faithful: ev.faithful, js: ev.js }) };
    case "fallback":
      return { ...next, handoffs: upsert(lane.handoffs, ev.handoff, { mode: "text", fallback: ev.reason, reason: "unfaithful" }) };
    case "final":
      return { ...next, answer: ev.answer, metrics: ev.metrics,
        tokens: ev.metrics?.tokens_written ?? lane.tokens, latentSteps: ev.metrics?.latent_steps ?? lane.latentSteps };
    case "run_finished":
      return { ...next, status: "done", active: undefined };
    default:
      return next;
  }
}

/** Last number in an answer (prefers \boxed{...}), for "both answered 42". */
export function answerNumber(text?: string): string | null {
  if (!text) return null;
  const boxed = [...text.matchAll(/\\boxed\{([^}]*)\}/g)].map((m) => m[1]);
  const src = boxed.length ? boxed[boxed.length - 1] : text;
  const nums = src.match(/[-+]?\d[\d,]*(?:\.\d+)?/g);
  return nums ? nums[nums.length - 1].replace(/,/g, "") : null;
}

export interface Verdict {
  speedup: number | null;
  fewerTokens: number | null;
  sameAnswer: boolean | null;
  answer: string | null;
  otherAnswer: string | null;
}

export function raceVerdict(english: Lane, telepathy: Lane): Verdict | null {
  if (english.status !== "done" || telepathy.status !== "done") return null;
  const es = english.metrics?.seconds, ts = telepathy.metrics?.seconds;
  const et = english.metrics?.tokens_written, tt = telepathy.metrics?.tokens_written;
  const a = answerNumber(english.answer), b = answerNumber(telepathy.answer);
  return {
    speedup: es && ts ? es / ts : null,
    fewerTokens: et && tt !== undefined ? 1 - tt / et : null,
    sameAnswer: a !== null && b !== null ? Number(a) === Number(b) : null,
    answer: b, otherAnswer: a,
  };
}
