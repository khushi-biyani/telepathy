"""Text-mode team on Nebius Token Factory (Nemotron 3 Super): the 'agents talking in English'
baseline at production scale. Same topology and role prompts as the local text mode.

    python -m telepathy.baseline_tf --n 100 --estimate     # no network, no cost
    python -m telepathy.baseline_tf --n 100 --run --yes     # real calls: costs money, see estimate
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from .config import DEFAULT_SYSTEM
from .llm import LLM, SETTINGS, cost
from . import trust
from .roles import reads_content, role_prompt, split_team

# Rough size of one GSM8K-style task, used only for the pre-batch budget estimate.
EST_PROMPT_TOKENS, EST_NOTE_TOKENS, EST_OUT_TOKENS = 200, 300, 350


def estimate_usd(n_tasks: int, size: str = "super", agents: int = 4) -> float:
    """Worst-ish case: every agent writes EST_OUT_TOKENS and re-reads everyone's notes."""
    tin = sum(EST_PROMPT_TOKENS + i * EST_NOTE_TOKENS for i in range(agents))
    tout = agents * EST_OUT_TOKENS
    return n_tasks * cost(size, tin, tout)


def _messages(role: str, question: str, notes: str, context: str, task: str = "math"):
    user = f"Question: {question}"
    if context:
        user += f"\n\n{trust.CONTEXT_LABEL}:\n{context}"
    if notes:
        user += f"\n\nTeam notes so far:\n{notes}"
    return [{"role": "system", "content": DEFAULT_SYSTEM},
            {"role": "user", "content": f"{role_prompt(role, task)}\n\n{user}"}]


def run_text_team(llm: LLM, question: str, topology: str = "sequential", context: str = "",
                  size: str = "super", tag: str = "q", max_tokens: int = 600):
    """Returns (answer, metrics). Greedy (temperature 0)."""
    early, final = split_team(topology)
    notes, t0 = "", time.perf_counter()
    before = (llm.usage.tokens_in, llm.usage.tokens_out, llm.usage.cost_usd, llm.usage.cached)
    out = ""
    for role in early + [final]:
        out = llm.chat(f"baseline:{topology}:{role}:{tag}", size,
                       _messages(role, question, notes, context if reads_content(topology, role) else ""),
                       max_tokens=max_tokens, temperature=0.0, cache=False)
        notes += f"\n[{role.title()}]: {out}"
    metrics = {"seconds": time.perf_counter() - t0,
               "tokens_in": llm.usage.tokens_in - before[0],
               "tokens_out": llm.usage.tokens_out - before[1],
               "cost_usd": llm.usage.cost_usd - before[2],
               "cached": llm.usage.cached - before[3]}  # must be 0: a cached call would cost nothing and look free
    return out, metrics


def stream_text_team(question: str, emit, topology: str = "sequential", size: str = "super",
                     context: str = "", llm: LLM | None = None, max_usd: float | None = None,
                     task: str = "math", max_tokens: int = 600):
    """Run the text team live on Token Factory and emit the same events as the local engine, so the
    dashboard's English lane works unchanged. Each agent's text arrives as one `token` event."""
    llm = llm or LLM(max_usd=max_usd)
    early, final = split_team(topology)
    roles = early + [final]
    t0 = time.perf_counter()
    stamp = lambda e: emit({**e, "t": round(time.perf_counter() - t0, 4)})  # noqa: E731
    stamp({"type": "run_started", "mode": "text", "topology": topology, "question": question,
           "roles": roles, "model": SETTINGS.models[size], "provider": "nebius_token_factory", "live": True})
    notes, out = "", ""
    for i, role in enumerate(roles):
        stamp({"type": "agent_started", "role": role})
        out = llm.chat(f"live:{role}", size,
                       _messages(role, question, notes, context if reads_content(topology, role) else "", task),
                       max_tokens=max_tokens, temperature=0.0, cache=False)
        stamp({"type": "token", "role": role, "text": out, "bulk": True})
        notes += f"\n[{role.title()}]: {out}"
        if i < len(early):
            stamp({"type": "handoff", "from": role, "to": roles[i + 1], "handoff": i, "mode_used": "text"})
    u = llm.usage
    stamp({"type": "final", "answer": out, "metrics": {
        "seconds": time.perf_counter() - t0, "tokens_in": u.tokens_in, "tokens_out": u.tokens_out,
        "tokens_written": u.tokens_out, "cost_usd": u.cost_usd}})
    stamp({"type": "run_finished"})
    return out, u.cost_usd


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--size", default="super", choices=["nano", "super", "ultra"])
    ap.add_argument("--topology", default="sequential", help="sequential (4 agents), team2, team3, team6 or team8")
    ap.add_argument("--estimate", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--yes", action="store_true", help="confirm that real, paid calls are intended")
    ap.add_argument("--workers", type=int, default=6, help="questions answered at the same time")
    ap.add_argument("--out", default="bench/results/test/gsm8k_tokenfactory_text.jsonl")
    a = ap.parse_args()

    est = estimate_usd(a.n, a.size, len(split_team(a.topology)[0]) + 1)
    print(f"estimate for {a.n} tasks on {a.size}: ${est:.2f} "
          f"(per-check cap ${SETTINGS.max_per_check}, lifetime cap ${SETTINGS.total_budget})")
    if est > 5:
        print("Estimate is over $5: stop and ask the project owner before running.")
        return
    if not (a.run and a.yes):
        return

    from bench.datasets import grade, load
    out = Path(a.out)
    if a.topology != "sequential" and a.out.endswith("gsm8k_tokenfactory_text.jsonl"):
        out = out.with_name(f"gsm8k_tokenfactory_text-{a.topology}.jsonl")
    out.parent.mkdir(parents=True, exist_ok=True)
    done = {r["id"] for r in map(json.loads, out.read_text().splitlines()) if r.get("tokens_in", 1) > 0} if out.exists() else set()
    import threading
    from concurrent.futures import ThreadPoolExecutor

    lock = threading.Lock()

    def one(item):
        llm = LLM()  # one per task, so MAX_USD_PER_CHECK applies per task
        ans, m = run_text_team(llm, item["question"], topology=a.topology, size=a.size, tag=item["id"])
        pred, ok = grade(item, ans)
        row = {"id": item["id"], "gold": item["gold"], "pred": pred, "ok": ok, "mode": "tokenfactory_text",
               "topology": a.topology, "agents": len(split_team(a.topology)[0]) + 1,
               "model": SETTINGS.models[a.size], **m}
        with lock:
            with out.open("a") as f:
                f.write(json.dumps(row) + "\n")
            print(item["id"], ok, f"${m['cost_usd']:.4f}", flush=True)

    todo = [it for it in load("gsm8k", "test", a.n) if it["id"] not in done]
    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        list(pool.map(one, todo))

if __name__ == "__main__":
    main()
