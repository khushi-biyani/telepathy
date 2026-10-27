"""Ultra as judge and reviewer, through Token Factory. Use on a sub-sample only, to stay in budget."""
from __future__ import annotations

import json
import re

from .llm import LLM

JUDGE_SYSTEM = "You are a strict evaluator. Reply with JSON only."


def parse_json(text: str) -> dict:
    m = re.search(r"\{.*\}", text, flags=re.S)
    try:
        return json.loads(m.group(0)) if m else {}
    except ValueError:
        return {}


def judge_subtitle(llm: LLM, question: str, subtitle: str, final_answer: str, tag: str = "q") -> dict:
    """{'clarity': 1-5, 'consistent': bool} for one subtitle."""
    prompt = (f"A team of AI agents answered a question. One agent left this plain-English summary of "
              f"its silent reasoning:\n\nSUMMARY: {subtitle}\n\nQUESTION: {question}\n"
              f"FINAL TEAM ANSWER: {final_answer}\n\n"
              'Return JSON: {"clarity": <1-5, how clear and readable the summary is>, '
              '"consistent": <true if the summary agrees with the final answer, else false>}')
    raw = llm.chat(f"judge:{tag}", "ultra", [{"role": "system", "content": JUDGE_SYSTEM},
                                             {"role": "user", "content": prompt}],
                   max_tokens=120, temperature=0.0, json_mode=True)
    d = parse_json(raw)
    try:
        clarity = max(1, min(5, int(d.get("clarity"))))
    except (TypeError, ValueError):
        clarity = None
    return {"clarity": clarity, "consistent": d.get("consistent") if isinstance(d.get("consistent"), bool) else None}


def review_research(llm: LLM, answer: str, sources: str, tag: str = "q") -> dict:
    """Optional final reviewer: is the Writer's answer supported by the Tavily sources?"""
    prompt = (f"SOURCES:\n{sources}\n\nANSWER:\n{answer}\n\n"
              'Return JSON: {"supported": <true if every claim is backed by the sources>, '
              '"issues": "<short note, empty if none>"}')
    raw = llm.chat(f"review:{tag}", "ultra", [{"role": "system", "content": JUDGE_SYSTEM},
                                              {"role": "user", "content": prompt}],
                   max_tokens=200, temperature=0.0, json_mode=True)
    return parse_json(raw)
