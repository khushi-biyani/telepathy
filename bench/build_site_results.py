"""Build the website's results from the Kaggle result files (nothing typed by hand).

    python -m bench.build_site_results

Writes dashboard/src/data/results.json (the summary the page shows), and copies the raw per-question files to
dashboard/public/evidence/runs/ (full rows, for download) and dashboard/public/evidence/slim/ (small, for the
in-browser check).
"""
from __future__ import annotations

import json
import math
import shutil
import statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "bench" / "results"
PUB = ROOT / "dashboard" / "public" / "evidence"
TASKS = [  # key, label, folder, file prefix, what the questions are, yardstick
    ("maths", "School maths", RES / "kaggle_run/saved/test_rerun", "gsm8k_test", "150 school maths word problems",
     {"published_4b": 88.2}),
    ("coding", "Coding", RES / "kaggle_teams/saved/teams", "mbppplus_test", "60 small Python tasks, checked by running tests",
     {"published_4b": 73.5}),
    ("medical", "Medical exam", RES / "kaggle_teams/saved/teams", "medqa_test", "60 US medical licensing exam questions",
     {"published_4b": 66.3, "random_guess": 25.0}),
]
METHODS = [("single", "single"), ("text", "text"), ("latent", "latent_s10")]


def sign_p(x: int, y: int) -> float:
    n, k = x + y, min(x, y)
    return 1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, j) for j in range(k + 1)) / 2 ** n)


def main():
    (PUB / "runs").mkdir(parents=True, exist_ok=True)
    (PUB / "slim").mkdir(parents=True, exist_ok=True)
    out = []
    for key, label, folder, prefix, about, yard in TASKS:
        rows = {}
        for m, suffix in METHODS:
            src = folder / f"{prefix}_{suffix}.jsonl"
            rows[m] = {r["id"]: r for r in map(json.loads, src.read_text().splitlines()) if r}
            shutil.copy(src, PUB / "runs" / f"{key}_{m}.jsonl")
            slim = [{"id": r["id"], "gold": r["gold"], "pred": r["pred"], "ok": r["ok"], "seconds": round(r["seconds"], 1),
                     "tokens": r.get("tokens_written", 0)} for r in rows[m].values()]
            (PUB / "slim" / f"{key}_{m}.json").write_text(json.dumps(slim))
        ids = sorted(set.intersection(*(set(v) for v in rows.values())))
        methods = {}
        for m in rows:
            v = [rows[m][i] for i in ids]
            methods[m] = {"right": sum(r["ok"] for r in v), "acc": round(100 * sum(r["ok"] for r in v) / len(ids), 1),
                          "sec": round(st.mean(r["seconds"] for r in v), 1), "tokens": round(st.mean(r.get("tokens_written", 0) for r in v))}
        pairs = {}
        for a, b in (("latent", "text"), ("latent", "single"), ("text", "single")):
            x = sum(rows[a][i]["ok"] and not rows[b][i]["ok"] for i in ids)
            y = sum(rows[b][i]["ok"] and not rows[a][i]["ok"] for i in ids)
            pairs[f"{a}_vs_{b}"] = {"only_a": x, "only_b": y, "p": round(sign_p(x, y), 3)}
        out.append({"key": key, "label": label, "about": about, "n": len(ids), "methods": methods, "pairs": pairs,
                    "speedup_vs_team": round(methods["text"]["sec"] / methods["latent"]["sec"], 1),
                    "tokens_saved_vs_team": round(100 * (1 - methods["latent"]["tokens"] / methods["text"]["tokens"])),
                    "yardstick": yard})
    # Web research: 3 real-search questions recorded for the demo (multi-agent and Telepathy only; no single-agent run)
    gal = Path(__file__).parent / "results" / "gallery"
    rids = ["eiffel_burj", "burj_shanghai", "moon_curiosity"]
    recs = [json.loads((gal / f"{i}.json").read_text()) for i in rids]
    methods, rows = {}, {}
    for m, mode in (("text", "text"), ("latent", "latent")):
        rs = [next(x for x in r["runs"] if x["mode"] == mode) for r in recs]
        rows[m] = [{"id": r["id"], "gold": r["answer"], "pred": x.get("pred"), "ok": x["correct"], "seconds": round(x["seconds"], 1),
                    "tokens": x["tokens_written"]} for r, x in zip(recs, rs)]
        (PUB / "slim" / f"research_{m}.json").write_text(json.dumps(rows[m]))
        methods[m] = {"right": sum(x["correct"] for x in rs), "acc": round(100 * sum(x["correct"] for x in rs) / len(rs), 1),
                      "sec": round(st.mean(x["seconds"] for x in rs), 1), "tokens": round(st.mean(x["tokens_written"] for x in rs))}
    out.append({"key": "research", "label": "Web research", "about": f"{len(recs)} questions answered from real web pages", "n": len(recs),
                "methods": methods, "pairs": {}, "speedup_vs_team": round(methods["text"]["sec"] / methods["latent"]["sec"], 1),
                "tokens_saved_vs_team": round(100 * (1 - methods["latent"]["tokens"] / methods["text"]["tokens"])), "yardstick": {}})
    research_questions = {r["id"]: r["question"] for r in recs}

    meta = {"model": "nvidia/Llama-3.1-Nemotron-Nano-4B-v1.1", "gpu": "Kaggle NVIDIA Tesla T4", "dtype": "float16",
            "greedy": True, "silent_steps": 10,
            "notes": {"maths": "up to 384 tokens per agent", "coding": "up to 1,024 tokens per agent", "medical": "up to 1,024 tokens per agent"},
            "published_source": "https://arxiv.org/abs/2511.20639"}
    # the questions themselves, so the Proof table can show real text instead of IDs
    from .datasets import load
    qs = {}
    for task in ("gsm8k", "mbppplus", "medqa"):
        for it in load(task, "all"):
            qs[it["id"]] = it["question"].split("\n\nGive your final answer")[0].split("\nYour code should pass")[0].strip()
    qs.update(research_questions)
    (PUB / "slim" / "questions.json").write_text(json.dumps(qs, ensure_ascii=False))
    (ROOT / "dashboard" / "src" / "data" / "results.json").write_text(json.dumps({"meta": meta, "tasks": out}, indent=1))
    for t in out:
        print(t["label"], {m: v["acc"] for m, v in t["methods"].items()}, f"x{t['speedup_vs_team']}", f"-{t['tokens_saved_vs_team']}%",
              {k: v["p"] for k, v in t["pairs"].items()})


if __name__ == "__main__":
    main()
