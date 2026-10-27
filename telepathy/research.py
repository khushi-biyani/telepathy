"""Research demo: Tavily search -> Researcher reads it and hands off in TEXT (it read outside content),
then Analyst, Critic and Writer think silently together and the Writer answers with citations.

    python -m telepathy.research "What changed in the EU AI Act in 2026?" [--mode latent|text|auto]
    python -m telepathy.research "How much change for 7 pens?" --fixture server/fixtures/fake_injection.json

--fixture uses saved fake search results (no network, no Tavily credits). The bundled fake page contains a
planted instruction so the safety design can be shown on harmless, clearly fake content.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .engine import TelepathyTeam
from .tools import tavily


def research(question: str, mode: str = "auto", latent_steps: int = 10, config=None, results=None, **team_kw):
    results = results if results is not None else tavily.search(question)
    team = TelepathyTeam("research", mode, latent_steps, config=config, **team_kw)
    return team.run(question, context=tavily.as_content(results)), results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("question")
    ap.add_argument("--mode", default="auto")
    ap.add_argument("--steps", type=int, default=10)
    ap.add_argument("--fixture", help="JSON file of fake search results instead of calling Tavily")
    ap.add_argument("--demo", action="store_true", help="turn on the instruction scan")
    a = ap.parse_args()
    results = json.loads(Path(a.fixture).read_text()) if a.fixture else None
    r, sources = research(a.question, a.mode, a.steps, results=results, demo=a.demo)
    print(r.answer, "\n\nSources:")
    for i, s in enumerate(sources, 1):
        print(f"[{i}] {s['url']}")
    print(r.metrics)


if __name__ == "__main__":
    main()
