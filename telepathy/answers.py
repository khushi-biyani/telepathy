"""Answer extraction and comparison for maths-style tasks."""
from __future__ import annotations

import re


def extract_answer(text: str):
    """Last \\boxed{...} if present, else the last number in the text. None if no number."""
    boxed = re.findall(r"\\boxed\{([^}]*)\}", text)
    src = boxed[-1] if boxed else text
    nums = re.findall(r"[-+]?\d[\d,]*(?:\.\d+)?", src)
    return nums[-1].replace(",", "") if nums else None


def same_number(a, b) -> bool:
    try:
        return abs(float(a) - float(b)) < 1e-6
    except (TypeError, ValueError):
        return False


def extract_choice(text: str):
    """Multiple choice: last \\boxed{X} letter, else the last standalone A-E letter. None if absent."""
    boxed = re.findall(r"\\boxed\{\s*\(?([A-Ea-e])\)?\s*\}", text)
    if boxed:
        return boxed[-1].upper()
    letters = re.findall(r"\b([A-E])\b", text)
    return letters[-1] if letters else None
