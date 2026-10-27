import type { Benchmarks, Ev, RunInfo } from "./types";
import fallback from "./data/benchmarks.json";

const BASE = (import.meta.env.VITE_API as string | undefined) ?? "/api";

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(BASE + path, { headers: { "Content-Type": "application/json" }, ...init });
  if (!r.ok) {
    let detail: any = null;
    try { detail = (await r.json()).detail; } catch { /* not json */ }
    throw Object.assign(new Error(typeof detail === "string" ? detail : `HTTP ${r.status}`), { status: r.status, detail });
  }
  return r.json();
}

export const postRace = (question: string, topology = "sequential", latent_steps = 10) =>
  json<{ text: RunInfo; latent: RunInfo }>("/race", { method: "POST", body: JSON.stringify({ question, latent_steps, topology }) });

export const postLive = (item: string) =>
  json<{ run_id: string }>("/live", { method: "POST", body: JSON.stringify({ item }) });

export const getRecordings = () =>
  json<{ file: string; question: string; mode: string; topology: string; answer?: string; metrics?: any }[]>("/recordings");

export async function getBenchmarks(): Promise<{ data: Benchmarks; live: boolean }> {
  try {
    const data = await json<Benchmarks>("/benchmarks");
    if (Object.keys(data.modes).length) return { data, live: true };
  } catch { /* API not running: use the bundled copy of the real gate numbers */ }
  return { data: fallback as unknown as Benchmarks, live: false };
}

/** Subscribe to a run's SSE stream. Returns a function that closes it. */
export function streamRun(runId: string, onEvent: (e: Ev) => void, onEnd: (err?: string) => void) {
  const es = new EventSource(`${BASE}/runs/${runId}/events`);
  es.onmessage = (m) => onEvent(JSON.parse(m.data));
  es.addEventListener("end", (m) => {
    es.close();
    const err = JSON.parse((m as MessageEvent).data)?.error;
    onEnd(err ?? undefined);
  });
  es.onerror = () => { es.close(); onEnd("connection lost"); };
  return () => es.close();
}

export const getHealth = () => json<{ ok: boolean; tf_live: boolean }>("/health");
