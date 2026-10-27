import { describe, expect, it } from "vitest";
import { answerNumber, emptyLane, raceVerdict, reduce } from "./lane";
import type { Ev } from "./types";

const play = (evs: Ev[]) => evs.reduce(reduce, emptyLane());

describe("reduce", () => {
  it("streams a latent run: steps, subtitle, honesty, final", () => {
    const lane = play([
      { type: "run_started", mode: "auto", roles: ["planner", "solver"], question: "q", recorded: true },
      { type: "agent_started", role: "planner" },
      { type: "latent_step", role: "planner", i: 0 },
      { type: "latent_step", role: "planner", i: 1 },
      { type: "subtitle", handoff: 0, role: "planner", text: "Plan: multiply" },
      { type: "handoff", from: "planner", to: "solver", handoff: 0, mode_used: "latent" },
      { type: "honesty", handoff: 0, faithful: true, js: 0.02 },
      { type: "token", role: "solver", text: "4" },
      { type: "final", answer: "\\boxed{42}", metrics: { seconds: 3, tokens_written: 1, latent_steps: 2 } },
      { type: "run_finished" },
    ]);
    expect(lane.status).toBe("done");
    expect(lane.recorded).toBe(true);
    expect(lane.steps.planner).toBe(2);
    expect(lane.handoffs[0]).toMatchObject({ from: "planner", subtitle: "Plan: multiply", faithful: true, js: 0.02, mode: "latent" });
    expect(lane.tokens).toBe(1);
  });

  it("a fallback marks the handoff as text and restarts the agent", () => {
    const lane = play([
      { type: "run_started", roles: ["a", "b"] },
      { type: "agent_started", role: "a" },
      { type: "latent_step", role: "a", i: 0 },
      { type: "handoff", from: "a", to: "b", handoff: 0, mode_used: "latent" },
      { type: "honesty", handoff: 0, faithful: false, js: 0.9 },
      { type: "fallback", handoff: 0, reason: "unfaithful subtitle" },
      { type: "agent_started", role: "a" },
      { type: "token", role: "a", text: "hello", bulk: true },
      { type: "handoff", from: "a", to: "b", handoff: 0, mode_used: "text" },
    ]);
    expect(lane.handoffs).toHaveLength(1);
    expect(lane.handoffs[0]).toMatchObject({ mode: "text", faithful: false, fallback: "unfaithful subtitle" });
    expect(lane.steps.a).toBe(0);
    expect(lane.tokens).toBe(2); // 5 chars of bulk text -> ceil(5/4)
  });
});

describe("safety events", () => {
  it("tracks outside content, a forced-text tainted handoff and its scan", () => {
    const lane = play([
      { type: "run_started", roles: ["researcher", "analyst", "critic", "writer"] },
      { type: "outside_content", role: "researcher", sources: ["tavily:https://a.example/x"], count: 1 },
      { type: "scan", handoff: 0, role: "researcher", flagged: true, reasons: ["ignore-previous-instructions"], action: "warn" },
      { type: "handoff", handoff: 0, from: "researcher", to: "analyst", mode_used: "text", reason: "tainted", taint: "direct", cache_len: 0 },
      { type: "handoff", handoff: 1, from: "analyst", to: "critic", mode_used: "latent", taint: "inherited", share: "full", cache_len: 40 },
    ]);
    expect(lane.tainted).toBe(true);
    expect(lane.outside).toMatchObject({ role: "researcher", count: 1 });
    expect(lane.handoffs[0]).toMatchObject({ mode: "text", reason: "tainted", taint: "direct", cacheLen: 0 });
    expect(lane.handoffs[0].scan).toEqual({ flagged: true, reasons: ["ignore-previous-instructions"], action: "warn" });
    expect(lane.handoffs[1]).toMatchObject({ mode: "latent", taint: "inherited" });
  });
  it("a fresh run clears the taint", () => {
    const lane = play([{ type: "run_started" }, { type: "outside_content", role: "r", sources: [], count: 0 }, { type: "run_started" }]);
    expect(lane.tainted).toBe(false);
  });
});

describe("answers and verdict", () => {
  it("extracts numbers", () => {
    expect(answerNumber("so \\boxed{1,260} dollars")).toBe("1260");
    expect(answerNumber("it is 7 then 9")).toBe("9");
    expect(answerNumber(undefined)).toBeNull();
  });
  it("computes the race verdict only when both lanes are done", () => {
    const mk = (answer: string, seconds: number, tokens: number) => ({
      ...emptyLane(), status: "done" as const, answer, metrics: { seconds, tokens_written: tokens },
    });
    expect(raceVerdict(mk("42", 70, 1300), emptyLane())).toBeNull();
    const v = raceVerdict(mk("\\boxed{42}", 70, 1300), mk("\\boxed{42}", 17.5, 300))!;
    expect(v.speedup).toBeCloseTo(4, 5);
    expect(v.fewerTokens).toBeCloseTo(1 - 300 / 1300, 5);
    expect(v.sameAnswer).toBe(true);
    expect(raceVerdict(mk("41", 70, 1300), mk("42", 17, 300))!.sameAnswer).toBe(false);
  });
});
