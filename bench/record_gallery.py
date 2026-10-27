"""Record the website's demo gallery on the LOCAL small model, in both modes, with real timings and grades.

    python -m bench.record_gallery --dtype float16 --device cuda            # every item except the bakery one
    python -m bench.record_gallery --ids pets,merge --dtype float16 --device cuda

One warm-up run first, then `--repeats` runs of each mode. Each item is saved as soon as it finishes to
bench/results/gallery/<id>.json (the bakery question was recorded earlier with bench.record_animation_local).
"""
from __future__ import annotations

import argparse
import json
import platform
import time
from pathlib import Path

from telepathy import Config, Policy, TelepathyTeam
from telepathy.roles import TASK_ROLES, split_team
from telepathy.tools import tavily

from .gallery import grade_item, load_gallery

OUT = Path(__file__).parent / "results" / "gallery"
WARMUP = "What is 12 plus 30, times 2?"


def one(item: dict, mode: str, steps: int, cfg: Config, question: str | None = None, quiet: bool = False):
    kind = item["kind"]
    topology = "research" if kind == "research" else "sequential"
    task = item.get("task") or (kind if kind in TASK_ROLES else "math")
    context = ""
    if kind == "research":
        context = tavily.as_content(json.loads(Path(item["fixture"]).read_text()))
    events, t0 = [], time.perf_counter()
    team = TelepathyTeam(topology, mode, steps, config=cfg, task=task, demo=(kind == "research"),
                         on_event=lambda e: events.append({**e, "t": time.perf_counter() - t0}),
                         policy=Policy(honesty_check="off"))
    res = team.run(question or item["question"], context=context)
    early, final = split_team(topology)
    roles = early + [final]
    starts = {e["role"]: e["t"] for e in events if e["type"] == "agent_started"}
    end = next(e["t"] for e in events if e["type"] == "final")
    agents = []
    for i, r in enumerate(roles):
        s, e = starts[r], (starts[roles[i + 1]] if i + 1 < len(roles) else end)
        text = "".join(x["text"] for x in events if x["type"] == "token" and x["role"] == r)
        agents.append({"role": r, "seconds": round(e - s, 2), "words_written": len(text.split()), "text": text,
                       "silent_steps": sum(1 for x in events if x["type"] == "latent_step" and x["role"] == r)})
    safety = [{k: v for k, v in e.items() if k != "t"} for e in events
              if e["type"] in ("outside_content", "scan") or (e["type"] == "handoff" and e.get("reason"))]
    rec = {"mode": mode, "seconds": round(res.metrics["seconds"], 2), "tokens_written": res.metrics["tokens_written"],
           "latent_steps": res.metrics["latent_steps"], "answer": res.answer, "agents": agents, "safety_events": safety}
    if not quiet:
        pred, ok, extra = grade_item(item, res.answer)
        rec.update({"pred": pred, "correct": ok, **extra})
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", default="", help="comma list; default is every item except the bakery one")
    ap.add_argument("--steps", type=int, default=10)
    ap.add_argument("--repeats", type=int, default=1, help="timings were identical across repeats in earlier recordings")
    ap.add_argument("--max-new", type=int, default=1024)
    ap.add_argument("--model", default=Config.model_id)
    ap.add_argument("--device", default="auto")
    ap.add_argument("--dtype", default="auto", choices=["auto", "bfloat16", "float16", "float32"])
    a = ap.parse_args()
    items = load_gallery(resolve=True)
    want = [x for x in a.ids.split(",") if x] or [i["id"] for i in items if i["id"] != "bakery"]
    cfg = Config(model_id=a.model, device=a.device, dtype=a.dtype, max_new_tokens=a.max_new)
    warm = {"id": "warmup", "kind": "math", "question": WARMUP, "answer": "84"}
    for mode in ("text", "latent"):
        one(warm, mode, a.steps, cfg, quiet=True)
    import torch, transformers
    OUT.mkdir(parents=True, exist_ok=True)
    for item in items:
        if item["id"] not in want or (OUT / f"{item['id']}.json").exists():
            continue  # resumable: finished items are skipped
        runs = [one(item, m, a.steps, cfg) for _ in range(a.repeats) for m in ("text", "latent")]
        rec = {k: item[k] for k in ("id", "title", "kind", "task", "blurb", "question", "answer", "func", "tests", "fixture", "attack_word") if k in item}
        rec.update({"model": a.model, "dtype": a.dtype, "latent_steps": a.steps, "max_new_tokens": a.max_new,
                    "recorded_at": time.strftime("%Y-%m-%d %H:%M:%S"), "repeats": a.repeats,
                    "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu",
                    "versions": {"torch": torch.__version__, "transformers": transformers.__version__, "python": platform.python_version()},
                    "runs": runs})
        (OUT / f"{item['id']}.json").write_text(json.dumps(rec, indent=2))
        for m in ("text", "latent"):
            r = [x for x in runs if x["mode"] == m][0]
            print(f"{item['id']:9s} {m:6s} {r['seconds']:6.1f}s  {r['tokens_written']:5d} tokens  answer={r['pred']!r}  correct={r['correct']}", flush=True)
    print("saved to", OUT)


if __name__ == "__main__":
    main()
