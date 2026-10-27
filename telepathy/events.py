"""Event recorder and replayer. The engine emits plain dicts through `on_event`; a Recorder stamps
each with the seconds since the run began and can save them as JSONL. A replay serves a recording
with its original timing, so the dashboard cannot tell live from replayed (it is shown a
'Recorded run' badge by the server)."""
from __future__ import annotations

import json
import re
import time
from pathlib import Path


class Recorder:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else None
        self.events: list[dict] = []
        self._t0 = None
        self._sinks = []
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text("")

    def add_sink(self, fn):
        """Also pass every stamped event to `fn` (the server uses this to stream live)."""
        self._sinks.append(fn)

    def __call__(self, event: dict):
        try:
            json.dumps(event)
        except TypeError as err:  # a tensor or cache in an event: caches never leave the process
            raise TypeError("events must be plain JSON; caches and tensors never leave the process") from err
        now = time.perf_counter()
        self._t0 = now if self._t0 is None else self._t0
        ev = {**event, "t": round(now - self._t0, 4)}
        self.events.append(ev)
        if self.path:
            with self.path.open("a") as f:
                f.write(json.dumps(ev) + "\n")
        for fn in self._sinks:
            fn(ev)


def load(path: str | Path) -> list[dict]:
    return [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]


def replay(events: list[dict], speed: float = 1.0, sleep=time.sleep):
    """Yield the events with their original gaps (divided by `speed`)."""
    prev = 0.0
    for ev in events:
        gap = max(0.0, ev.get("t", prev) - prev) / max(speed, 1e-9)
        if gap:
            sleep(gap)
        prev = ev.get("t", prev)
        yield ev


def _words(text: str) -> set:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def similarity(a: str, b: str) -> float:
    """Jaccard overlap of the words in two questions, 0..1."""
    wa, wb = _words(a), _words(b)
    return len(wa & wb) / len(wa | wb) if wa | wb else 0.0


def describe(path: str | Path) -> dict | None:
    """First `run_started` event of a recording, plus its final metrics."""
    evs = load(path)
    start = next((e for e in evs if e["type"] == "run_started"), None)
    if start is None:
        return None
    fin = next((e for e in evs if e["type"] == "final"), {})
    return {"file": Path(path).name, "question": start["question"], "mode": start["mode"],
            "topology": start["topology"], "answer": fin.get("answer"), "metrics": fin.get("metrics")}


def nearest(directory: str | Path, question: str, mode: str | None = None, topology: str | None = None):
    """(path, score) of the recording closest to `question`, optionally of a given mode/topology."""
    best = (None, -1.0)
    for p in sorted(Path(directory).glob("*.jsonl")):
        d = describe(p)
        if not d or (mode and d["mode"] != mode) or (topology and d["topology"] != topology):
            continue
        score = similarity(question, d["question"])
        if score > best[1]:
            best = (p, score)
    return best
