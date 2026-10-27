"""Record one real run of the website animation's question on Nebius Token Factory (usual multi-agent flow).
Saves each agent's real notes, seconds and tokens. Usage: python -m bench.record_animation"""
import json, sys, time, platform
from pathlib import Path
from telepathy.llm import LLM, SETTINGS
from telepathy.baseline_tf import _messages
from telepathy.roles import split_team

QUESTION = ("A bakery sells muffins for 35 rupees and cookies for 18 rupees. On Monday it sold 24 muffins and 40 cookies. "
            "On Tuesday it sold a quarter more muffins than on Monday, but 10 fewer cookies. It spends 40% of its two-day "
            "sales on ingredients. How much profit does it make over the two days?")
OUT = Path(__file__).parent / "results" / "recordings" / "animation_usual_flow.json"

def main():
    llm = LLM(max_usd=0.05)
    early, final = split_team("sequential")
    notes, agents, t0 = "", [], time.perf_counter()
    for role in early + [final]:
        u0 = (llm.usage.tokens_in, llm.usage.tokens_out, llm.usage.cached)
        s = time.perf_counter()
        out = llm.chat(f"anim:{role}", "super", _messages(role, QUESTION, notes, ""), max_tokens=600, temperature=0.0, cache=False)
        agents.append({"role": role, "seconds": round(time.perf_counter() - s, 2), "text": out,
                       "tokens_in": llm.usage.tokens_in - u0[0], "tokens_out": llm.usage.tokens_out - u0[1],
                       "words_written": len(out.split()), "cached": llm.usage.cached - u0[2]})
        notes += f"\n[{role.title()}]: {out}"
    rec = {"question": QUESTION, "model": SETTINGS.models["super"], "provider": "nebius_token_factory",
           "recorded_at": time.strftime("%Y-%m-%d %H:%M:%S"), "temperature": 0.0,
           "total_seconds": round(time.perf_counter() - t0, 2), "agents": agents,
           "total_tokens_in": llm.usage.tokens_in, "total_tokens_out": llm.usage.tokens_out,
           "total_words_written": sum(a["words_written"] for a in agents), "cost_usd": round(llm.usage.cost_usd, 5)}
    OUT.write_text(json.dumps(rec, indent=2))
    print(json.dumps({k: v for k, v in rec.items() if k != "agents"}, indent=1))
    for a in agents: print(a["role"], a["seconds"], "s", a["words_written"], "words", a["tokens_in"], "in", a["tokens_out"], "out", "cached", a["cached"])

if __name__ == "__main__":
    main()
