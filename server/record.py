"""Record demo runs for replay mode. Run this where the model runs (a GPU), not on the public server.

    python -m server.record --questions server/demo_questions.json --steps 10 --dtype float16 --device cuda

For each question it records a text-mode run and an auto-mode run (subtitles + honesty check on every
handoff), one after the other so their timings are comparable. A handoff that really fails the check
is recorded as it happened: we never script a failure.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from telepathy import Config, Policy, TelepathyTeam
from telepathy.events import Recorder
from telepathy.tools import tavily


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--questions", default="server/demo_questions.json")
    ap.add_argument("--steps", type=int, default=10)
    ap.add_argument("--topology", default="sequential")
    ap.add_argument("--model", default=Config.model_id)
    ap.add_argument("--device", default="auto")
    ap.add_argument("--dtype", default="auto", choices=["auto", "bfloat16", "float16", "float32"])
    ap.add_argument("--fixture", help="record the research team on saved FAKE search results (safety demo)")
    ap.add_argument("--out", default="server/recordings")
    a = ap.parse_args()

    cfg = Config(model_id=a.model, device=a.device, dtype=a.dtype)
    questions = json.loads(Path(a.questions).read_text())
    fixture = json.loads(Path(a.fixture).read_text()) if a.fixture else None
    topology = "research" if fixture else a.topology
    for q in questions:
        for mode in ("text", "auto"):
            rec = Recorder(Path(a.out) / f"{slug(q)}__{'research-' if fixture else ''}{mode}.jsonl")
            team = TelepathyTeam(topology, mode, a.steps, config=cfg, on_event=rec, demo=bool(fixture),
                                 policy=Policy(honesty_check="off" if fixture else "always"))
            r = team.run(q, context=tavily.as_content(fixture) if fixture else "")
            print(f"{mode:5s} {r.metrics['seconds']:.1f}s  answer={r.answer[-60:]!r}", flush=True)


if __name__ == "__main__":
    main()
