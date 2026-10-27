import { useEffect, useReducer, useState } from "react";
import { streamRun } from "./api";
import { emptyLane, reduce } from "./lane";
import type { Ev, Lane } from "./types";

type Action = { ev: Ev } | { reset: true } | { error: string };
const step = (lane: Lane, a: Action): Lane =>
  "reset" in a ? emptyLane() : "error" in a ? { ...lane, status: "error", error: a.error } : reduce(lane, a.ev);

/** Follows one run's event stream and folds it into lane state. */
export function useLane(runId: string | null) {
  const [lane, dispatch] = useReducer(step, undefined, emptyLane);
  useEffect(() => {
    dispatch({ reset: true });
    if (!runId) return;
    return streamRun(runId, (ev) => dispatch({ ev }), (err) => err && dispatch({ error: err }));
  }, [runId]);
  return lane;
}

/** Seconds on screen: ticks while running, then snaps to the run's own measured time. */
export function useElapsed(lane: Lane) {
  const [now, setNow] = useState(0);
  useEffect(() => {
    if (lane.status !== "running") return;
    const t0 = performance.now() - lane.t * 1000;
    let raf = 0;
    const tick = () => { setNow((performance.now() - t0) / 1000); raf = requestAnimationFrame(tick); };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [lane.status]); // eslint-disable-line react-hooks/exhaustive-deps
  if (lane.status === "done") return lane.metrics?.seconds ?? lane.t;
  return lane.status === "running" ? Math.max(now, lane.t) : 0;
}
