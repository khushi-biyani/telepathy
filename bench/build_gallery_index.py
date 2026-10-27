"""Build the website's gallery data from the saved recordings (no model needed).

    python -m bench.build_gallery_index

Reads bench/results/gallery/*.json (+ the bakery question from bench/results/recordings/animation_local.json),
and writes dashboard/public/gallery/<id>.json (the full recording) and dashboard/public/gallery/index.json
(a small summary the page loads first). Nothing here is typed in by hand: every number comes from the recordings.
"""
from __future__ import annotations

import json
import re
import shutil
import statistics
from pathlib import Path

from .gallery import grade_item, load_gallery

ROOT = Path(__file__).resolve().parent.parent
SRC = Path(__file__).parent / "results" / "gallery"
BAKERY = Path(__file__).parent / "results" / "recordings" / "animation_local.json"
OUT = ROOT / "dashboard" / "public" / "gallery"
KINDS = ["math", "logic", "code", "science", "research"]


def bakery_record(item: dict) -> dict:
    """The bakery question was recorded earlier (3 repeats). Use the middle run of each mode, in the gallery format."""
    r = json.loads(BAKERY.read_text())
    runs = []
    for mode in ("text", "latent"):
        rs = sorted([x for x in r["runs"] if x["mode"] == mode], key=lambda x: x["seconds"])
        x = dict(rs[len(rs) // 2])
        pred, ok, extra = grade_item(item, x["answer"])
        x.update({"pred": pred, "correct": ok, "safety_events": [], **extra})
        runs.append(x)
    rec = {k: item[k] for k in ("id", "title", "kind", "blurb", "question", "answer") if k in item}
    rec.update({k: r[k] for k in ("model", "dtype", "latent_steps", "max_new_tokens", "recorded_at", "repeats", "gpu", "versions")})
    rec["runs"] = runs
    return rec


def summarize(rec: dict, featured: bool = False) -> dict:
    out = {k: rec[k] for k in ("id", "title", "kind", "blurb", "question", "answer", "recorded_at") if k in rec}
    out["featured"] = featured
    for mode, key in (("text", "usual"), ("latent", "telepathy")):
        x = next(r for r in rec["runs"] if r["mode"] == mode)
        out[key] = {"seconds": x["seconds"], "tokens": x["tokens_written"], "correct": x["correct"],
                    "words": sum(a["words_written"] for a in x["agents"]),
                    "detail": x.get("pred") if rec["kind"] != "research" else None}
    return out


def main():
    items = {i["id"]: i for i in load_gallery(resolve=True)}
    OUT.mkdir(parents=True, exist_ok=True)
    recs = {}
    for f in SRC.glob("*.json"):
        r = json.loads(f.read_text())
        recs[r["id"]] = r
    recs["bakery"] = bakery_record(items["bakery"])
    order = [i["id"] for i in load_gallery()]
    index = []
    for gid in order:
        if gid not in recs:
            print("not recorded yet:", gid)
            continue
        (OUT / f"{gid}.json").write_text(json.dumps(recs[gid], ensure_ascii=False))
        index.append(summarize(recs[gid], bool(items[gid].get("featured"))))
    live = []
    for gid in order:
        if gid in recs:
            it = items[gid]
            entry = {"id": gid, "kind": it["kind"], "question": recs[gid]["question"], **({"task": it["task"]} if it.get("task") else {})}
            if it["kind"] == "research":
                entry["pages"] = json.loads((ROOT / it["fixture"]).read_text())
            live.append(entry)
    (ROOT / "server" / "gallery_live.json").write_text(json.dumps(live, ensure_ascii=False, indent=1))
    ref = next(iter(recs.values()))
    stats = {
        "n": len(index),
        "usual_right": sum(i["usual"]["correct"] for i in index), "telepathy_right": sum(i["telepathy"]["correct"] for i in index),
        "usual_seconds": round(sum(i["usual"]["seconds"] for i in index), 1), "telepathy_seconds": round(sum(i["telepathy"]["seconds"] for i in index), 1),
        "usual_tokens": sum(i["usual"]["tokens"] for i in index), "telepathy_tokens": sum(i["telepathy"]["tokens"] for i in index),
        "median_speedup": round(statistics.median(i["usual"]["seconds"] / i["telepathy"]["seconds"] for i in index), 1),
        "by_kind": {k: {"n": sum(i["kind"] == k for i in index),
                        "usual_right": sum(i["kind"] == k and i["usual"]["correct"] for i in index),
                        "telepathy_right": sum(i["kind"] == k and i["telepathy"]["correct"] for i in index)} for k in KINDS},
        "model": ref["model"], "gpu": ref["gpu"], "dtype": ref["dtype"], "max_new_tokens": ref["max_new_tokens"],
        "versions": ref["versions"],
    }
    (OUT / "index.json").write_text(json.dumps({"stats": stats, "items": index}, ensure_ascii=False, indent=1))
    (ROOT / "dashboard" / "src" / "data" / "gallery_index.json").write_text(json.dumps({"stats": stats, "items": index}, ensure_ascii=False))  # for the Proof table
    print(json.dumps({k: v for k, v in stats.items() if k not in ("versions",)}, indent=1))


if __name__ == "__main__":
    main()
