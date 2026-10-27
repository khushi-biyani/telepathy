import { describe, expect, it } from "vitest";
import { measuredFrom, perDay } from "./savings";

const m = { agents: 4, textTokens: 1266.567, textSec: 71.41, teleTokens: 282.98, teleSec: 16.614, split: "x" };

describe("savings", () => {
  it("multiplies the measured per-question numbers by the task count and nothing else", () => {
    const d = perDay(m, 1000);
    expect(d.hoursSaved).toBeCloseTo(((71.41 - 16.614) * 1000) / 3600, 6);
    expect(d.wordsSaved).toBeCloseTo((1266.567 - 282.98) * 1000, 3);
    expect(perDay(m, 0).hoursSaved).toBe(0);
  });
  it("reads the measured numbers from benchmark data, preferring the report split", () => {
    const row = (s: number, t: number) => ({ n: 50, accuracy: 0.7, sec_avg: s, tokens_written: t });
    const got = measuredFrom({ modes: {
      "gate/gsm8k_all_text": row(1, 1), "gate/gsm8k_all_latent_s10": row(1, 1),
      "test/gsm8k_test_text": row(71, 1266), "test/gsm8k_test_latent_s10": row(16, 283) }, honesty: {} } as any)!;
    expect(got.textSec).toBe(71);
    expect(got.split).toContain("report");
    expect(measuredFrom({ modes: {}, honesty: {} })).toBeNull();
  });
});
