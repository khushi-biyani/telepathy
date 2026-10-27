"""Does the silent hand-off carry real information? Three arms on the same questions (greedy, resumable).

  real            the normal Telepathy run: 3 agents think silently, the Solver answers
  no_thinking     the same, but the silent agents take 0 thinking steps (they only read their instructions)
  other_question  the silent agents think about a DIFFERENT question; the Solver still gets the real question

    python -m bench.mismatch_bench --split dev --n 50 --dtype float16 --device cuda

If `real` beats `no_thinking`, the silent thinking helps. If `real` beats `other_question`, what the agents
think about matters, so the cache carries information about this question. (`other_question` also puts the
other question's words in the cache, so read it as "wrong notebook", not as a perfectly clean test.)
Results: bench/results/mismatch/<task>_<split>_<arm>.jsonl, then a summary.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from telepathy import Config
from telepathy.engine import LocalModel
from telepathy.latent import think
from telepathy.roles import split_team

from .datasets import grade, load

ARMS = ("real", "no_thinking", "other_question")
OUT = Path(__file__).parent / "results" / "mismatch"


def donor_index(i: int, n: int) -> int:
    """The question whose thoughts are used as the wrong notebook: 7 places along, never the same one."""
    return (i + 7) % n if n > 7 else (i + 1) % n


def run_arm(lm: LocalModel, question: str, donor: str | None, steps: int, topology: str = "sequential"):
    """Returns (answer, tokens_written, seconds). Follows the engine's latent path with the full cache shared."""
    early, final = split_team(topology)
    t0, past = time.perf_counter(), None
    for role in early:
        ids = lm.prompt_ids(role, donor if donor is not None else question, "", "", first=past is None)
        past = think(lm.model, ids, past, steps, lm.target_norm)
    ids = lm.prompt_ids(final, question, "", "", first=past is None)
    ans, n, _ = lm.decode(ids, past)
    lm.sync()
    return ans, n, time.perf_counter() - t0


def arm_settings(arm: str, steps: int):
    return {"real": (False, steps), "no_thinking": (False, 0), "other_question": (True, steps)}[arm]


def summarize(rows: dict[str, dict[str, dict]]) -> str:
    ids = sorted(set.intersection(*(set(r) for r in rows.values())))
    lines = [f"Questions answered in every arm: {len(ids)}", ""]
    for arm, r in rows.items():
        ok = sum(r[i]["ok"] for i in ids)
        lines.append(f"{arm:15s} {ok}/{len(ids)} right = {100 * ok / max(len(ids), 1):.1f}%")
    if "real" in rows:
        for other in ("no_thinking", "other_question"):
            if other in rows:
                both = sum(rows["real"][i]["ok"] and rows[other][i]["ok"] for i in ids)
                only_real = sum(rows["real"][i]["ok"] and not rows[other][i]["ok"] for i in ids)
                only_other = sum(rows[other][i]["ok"] and not rows["real"][i]["ok"] for i in ids)
                lines.append(f"real vs {other}: both right {both}, only real right {only_real}, only {other} right {only_other}")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--task", default="gsm8k", choices=["gsm8k"])
    ap.add_argument("--split", default="dev", choices=["dev", "test", "all"])
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--steps", type=int, default=10)
    ap.add_argument("--arms", default=",".join(ARMS))
    ap.add_argument("--model", default=Config.model_id)
    ap.add_argument("--device", default="auto")
    ap.add_argument("--dtype", default="auto", choices=["auto", "bfloat16", "float16", "float32"])
    a = ap.parse_args()

    items = load(a.task, a.split, a.n)
    lm = LocalModel.get(Config(model_id=a.model, device=a.device, dtype=a.dtype))
    OUT.mkdir(parents=True, exist_ok=True)
    arms = [x for x in a.arms.split(",") if x]
    rows: dict[str, dict[str, dict]] = {}
    for arm in arms:
        path = OUT / f"{a.task}_{a.split}_{arm}.jsonl"
        have = {json.loads(l)["id"]: json.loads(l) for l in path.read_text().splitlines() if l.strip()} if path.exists() else {}
        use_donor, steps = arm_settings(arm, a.steps)
        with path.open("a") as f:
            for i, item in enumerate(items):
                if item["id"] in have:
                    continue
                donor = items[donor_index(i, len(items))]["question"] if use_donor else None
                ans, n, sec = run_arm(lm, item["question"], donor, steps)
                pred, ok = grade(item, ans)
                row = {"id": item["id"], "arm": arm, "gold": item["gold"], "pred": pred, "ok": ok, "seconds": round(sec, 2),
                       "tokens_written": n, "steps": steps, "donor": items[donor_index(i, len(items))]["id"] if use_donor else None}
                f.write(json.dumps(row) + "\n"); f.flush()
                have[item["id"]] = row
                print(f"{arm:15s} {item['id']:10s} gold={item['gold']:>8s} pred={str(pred):>8s} {'ok' if ok else 'WRONG'}", flush=True)
        rows[arm] = have
    text = summarize(rows)
    (OUT / f"{a.task}_{a.split}_summary.md").write_text(text + "\n")
    print("\n" + text)


if __name__ == "__main__":
    main()
