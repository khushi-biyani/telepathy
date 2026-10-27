"""Resumable benchmark sweep: modes x latent steps x task.

    python -m bench.run_bench --task gsm8k --split dev --modes single,text,latent --steps 0,5,10,20 --n 50
    python -m bench.run_bench --task gsm8k --dtype float16        # Kaggle T4/P100 (no bf16)

Results append to bench/results/<task>_<split>_<mode>[_s<steps>].jsonl; finished question ids are
skipped, so an interrupted run picks up where it stopped. Greedy decoding only.
"""
from __future__ import annotations

import argparse
import json
import platform
from pathlib import Path

import torch
import transformers

from telepathy import Config, Policy, TelepathyTeam

from .datasets import ROLES_FOR, grade, load


def result_path(out: Path, task: str, split: str, mode: str, steps: int, tag: str = "") -> Path:
    suffix = f"_s{steps}" if mode in ("latent", "auto") else ""
    return out / f"{task}_{split}_{mode}{('-' + tag) if tag else ''}{suffix}.jsonl"


def done_ids(path: Path) -> set:
    if not path.exists():
        return set()
    return {json.loads(l)["id"] for l in path.read_text().splitlines() if l.strip()}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--task", default="gsm8k", choices=["gsm8k", "arc", "medqa", "mbppplus"])
    ap.add_argument("--split", default="test", choices=["dev", "test", "all"])
    ap.add_argument("--modes", default="single,text,latent")
    ap.add_argument("--steps", default="10", help="comma list of latent steps (latent/auto only)")
    ap.add_argument("--n", type=int, default=None)
    ap.add_argument("--model", default=Config.model_id)
    ap.add_argument("--device", default="auto")
    ap.add_argument("--dtype", default="auto", choices=["auto", "bfloat16", "float16", "float32"])
    ap.add_argument("--max-new-tokens", type=int, default=384)
    ap.add_argument("--topology", default="sequential", choices=["sequential", "team2", "team3", "team6", "team8"],
                    help="team size: sequential is the 4-agent team; teamN has N agents")
    ap.add_argument("--share", default="auto", choices=["auto", "full", "thoughts_only"],
                    help="thoughts_only hands over only each agent's silent steps (Section 8a.3); measure its accuracy cost")
    ap.add_argument("--honesty", default="sample", choices=["off", "sample", "always"], help="auto mode only")
    ap.add_argument("--sample-rate", type=float, default=0.3, help="auto mode, honesty=sample")
    ap.add_argument("--out", default="bench/results")
    a = ap.parse_args()

    items = load(a.task, a.split, a.n)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    cfg = Config(model_id=a.model, device=a.device, dtype=a.dtype, max_new_tokens=a.max_new_tokens)
    env = {"torch": torch.__version__, "transformers": transformers.__version__,
           "device": a.device, "python": platform.python_version()}
    print(f"env={env} items={len(items)}")

    for mode in a.modes.split(","):
        step_list = [int(s) for s in a.steps.split(",")] if mode in ("latent", "auto") else [0]
        for steps in step_list:
            tag = "-".join(t for t in (a.topology if a.topology != "sequential" else "", a.honesty if mode == "auto" else "", a.share if a.share != "auto" else "") if t)
            path = result_path(out, a.task, a.split, mode, steps, tag)
            skip = done_ids(path)
            team = TelepathyTeam(a.topology, mode, latent_steps=steps, config=cfg, share=a.share, task=ROLES_FOR.get(a.task, "math"),
                                 policy=Policy(honesty_check=a.honesty, sample_rate=a.sample_rate))
            for item in items:
                if item["id"] in skip:
                    continue
                r = team.run(item["question"])
                pred, ok = grade(item, r.answer)
                row = {"id": item["id"], "gold": item["gold"], "pred": pred, "ok": ok, "mode": mode,
                       "steps": steps, "answer": r.answer, "env": env, **r.metrics,
                       "fallbacks": r.metrics.get("fallbacks", 0),
                       "trace": [{"role": h.role, "mode": h.mode_used, "text": h.text, "subtitle": h.subtitle}
                                 for h in r.handoffs]}
                with path.open("a") as f:
                    f.write(json.dumps(row) + "\n")
                print(f"{path.name} {item['id']} ok={ok} {r.metrics['seconds']:.1f}s", flush=True)


if __name__ == "__main__":
    main()
