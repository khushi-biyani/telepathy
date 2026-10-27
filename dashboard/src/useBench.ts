import { useEffect, useState } from "react";
import { getBenchmarks } from "./api";
import { measuredFrom, type Measured } from "./savings";
import type { Benchmarks } from "./types";

export interface Bench { data: Benchmarks; m: Measured | null; live: boolean }

export function useBench(): Bench | null {
  const [b, setB] = useState<Bench | null>(null);
  useEffect(() => { getBenchmarks().then((r) => setB({ data: r.data, m: measuredFrom(r.data), live: r.live })); }, []);
  return b;
}
