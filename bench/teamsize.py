"""How the cost of a written-notes team grows with team size, measured on Nebius Token Factory.

    python -m bench.teamsize                 # reads bench/results/test/gsm8k_tokenfactory_text*.jsonl

Compares the same questions at every team size (the first 50 questions common to all files), so the
sizes are not compared on different questions.
"""
from __future__ import annotations

import statistics as st
import sys
from pathlib import Path

from .metrics import read


def summary(rows: list[dict]) -> dict:
    n = len(rows)
    return {"questions": n, "accuracy": sum(r["ok"] for r in rows) / n,
            "sec_avg": st.mean(r["seconds"] for r in rows),
            "tokens_in": st.mean(r["tokens_in"] for r in rows),
            "tokens_out": st.mean(r["tokens_out"] for r in rows),
            "usd": st.mean(r["cost_usd"] for r in rows)}


def by_size(folder: Path) -> dict[int, dict]:
    files = sorted(folder.glob("gsm8k_tokenfactory_text*.jsonl"))
    sets: dict[int, dict[str, dict]] = {}
    for f in files:
        for r in read(f):
            if r.get("cached", 0) > 0 or r["tokens_in"] == 0:  # served from the saved-answer cache: not a real measurement
                continue
            sets.setdefault(r.get("agents", 4), {})[r["id"]] = r
    if not sets:
        return {}
    common = set.intersection(*(set(v) for v in sets.values()))
    return {n: summary([sets[n][i] for i in sorted(common)]) for n in sorted(sets)}


def main():
    folder = Path(sys.argv[1] if len(sys.argv) > 1 else "bench/results/test")
    res = by_size(folder)
    if not res:
        print("no Token Factory results found")
        return
    print(f"{'agents':>6} {'questions':>9} {'right':>6} {'sec':>6} {'read':>7} {'written':>8} {'$/question':>11}")
    for n, s in res.items():
        print(f"{n:>6} {s['questions']:>9} {s['accuracy']:>6.0%} {s['sec_avg']:>6.1f} {s['tokens_in']:>7.0f} {s['tokens_out']:>8.0f} {s['usd']:>11.4f}")


if __name__ == "__main__":
    main()
