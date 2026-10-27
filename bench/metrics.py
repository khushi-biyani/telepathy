"""Summarise result JSONL files."""
from __future__ import annotations

import json
import statistics
from pathlib import Path


def read(path) -> list[dict]:
    p = Path(path)
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []


def p90(xs):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(0.9 * len(xs)))] if xs else 0.0


def summarize(rows: list[dict]) -> dict:
    if not rows:
        return {"n": 0}
    secs = [r["seconds"] for r in rows]
    return {
        "n": len(rows),
        "accuracy": sum(r["ok"] for r in rows) / len(rows),
        "sec_avg": statistics.mean(secs),
        "sec_p90": p90(secs),
        "tokens_written": statistics.mean(r["tokens_written"] for r in rows),
        "latent_steps": statistics.mean(r["latent_steps"] for r in rows),
    }


def compare(base: dict, other: dict) -> str:
    """e.g. 'latent vs text: 3.2x faster, 80% fewer tokens, accuracy -2 points'"""
    if not base.get("n") or not other.get("n"):
        return "not enough data"
    speed = base["sec_avg"] / other["sec_avg"]
    fewer = 1 - other["tokens_written"] / max(base["tokens_written"], 1e-9)
    dacc = (other["accuracy"] - base["accuracy"]) * 100
    return f"{speed:.2f}x faster, {fewer:.0%} fewer tokens written, accuracy {dacc:+.1f} points"


def main():
    import sys
    d = Path(sys.argv[1] if len(sys.argv) > 1 else "bench/results")
    for f in sorted(d.glob("*.jsonl")):
        if "honesty" in f.name:
            print_honesty(d)
            continue
        s = summarize(read(f))
        print(f.name, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in s.items()})



def auroc(real: list, bad: list):
    """Probability that a random bad-subtitle score exceeds a random real-subtitle score (ties count half).
    0.5 = the score cannot tell them apart, 1.0 = perfectly separates them."""
    if not real or not bad:
        return None
    wins = sum((b > r) + 0.5 * (b == r) for b in bad for r in real)
    return wins / (len(real) * len(bad))


def honesty_summary(rows: list[dict]) -> dict:
    """Rates over all handoffs of all questions. 'Caught' = the check flagged the bad subtitle."""
    hs = [h for r in rows for h in r["handoffs"]]

    def rate(vals):
        vals = [v for v in vals if v is not None]
        return (sum(bool(v) for v in vals) / len(vals), len(vals)) if vals else (None, 0)

    faithful, nf = rate([h["faithful"] for h in hs])
    shuf, ns = rate([h["shuffled_caught"] for h in hs])
    corr, nc = rate([h["corrupted_caught"] for h in hs])
    js_ok = [h["js"] for h in hs if h["faithful"] and h["js"] is not None]
    js_bad = [h["js"] for h in hs if h["faithful"] is False and h["js"] is not None]
    mean = lambda xs: statistics.mean(xs) if xs else None  # noqa: E731
    # The check measures consistency, not correctness, so split it by whether the real run was right.
    ok_h = [h["faithful"] for r in rows if r.get("ok") for h in r["handoffs"] if h["faithful"] is not None]
    bad_h = [h["faithful"] for r in rows if r.get("ok") is False for h in r["handoffs"] if h["faithful"] is not None]
    flagged = [r.get("ok") for r in rows for h in r["handoffs"] if h["faithful"] is False]
    g = lambda key: [h[key] for h in hs if h.get(key) is not None]  # noqa: E731
    return {"questions": len(rows), "handoffs": nf, "faithful_rate": faithful,
            "gap_real_mean": mean(g("gap")), "gap_shuffled_mean": mean(g("shuffled_gap")),
            "gap_corrupted_mean": mean(g("corrupted_gap")),
            "gap_empty_mean": mean(g("empty_gap")),
            "real_flagged_rate": (1 - faithful) if faithful is not None else None,
            "auroc_empty": auroc(g("gap"), g("empty_gap")),  # >0.5: a real subtitle beats having none
            "auroc_shuffled": auroc(g("gap"), g("shuffled_gap")),
            "auroc_corrupted": auroc(g("gap"), g("corrupted_gap")),
            "faithful_rate_when_correct": (sum(ok_h) / len(ok_h)) if ok_h else None,
            "faithful_rate_when_wrong": (sum(bad_h) / len(bad_h)) if bad_h else None,
            "flagged_that_were_wrong": (sum(1 for x in flagged if x is False) / len(flagged)) if flagged else None,
            "shuffled_catch_rate": shuf, "shuffled_n": ns,
            "corrupted_catch_rate": corr, "corrupted_n": nc,
            "mean_js_faithful": mean(js_ok), "mean_js_unfaithful": mean(js_bad)}


def print_honesty(d) -> None:
    for f in sorted(Path(d).glob("*honesty*.jsonl")):
        print(f.name, {k: (round(v, 3) if isinstance(v, float) else v)
                       for k, v in honesty_summary(read(f)).items()})


if __name__ == "__main__":
    main()
