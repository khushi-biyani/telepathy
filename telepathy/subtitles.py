"""Thought Subtitles: a short plain-English summary of a silent handoff.
Generated on a COPY of the working memory, so it can never change the real run."""
from __future__ import annotations

from .cache_utils import fork

INSTRUCTION = "In at most 50 words, state what you concluded and what the next teammate should do."
# The plain subtitle said what an agent did, not the facts it used. The rich one asks for the numbers.
INSTRUCTION_RICH = ("In at most 80 words, restate the key numbers and facts you are using from the question, "
                    "what you have concluded so far, and what the next teammate should do.")


def subtitle(lm, past, max_new: int = 70, style: str = "plain") -> str:
    branch = fork(past)
    rich = style == "rich"
    text, _, _ = lm.decode(lm.turn_suffix_ids(INSTRUCTION_RICH if rich else INSTRUCTION), branch,
                           max_new=max(max_new, 110) if rich else max_new)
    return text
