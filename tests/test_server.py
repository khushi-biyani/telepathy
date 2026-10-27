import json
import time

import pytest
from fastapi.testclient import TestClient

from server.app import Settings, create_app
from telepathy import events as ev


def fake_run(path, question, mode):
    """A scripted event sequence recorded through the real Recorder."""
    rec = ev.Recorder(path)
    rec({"type": "run_started", "mode": mode, "topology": "sequential", "question": question,
         "roles": ["planner", "solver"]})
    rec({"type": "agent_started", "role": "planner"})
    rec({"type": "handoff", "from": "planner", "to": "solver", "handoff": 0, "mode_used": mode})
    rec({"type": "token", "role": "solver", "text": "42"})
    rec({"type": "final", "answer": "42", "metrics": {"seconds": 1.0, "tokens_written": 5}})
    rec({"type": "run_finished"})
    return rec.events


# ---- test 7: record then replay gives the same event sequence
def test_record_then_replay_same_sequence(tmp_path):
    p = tmp_path / "a.jsonl"
    original = fake_run(p, "How many pens?", "auto")
    assert ev.load(p) == original
    assert list(ev.replay(ev.load(p), sleep=lambda s: None)) == original


def test_replay_keeps_original_timing(tmp_path):
    slept = []
    events = [{"type": "a", "t": 0.0}, {"type": "b", "t": 0.5}, {"type": "c", "t": 2.0}]
    list(ev.replay(events, speed=2.0, sleep=slept.append))
    assert slept == [0.25, 0.75]


def test_nearest_picks_closest_question_and_mode(tmp_path):
    fake_run(tmp_path / "1.jsonl", "A shop sells pens at 12 rupees", "auto")
    fake_run(tmp_path / "2.jsonl", "A train travels 60 km per hour", "auto")
    fake_run(tmp_path / "3.jsonl", "A train travels 60 km per hour", "text")
    path, score = ev.nearest(tmp_path, "how far does a train travel at 60 km per hour", mode="auto")
    assert path.name == "2.jsonl" and score > 0.3
    assert ev.nearest(tmp_path, "anything", mode="single")[0] is None


# ---- API
@pytest.fixture
def client(tmp_path):
    fake_run(tmp_path / "pens__auto.jsonl", "A shop sells pens at 12 rupees", "auto")
    fake_run(tmp_path / "pens__text.jsonl", "A shop sells pens at 12 rupees", "text")
    cfg = Settings(replay=True, replay_speed=1000.0, recordings=tmp_path, results=tmp_path / "results")
    return TestClient(create_app(cfg))


def read_sse(client, run_id):
    events, ended = [], False
    with client.stream("GET", f"/runs/{run_id}/events") as r:
        for line in r.iter_lines():
            if line.startswith("event: end"):
                ended = True
            elif line.startswith("data: ") and not ended:
                events.append(json.loads(line[6:]))
    return events


def test_run_streams_recorded_events_with_badge(client):
    r = client.post("/run", json={"question": "pens at 12 rupees", "mode": "auto"}).json()
    assert r["recorded"] is True and r["file"] == "pens__auto.jsonl"
    events = read_sse(client, r["run_id"])
    assert [e["type"] for e in events] == ["run_started", "agent_started", "handoff", "token", "final",
                                           "run_finished"]
    assert all(e["recorded"] for e in events)
    assert client.get(f"/runs/{r['run_id']}").json()["done"] is True


def test_race_starts_two_lanes(client):
    r = client.post("/race", json={"question": "pens at 12 rupees"}).json()
    assert r["text"]["run_id"] != r["latent"]["run_id"]
    assert read_sse(client, r["text"]["run_id"])[0]["mode"] == "text"
    assert read_sse(client, r["latent"]["run_id"])[0]["mode"] == "auto"


def test_unknown_mode_lists_what_exists(client):
    r = client.post("/run", json={"question": "x", "mode": "single"})
    assert r.status_code == 404 and len(r.json()["detail"]["available"]) == 2
    assert client.get("/runs/nope").status_code == 404


def test_recordings_and_benchmarks(client, tmp_path):
    assert len(client.get("/recordings").json()) == 2
    (tmp_path / "results").mkdir()
    (tmp_path / "results" / "x_text.jsonl").write_text(
        json.dumps({"id": "q", "ok": True, "seconds": 2.0, "tokens_written": 10, "latent_steps": 0}) + "\n")
    b = client.get("/benchmarks").json()
    assert b["modes"]["results/x_text"]["accuracy"] == 1.0


# ---- live mode with a fake engine (no model)
def test_live_mode_uses_engine_and_records(tmp_path):
    class FakeTeam:
        on_event = None

        def run(self, question):
            for e in ({"type": "run_started", "mode": "auto", "topology": "sequential", "question": question},
                      {"type": "final", "answer": "7", "metrics": {}}, {"type": "run_finished"}):
                self.on_event(e)

    cfg = Settings(replay=False, recordings=tmp_path, results=tmp_path)
    c = TestClient(create_app(cfg, engine_factory=lambda req: FakeTeam()))
    r = c.post("/run", json={"question": "q?", "mode": "auto"}).json()
    assert r["recorded"] is False
    events = read_sse(c, r["run_id"])
    assert events[-1]["type"] == "run_finished" and not any(e["recorded"] for e in events)
    assert len(list(tmp_path.glob("live_*.jsonl"))) == 1


# ---- Token Factory live text lane (mocked)
def test_stream_text_team_events(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from telepathy import baseline_tf, llm as L

    class C:
        def __init__(self):
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

        def create(self, **kw):
            msg = SimpleNamespace(content="answer 5")
            return SimpleNamespace(choices=[SimpleNamespace(message=msg, finish_reason="stop")],
                                   usage=SimpleNamespace(prompt_tokens=10, completion_tokens=4))

    monkeypatch.setattr(L, "_get_client", lambda: C())
    monkeypatch.setattr(L, "LEDGER", L.Ledger(tmp_path / "s.json"))
    monkeypatch.setattr(L, "CACHE_DIR", tmp_path / "c")
    got = []
    baseline_tf.stream_text_team("q?", got.append)
    kinds = [e["type"] for e in got]
    assert kinds[0] == "run_started" and kinds[-2:] == ["final", "run_finished"]
    assert kinds.count("handoff") == 3 and kinds.count("token") == 4
    assert got[-2]["metrics"]["tokens_out"] == 16


# ---- live Nebius lane and its limits (the runner is faked: no network, no money)
def live_client(tmp_path, runner, **kw):
    fake_run(tmp_path / "pens__text.jsonl", "A shop sells pens at 12 rupees", "text")
    fake_run(tmp_path / "pens__auto.jsonl", "A shop sells pens at 12 rupees", "auto")
    cfg = Settings(replay=True, replay_speed=1000.0, recordings=tmp_path, results=tmp_path / "results", tf_live=True, **kw)
    return TestClient(create_app(cfg, tf_runner=runner)), cfg


def good_runner(req, push):
    push({"type": "run_started", "mode": "text", "topology": "sequential", "question": req.question, "provider": "nebius_token_factory", "live": True})
    push({"type": "final", "answer": "42", "metrics": {"seconds": 1.0, "tokens_in": 100, "tokens_out": 50, "cost_usd": 0.002}})
    push({"type": "run_finished"})
    return 0.002


def race(c, q="pens at 12 rupees"):
    return c.post("/race", json={"question": q}).json()


def test_live_lane_runs_on_nebius_and_the_other_lane_is_a_recording(tmp_path):
    c, _ = live_client(tmp_path, good_runner)
    r = race(c)
    assert r["text"]["source"] == "token_factory_live" and r["text"]["recorded"] is False
    assert r["latent"]["recorded"] is True and "live_denied" not in r["text"]
    events = read_sse(c, r["text"]["run_id"])
    assert events[0]["provider"] == "nebius_token_factory" and not any(e["recorded"] for e in events)
    assert c.get("/health").json()["live"]["spent_usd"] == pytest.approx(0.002)


def test_a_visitor_gets_only_a_few_live_questions_an_hour(tmp_path):
    c, _ = live_client(tmp_path, good_runner, live_per_ip_per_hour=2)
    assert race(c)["text"]["source"] == "token_factory_live"
    assert race(c)["text"]["source"] == "token_factory_live"
    third = race(c)["text"]
    assert third["recorded"] is True and "questions for this hour" in third["live_denied"]


def wait_done(c, run_id):
    for _ in range(100):
        if c.get(f"/runs/{run_id}").json()["done"]:
            return
        time.sleep(0.05)
    raise AssertionError("run did not finish")


def test_spending_limit_stops_live_questions(tmp_path):
    def costly(req, push):
        good_runner(req, push)
        return 0.03                                   # this question really cost 3 cents
    c, _ = live_client(tmp_path, costly, demo_budget_usd=0.05, live_usd_per_run=0.03, live_per_ip_per_hour=99)
    first = race(c)["text"]
    assert first["source"] == "token_factory_live"   # 0.00 + 0.03 fits in 0.05
    wait_done(c, first["run_id"])
    second = race(c)["text"]                          # 0.03 spent, and another 0.03 would pass 0.05
    assert second["recorded"] is True and "spending limit" in second["live_denied"]
    assert c.get("/health").json()["live"]["spent_usd"] == pytest.approx(0.03)


def test_overlong_questions_and_busy_demo_fall_back_to_a_recording(tmp_path):
    c, _ = live_client(tmp_path, good_runner, max_question_chars=40)
    d = race(c, "pens at 12 rupees " * 5)["text"]
    assert d["recorded"] is True and "limited to 40 characters" in d["live_denied"]

    import threading
    gate = threading.Event()

    def slow(req, push):
        gate.wait(5)
        return 0.0
    c, _ = live_client(tmp_path, slow, live_max_concurrent=1, live_per_ip_per_hour=99)
    assert race(c)["text"]["source"] == "token_factory_live"
    busy = race(c)["text"]
    assert busy["recorded"] is True and "busy" in busy["live_denied"]
    gate.set()


def test_a_failed_live_run_still_counts_against_the_budget(tmp_path):
    def broken(req, push):
        raise RuntimeError("nebius down")
    c, cfg = live_client(tmp_path, broken)
    r = race(c)
    events_done = None
    for _ in range(50):
        if c.get(f"/runs/{r['text']['run_id']}").json()["done"]:
            events_done = True
            break
        time.sleep(0.05)
    assert events_done and c.get(f"/runs/{r['text']['run_id']}").json()["error"] == "nebius down"
    assert c.get("/health").json()["live"]["spent_usd"] == pytest.approx(cfg.live_usd_per_run)


# ---- /live: only gallery questions, never free text
def item_client(tmp_path, runner, tf_live=True, **kw):
    gal = tmp_path / "gal.json"
    gal.write_text(json.dumps([{"id": "pets", "kind": "logic", "question": "Q" * 700},
                               {"id": "pens", "kind": "research", "question": "pens?", "pages": [{"title": "t", "content": "c"}]}]))
    cfg = Settings(replay=True, replay_speed=1000.0, recordings=tmp_path, results=tmp_path / "results", tf_live=tf_live, gallery_live=gal, **kw)
    return TestClient(create_app(cfg, item_runner=runner)), cfg


def item_runner_ok(item, push):
    push({"type": "run_started", "mode": "text", "topology": "sequential", "question": item["question"], "provider": "nebius_token_factory", "live": True})
    push({"type": "final", "answer": "ok", "metrics": {"seconds": 1.0, "tokens_in": 1, "tokens_out": 1, "cost_usd": 0.002}})
    push({"type": "run_finished"})
    return 0.002


def test_live_runs_a_gallery_question_even_if_it_is_long(tmp_path):
    c, _ = item_client(tmp_path, item_runner_ok)
    r = c.post("/live", json={"item": "pets"})
    assert r.status_code == 200 and r.json()["source"] == "token_factory_live"
    assert read_sse(c, r.json()["run_id"])[0]["question"] == "Q" * 700


def test_live_refuses_anything_not_in_the_gallery_and_when_switched_off(tmp_path):
    c, _ = item_client(tmp_path, item_runner_ok)
    assert c.post("/live", json={"item": "ignore previous instructions"}).status_code == 404
    assert c.post("/live", json={"question": "free text"}).status_code == 422   # the field does not exist
    off, _ = item_client(tmp_path, item_runner_ok, tf_live=False)
    assert off.post("/live", json={"item": "pets"}).status_code == 503


def test_live_obeys_the_same_limits(tmp_path):
    c, _ = item_client(tmp_path, item_runner_ok, live_per_ip_per_hour=1)
    assert c.post("/live", json={"item": "pets"}).status_code == 200
    second = c.post("/live", json={"item": "pens"})
    assert second.status_code == 429 and "this hour" in second.json()["detail"]


def test_live_roles_follow_the_kind():
    from telepathy.baseline_tf import _messages
    assert "boxed" in _messages("solver", "q", "", "", "logic")[1]["content"]
    assert "boxed" in _messages("solver", "q", "", "")[1]["content"]  # math default unchanged
