export type Ev = { type: string; t?: number; recorded?: boolean; [k: string]: any };

export interface Metrics {
  seconds?: number;
  tokens_written?: number;
  latent_steps?: number;
  fallbacks?: number;
  cost_usd?: number;
  [k: string]: any;
}

export interface Handoff {
  idx: number;
  from: string;
  to: string;
  mode: "latent" | "text";
  subtitle?: string;
  faithful?: boolean;
  js?: number;
  fallback?: string;
  reason?: string;            // why the handoff is in English: tainted | high_stakes | unfaithful
  taint?: string;             // clean | direct | inherited
  share?: string;             // full | thoughts_only
  cacheLen?: number;
  scan?: { flagged: boolean; reasons: string[]; action: string };
}

export interface Lane {
  status: "idle" | "running" | "done" | "error";
  mode?: string;
  recorded: boolean;
  synthetic: boolean;
  roles: string[];
  active?: string;
  texts: Record<string, string>;
  steps: Record<string, number>;
  handoffs: Handoff[];
  tokens: number;
  latentSteps: number;
  t: number;
  answer?: string;
  metrics?: Metrics;
  question?: string;
  model?: string;
  error?: string;
  provider?: string;   // "nebius_token_factory" when this lane ran live on Nebius
  outside?: { role: string; sources: string[]; count: number };  // the agent that read outside content
  tainted: boolean;
}

export interface ModeStats {
  n: number;
  accuracy?: number;
  sec_avg?: number;
  sec_p90?: number;
  tokens_written?: number;
  latent_steps?: number;
}

export interface HonestyStats {
  questions: number;
  handoffs: number;
  faithful_rate: number | null;
  shuffled_catch_rate: number | null;
  shuffled_n: number;
  corrupted_catch_rate: number | null;
  corrupted_n: number;
  mean_js_faithful: number | null;
  mean_js_unfaithful: number | null;
}

export interface TeamSize {
  questions: number; accuracy: number; sec_avg: number; tokens_in: number; tokens_out: number; usd: number;
}

export interface Benchmarks {
  team_sizes?: Record<string, TeamSize>;
  modes: Record<string, ModeStats>;
  honesty: Record<string, HonestyStats>;
  notes?: string | null;
}

export interface RunInfo {
  run_id: string;
  recorded: boolean;
  source?: string;
  live_denied?: string;  // why a live Nebius question was not allowed (we show a recording instead)
  matched_question?: string;
  similarity?: number;
  exact?: boolean;
}
