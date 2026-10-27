"""The make-or-break gate: is latent at least 1.5x faster than text with accuracy within 5 points?

    python -m bench.gate bench/results/gate
"""
from __future__ import annotations

import sys
from pathlib import Path

from .metrics import compare, read, summarize

MIN_SPEEDUP, MAX_ACC_DROP = 1.5, 0.05


def verdict(text: dict, latent: dict) -> str:
    if not text.get("n") or not latent.get("n"):
        return "NO DATA"
    speed = text["sec_avg"] / latent["sec_avg"]
    drop = text["accuracy"] - latent["accuracy"]
    return "PASS" if speed >= MIN_SPEEDUP and drop <= MAX_ACC_DROP else "NOT YET"


def main():
    d = Path(sys.argv[1] if len(sys.argv) > 1 else "bench/results/gate")
    text = summarize(read(d / "gsm8k_all_text.jsonl"))
    print(f"text   : {text}")
    best = None
    for f in sorted(d.glob("gsm8k_all_latent_s*.jsonl")):
        s = summarize(read(f))
        print(f"{f.stem}: {s}")
        print(f"  latent vs text: {compare(text, s)} -> {verdict(text, s)}")
        if verdict(text, s) == "PASS":
            best = f.stem
    print("\nGATE VERDICT:", "PASS (" + best + ")" if best else "NOT YET (try other latent steps) or NO DATA")


if __name__ == "__main__":
    main()
