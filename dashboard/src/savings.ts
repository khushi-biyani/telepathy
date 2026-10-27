import type { Benchmarks } from "./types";

/** Numbers measured on the 4-agent GSM8K team (per question). */
export interface Measured {
  agents: number;      // team size the numbers were measured with
  textTokens: number;  // tokens written by the English team
  textSec: number;
  teleTokens: number;  // tokens written by Telepathy (only the last agent writes)
  teleSec: number;
  split: string;
}

export function measuredFrom(data: Benchmarks): Measured | null {
  const groups: Record<string, Record<string, any>> = {};
  for (const [key, v] of Object.entries(data.modes)) {
    const [folder, stem] = key.split("/");
    (groups[folder] ??= {})[stem.replace(/^[a-z0-9]+_(all|dev|test)_/, "")] = v;
  }
  const folder = groups.test?.text && groups.test?.latent_s10 ? "test" : Object.keys(groups).find((g) => groups[g].text && groups[g].latent_s10);
  if (!folder) return null;
  const t = groups[folder].text, l = groups[folder].latent_s10;
  return { agents: 4, textTokens: t.tokens_written, textSec: t.sec_avg, teleTokens: l.tokens_written,
           teleSec: l.sec_avg, split: folder === "test" ? "150-question report split" : "50-question dev split" };
}

export interface Daily { hoursSaved: number; wordsSaved: number }

/** Per-day totals: the measured per-question numbers multiplied by the number of tasks. Nothing else is assumed. */
export function perDay(m: Measured, tasks: number): Daily {
  return { hoursSaved: ((m.textSec - m.teleSec) * tasks) / 3600, wordsSaved: (m.textTokens - m.teleTokens) * tasks };
}
