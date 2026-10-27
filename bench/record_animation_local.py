"""Record the website animation's question on the LOCAL small model, in both modes, with real timings.

    python -m bench.record_animation_local --dtype float16 --device cuda --repeats 3

Runs one warm-up first (the first GPU run is slower), then `--repeats` runs of each mode, one after the other.
Saves every run, per agent: seconds, words written, silent steps. Output: bench/results/recordings/animation_local.json
"""
from __future__ import annotations

import argparse
import json
import platform
import statistics
import time
from pathlib import Path

from telepathy import Config, TelepathyTeam, Policy
from telepathy.roles import split_team
from bench.record_animation import QUESTION

OUT = Path(__file__).parent / "results" / "recordings" / "animation_local.json"
WARMUP = "What is 12 plus 30, times 2?"


def one(mode: str, steps: int, cfg: Config, question: str):
    events = []
    t0 = time.perf_counter()
    stamp = lambda e: events.append({**e, "t": time.perf_counter() - t0})  # noqa: E731
    team = TelepathyTeam("sequential", mode, steps, config=cfg, on_event=stamp, policy=Policy(honesty_check="off"))
    res = team.run(question)
    early, final = split_team("sequential")
    roles = early + [final]
    starts = {e["role"]: e["t"] for e in events if e["type"] == "agent_started"}
    end = next(e["t"] for e in events if e["type"] == "final")
    agents = []
    for i, r in enumerate(roles):
        s, e = starts[r], (starts[roles[i + 1]] if i + 1 < len(roles) else end)
        text = "".join(x["text"] for x in events if x["type"] == "token" and x["role"] == r)
        agents.append({"role": r, "seconds": round(e - s, 2), "words_written": len(text.split()), "text": text,
                       "silent_steps": sum(1 for x in events if x["type"] == "latent_step" and x["role"] == r)})
    return {"mode": mode, "seconds": round(res.metrics["seconds"], 2), "tokens_written": res.metrics["tokens_written"],
            "latent_steps": res.metrics["latent_steps"], "answer": res.answer, "agents": agents}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=10)
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--model", default=Config.model_id)
    ap.add_argument("--device", default="auto")
    ap.add_argument("--dtype", default="auto", choices=["auto", "bfloat16", "float16", "float32"])
    ap.add_argument("--max-new", type=int, default=1024, help="most tokens one agent may write (the benchmark used 384)")
    ap.add_argument("--question", default=QUESTION)
    ap.add_argument("--gsm8k-id", help="use this GSM8K test question instead, e.g. gsm8k-80 (graded against the known answer)")
    a = ap.parse_args()
    item = None
    out_path = OUT
    if a.gsm8k_id:
        from bench.datasets import load
        item = next(i for i in load("gsm8k", "all") if i["id"] == a.gsm8k_id)
        a.question = item["question"]
        out_path = OUT.with_name(f"animation_local_{a.gsm8k_id}.json")
    cfg = Config(model_id=a.model, device=a.device, dtype=a.dtype, max_new_tokens=a.max_new)
    for mode in ("text", "latent"):
        one(mode, a.steps, cfg, WARMUP)  # warm-up, not saved
    runs = [one(m, a.steps, cfg, a.question) for _ in range(a.repeats) for m in ("text", "latent")]
    import torch, transformers
    rec = {"question": a.question, "model": a.model, "dtype": a.dtype, "device": a.device, "latent_steps": a.steps, "max_new_tokens": a.max_new,
           "recorded_at": time.strftime("%Y-%m-%d %H:%M:%S"), "repeats": a.repeats,
           "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu",
           "versions": {"torch": torch.__version__, "transformers": transformers.__version__, "python": platform.python_version()},
           "runs": runs}
    if item:
        from bench.datasets import grade
        rec["gsm8k_id"], rec["gold"] = item["id"], item["gold"]
        for r in runs:
            r["pred"], r["correct"] = grade(item, r["answer"])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(rec, indent=2))
    for m in ("text", "latent"):
        rs = [r for r in runs if r["mode"] == m]
        print(f"{m:6s} median {statistics.median(r['seconds'] for r in rs):.1f}s  "
              f"words {[r['tokens_written'] for r in rs]}  seconds {[r['seconds'] for r in rs]}")
    if item:
        print("question:", item["question"], "\nright answer:", item["gold"])
        print("answers:", {m: [(r["pred"], r["correct"]) for r in runs if r["mode"] == m] for m in ("text", "latent")})
    print("saved", out_path)


main()
