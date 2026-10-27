"""Measure the Honesty Check on the real model.

For every question, with latent handoffs and a subtitle at each one:
  * faithful?      does the final answer survive replacing the real thoughts with the subtitle?
  * shuffled ctrl  subtitle swapped in from a DIFFERENT question  (should be flagged)
  * corrupted ctrl one number in the subtitle changed            (should be flagged)

    python -m bench.honesty_bench --n 30 --steps 10 --dtype float16 --device cuda

Resumable (appends one JSON row per question). Greedy decoding only.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from telepathy import Config, Policy, TelepathyTeam
from telepathy import honesty

from .datasets import grade, load


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--task", default="gsm8k", choices=["gsm8k", "arc"])
    ap.add_argument("--split", default="dev", choices=["dev", "test", "all"])
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--steps", type=int, default=10)
    ap.add_argument("--model", default=Config.model_id)
    ap.add_argument("--device", default="auto")
    ap.add_argument("--dtype", default="auto", choices=["auto", "bfloat16", "float16", "float32"])
    ap.add_argument("--max-new-tokens", type=int, default=384)
    ap.add_argument("--hide-question", action="store_true",
                    help="strict variant: later agents on the subtitle path are not shown the question")
    ap.add_argument("--subtitle-style", default="plain", choices=["plain", "rich"],
                    help="rich asks the agent to restate the key numbers and facts in its subtitle")
    ap.add_argument("--out", default="bench/results/honesty")
    a = ap.parse_args()

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{a.task}_{a.split}_honesty{'-strict' if a.hide_question else ''}{'-rich' if a.subtitle_style == 'rich' else ''}_s{a.steps}.jsonl"
    done = {json.loads(l)["id"] for l in path.read_text().splitlines() if l.strip()} if path.exists() else set()

    cfg = Config(model_id=a.model, device=a.device, dtype=a.dtype, max_new_tokens=a.max_new_tokens)
    # flag_only: we want to MEASURE the check, not change the run when it fires
    team = TelepathyTeam("sequential", "auto", a.steps, config=cfg, subtitle_style=a.subtitle_style,
                         policy=Policy(honesty_check="always", on_unfaithful="flag_only"))
    items = load(a.task, a.split, a.n)
    prev_subs: dict = {}
    for item in items:
        if item["id"] in done:
            continue
        r = team.run(item["question"])
        st = r.state
        pred, ok = grade(item, r.answer)
        handoffs = []
        for k, h in enumerate(r.handoffs):
            if a.hide_question:  # the main-run verdict used the normal check; redo it strictly
                res = honesty.check(team, st, k, hide_question=True)
                h.faithful, h.js, gap = res.faithful, res.js, res.gap
            else:
                gap = st.gap.get(k)
            c = honesty.controls(team, st, k, prev_subs, a.hide_question)
            handoffs.append({"k": k, "role": h.role, "subtitle": h.subtitle, "faithful": h.faithful,
                             "js": h.js, "gap": gap, "shuffled_caught": c["shuffled"],
                             "corrupted_caught": c["corrupted"], "shuffled_gap": c["shuffled_gap"],
                             "corrupted_gap": c["corrupted_gap"], "empty_caught": c["empty"],
                             "empty_gap": c["empty_gap"]})
        prev_subs = dict(st.subs)
        row = {"id": item["id"], "ok": ok, "pred": pred, "gold": item["gold"], "answer": r.answer,
               "steps": a.steps, "seconds": r.metrics["seconds"], "handoffs": handoffs}
        with path.open("a") as f:
            f.write(json.dumps(row) + "\n")
        flags = "".join("F" if h["faithful"] else "x" for h in handoffs)
        print(f"{item['id']} ok={ok} faithful[{flags}]", flush=True)


if __name__ == "__main__":
    main()
