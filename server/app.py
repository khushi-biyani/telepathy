"""Telepathy API (FastAPI + server-sent events).

    POST /run                 {question, mode, topology, latent_steps} -> {run_id, recorded, ...}
    POST /race                {question, latent_steps}  -> a text run and a latent run for one question
    GET  /runs/{id}           status
    GET  /runs/{id}/events    SSE stream of events
    GET  /recordings          what can be replayed
    GET  /benchmarks          latest benchmark summaries

Default is replay mode (REPLAY=1): the nearest recording is served with its original timing and every
event is marked recorded=true, so the dashboard shows a 'Recorded run' badge. Live mode (REPLAY=0)
runs the local GPU engine; it needs the model. TF_LIVE=1 additionally lets replay-mode text runs go
to Token Factory (costs money, guarded by the budget brakes in llm.py).
"""
from __future__ import annotations

import asyncio
import json
import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from telepathy import events as ev

ROOT = Path(__file__).resolve().parent.parent


@dataclass
class Settings:
    replay: bool = os.environ.get("REPLAY", "1") == "1"
    replay_speed: float = float(os.environ.get("REPLAY_SPEED", "1"))
    recordings: Path = Path(os.environ.get("RECORDINGS", ROOT / "server" / "recordings"))
    results: Path = ROOT / "bench" / "results"
    tf_live: bool = os.environ.get("TF_LIVE", "0") == "1"
    min_match: float = 0.0  # below this similarity we still serve the nearest recording, but say so
    # Limits on LIVE Nebius questions, so a public page can never drain the credits. Past any of them the
    # visitor gets a recorded run and a short reason.
    demo_budget_usd: float = float(os.environ.get("DEMO_BUDGET_USD", "3.0"))        # most the page may spend in total
    live_usd_per_run: float = float(os.environ.get("LIVE_USD_PER_RUN", "0.03"))     # most one question may cost
    live_per_ip_per_hour: int = int(os.environ.get("LIVE_PER_IP_PER_HOUR", "6"))
    live_max_concurrent: int = int(os.environ.get("LIVE_MAX_CONCURRENT", "3"))
    max_question_chars: int = int(os.environ.get("MAX_QUESTION_CHARS", "500"))
    gallery_live: Path = Path(os.environ.get("GALLERY_LIVE", ROOT / "server" / "gallery_live.json"))  # the only questions /live will run


@dataclass
class Run:
    id: str
    recorded: bool
    meta: dict = field(default_factory=dict)
    events: list = field(default_factory=list)
    done: bool = False
    error: str | None = None

    def push(self, e: dict):
        self.events.append({**e, "recorded": self.recorded})


class RunRequest(BaseModel):
    question: str
    mode: str = "auto"
    topology: str = "sequential"
    latent_steps: int = 10


class LiveRequest(BaseModel):
    item: str  # an id from the demo gallery. Free text is never accepted here.


class RaceRequest(BaseModel):
    question: str
    latent_steps: int = 10
    topology: str = "sequential"


def create_app(settings: Settings | None = None, engine_factory=None, tf_runner=None, item_runner=None) -> FastAPI:
    cfg = settings or Settings()
    app = FastAPI(title="Telepathy")
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
    runs: dict[str, Run] = {}
    lim = {"spent": 0.0, "active": 0, "hits": {}}
    lim_lock = threading.Lock()
    worker = ThreadPoolExecutor(max_workers=1)  # one GPU: runs are serial, so timings stay fair
    worker_live = ThreadPoolExecutor(max_workers=max(1, cfg.live_max_concurrent))

    def get_team(req: RunRequest):
        from telepathy import TelepathyTeam
        factory = engine_factory or (lambda r: TelepathyTeam(r.topology, r.mode, r.latent_steps))
        return factory(req)

    def start_replay(run: Run, path: Path):
        def work():
            try:
                for e in ev.replay(ev.load(path), speed=cfg.replay_speed):
                    run.push(e)
            except Exception as err:  # noqa: BLE001
                run.error = str(err)
            run.done = True
        threading.Thread(target=work, daemon=True).start()

    def start_live(run: Run, req: RunRequest):
        def work():
            try:
                team = get_team(req)
                rec = ev.Recorder(cfg.recordings / f"live_{run.id}.jsonl")
                rec.add_sink(run.push)
                team.on_event = rec
                team.run(req.question)
            except Exception as err:  # noqa: BLE001
                run.error = str(err)
            run.done = True
        worker.submit(work)

    def allow_live(ip: str, question: str) -> str | None:
        """None if a live Nebius question is allowed (and counts it), else a short reason."""
        with lim_lock:
            if len(question) > cfg.max_question_chars:
                return f"questions are limited to {cfg.max_question_chars} characters"
            if lim["active"] >= cfg.live_max_concurrent:
                return "the live demo is busy"
            now = time.time()
            recent = [t for t in lim["hits"].get(ip, []) if now - t < 3600]
            if len(recent) >= cfg.live_per_ip_per_hour:
                return f"you have used your {cfg.live_per_ip_per_hour} live questions for this hour"
            if lim["spent"] + cfg.live_usd_per_run > cfg.demo_budget_usd:
                return "the live demo's spending limit has been reached"
            lim["hits"][ip] = recent + [now]
            lim["active"] += 1
        return None

    def start_tf(run: Run, req: RunRequest):
        def work():
            cost = cfg.live_usd_per_run  # if it fails midway, count the most it could have cost
            try:
                cost = tf_runner(req, run.push) or 0.0
            except Exception as err:  # noqa: BLE001
                run.error = str(err)
            finally:
                with lim_lock:
                    lim["active"] -= 1
                    lim["spent"] += cost
            run.done = True
        worker_live.submit(work)

    def start_item(run: Run, item: dict):
        def work():
            cost = cfg.live_usd_per_run
            try:
                cost = item_runner(item, run.push) or 0.0
            except Exception as err:  # noqa: BLE001
                run.error = str(err)
            finally:
                with lim_lock:
                    lim["active"] -= 1
                    lim["spent"] += cost
            run.done = True
        worker_live.submit(work)

    def launch(req: RunRequest, ip: str = "unknown") -> Run:
        denied = None
        if cfg.replay and req.mode == "text" and cfg.tf_live and tf_runner:
            denied = allow_live(ip, req.question)
            if denied is None:
                run = Run(uuid.uuid4().hex[:10], recorded=False, meta={"source": "token_factory_live"})
                runs[run.id] = run
                start_tf(run, req)
                return run
        if cfg.replay:
            path, score = ev.nearest(cfg.recordings, req.question, req.mode, req.topology)
            if path is None:
                have = [ev.describe(p) for p in sorted(cfg.recordings.glob("*.jsonl"))]
                raise HTTPException(404, {"error": "no recording for this mode/topology",
                                          "available": [h for h in have if h]})
            d = ev.describe(path)
            run = Run(uuid.uuid4().hex[:10], recorded=True,
                      meta={"source": "recording", "file": path.name, "matched_question": d["question"],
                            "similarity": round(score, 3), "exact": score >= 0.999})
            if denied:
                run.meta["live_denied"] = denied
            runs[run.id] = run
            start_replay(run, path)
            return run
        run = Run(uuid.uuid4().hex[:10], recorded=False, meta={"source": "live_gpu"})
        runs[run.id] = run
        start_live(run, req)
        return run

    @app.get("/health")
    def health():
        return {"ok": True, "replay": cfg.replay, "tf_live": cfg.tf_live,
                "live": {"spent_usd": round(lim["spent"], 4), "budget_usd": cfg.demo_budget_usd, "active": lim["active"]}}

    @app.post("/run")
    def post_run(req: RunRequest, request: Request):
        r = launch(req, request.client.host if request.client else "unknown")
        return {"run_id": r.id, "recorded": r.recorded, **r.meta}

    @app.post("/live")
    def post_live(req: LiveRequest, request: Request):
        """Run the usual team live on Nebius for one question from the demo gallery. Same brakes as everything live."""
        if not (cfg.tf_live and item_runner):
            raise HTTPException(503, "live Nebius runs are switched off on this server")
        items = {i["id"]: i for i in json.loads(cfg.gallery_live.read_text())} if cfg.gallery_live.exists() else {}
        item = items.get(req.item)
        if item is None:
            raise HTTPException(404, "that question is not in the gallery")
        denied = allow_live(request.client.host if request.client else "unknown", "")  # gallery text is ours, so no length check
        if denied:
            raise HTTPException(429, denied)
        run = Run(uuid.uuid4().hex[:10], recorded=False, meta={"source": "token_factory_live", "item": req.item})
        runs[run.id] = run
        start_item(run, item)
        return {"run_id": run.id, "recorded": False, **run.meta}

    @app.post("/race")
    def post_race(req: RaceRequest, request: Request):
        ip = request.client.host if request.client else "unknown"
        a = launch(RunRequest(question=req.question, mode="text", topology=req.topology), ip)
        b = launch(RunRequest(question=req.question, mode="auto", topology=req.topology,
                              latent_steps=req.latent_steps))
        return {"text": {"run_id": a.id, "recorded": a.recorded, **a.meta},
                "latent": {"run_id": b.id, "recorded": b.recorded, **b.meta}}

    @app.get("/runs/{run_id}")
    def get_run(run_id: str):
        r = runs.get(run_id)
        if not r:
            raise HTTPException(404, "unknown run")
        return {"run_id": r.id, "recorded": r.recorded, "done": r.done, "error": r.error,
                "events": len(r.events), **r.meta}

    @app.get("/runs/{run_id}/events")
    async def get_events(run_id: str):
        r = runs.get(run_id)
        if not r:
            raise HTTPException(404, "unknown run")

        async def stream():
            i = 0
            while True:
                while i < len(r.events):
                    yield f"data: {json.dumps(r.events[i])}\n\n"
                    i += 1
                if r.done and i >= len(r.events):
                    yield f"event: end\ndata: {json.dumps({'error': r.error})}\n\n"
                    return
                await asyncio.sleep(0.03)
        return StreamingResponse(stream(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    @app.get("/recordings")
    def recordings():
        return [d for d in (ev.describe(p) for p in sorted(cfg.recordings.glob("*.jsonl"))) if d]

    @app.get("/benchmarks")
    def benchmarks():
        from bench import metrics as M
        from bench.teamsize import by_size
        out = {"modes": {}, "honesty": {}, "notes": None, "team_sizes": {str(n): v for n, v in by_size(cfg.results / "test").items()}}
        for f in sorted(cfg.results.rglob("*.jsonl")):
            key = f"{f.parent.name}/{f.stem}"
            if "tokenfactory" in f.name:
                continue  # different measurements (tokens read and written); reported under team_sizes
            if "honesty" in f.name:
                out["honesty"][key] = M.honesty_summary(M.read(f))
            else:
                out["modes"][key] = M.summarize(M.read(f))
        gate = cfg.results / "gate_summary.md"
        out["notes"] = gate.read_text() if gate.exists() else None
        return out

    return app


def make_tf_runner(cfg: Settings):
    def run(req, push) -> float:
        from telepathy.baseline_tf import stream_text_team
        _, cost = stream_text_team(req.question, push, req.topology, max_usd=cfg.live_usd_per_run)
        return cost
    return run


def make_item_runner(cfg: Settings):
    """Runs one gallery question as the usual team on Token Factory, with the right instructions for its kind."""
    def run(item: dict, push) -> float:
        from telepathy.baseline_tf import stream_text_team
        kind = item["kind"]
        context = "\n".join(f"{p['title']}: {p['content']}" for p in item.get("pages", []))
        _, cost = stream_text_team(item["question"], push, "research" if kind == "research" else "sequential", context=context,
                                   max_usd=cfg.live_usd_per_run, task=item.get("task") or (kind if kind in ("logic", "code", "science") else "math"),
                                   max_tokens=900)
        return cost
    return run


_cfg = Settings()
app = create_app(_cfg, tf_runner=make_tf_runner(_cfg), item_runner=make_item_runner(_cfg))
