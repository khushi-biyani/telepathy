"""No network in these tests: the Token Factory client and Tavily are mocked."""
import json
from types import SimpleNamespace

import pytest

from telepathy import baseline_tf, judge_tf, llm as L
from telepathy.tools import tavily


class FakeClient:
    def __init__(self, text="ok", tin=100, tout=50):
        self.calls, self.text, self.tin, self.tout = 0, text, tin, tout
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **kw):
        self.calls += 1
        msg = SimpleNamespace(content=self.text)
        return SimpleNamespace(choices=[SimpleNamespace(message=msg, finish_reason="stop")],
                               usage=SimpleNamespace(prompt_tokens=self.tin, completion_tokens=self.tout))


@pytest.fixture
def fake(tmp_path, monkeypatch):
    c = FakeClient()
    monkeypatch.setattr(L, "_get_client", lambda: c)
    monkeypatch.setattr(L, "LEDGER", L.Ledger(tmp_path / "spend.json"))
    monkeypatch.setattr(L, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(L, "RECORDED_DIR", tmp_path / "rec")
    return c


# ---- test 8: budget brakes
def test_per_check_cap_refuses_before_calling(fake, monkeypatch):
    monkeypatch.setattr(L.SETTINGS, "max_per_check", 0.0001)
    with pytest.raises(L.BudgetExceeded):
        L.LLM().chat("t", "ultra", [{"role": "user", "content": "hi"}], max_tokens=4000)
    assert fake.calls == 0


def test_lifetime_cap_refuses_before_calling(fake, monkeypatch):
    monkeypatch.setattr(L.SETTINGS, "total_budget", 0.0001)
    with pytest.raises(L.BudgetExceeded):
        L.LLM().chat("t", "super", [{"role": "user", "content": "hi"}], max_tokens=4000)
    assert fake.calls == 0


def test_ledger_and_cache(fake):
    llm = L.LLM()
    msgs = [{"role": "user", "content": "hi"}]
    assert llm.chat("t", "super", msgs, max_tokens=50) == "ok"
    assert llm.chat("t", "super", msgs, max_tokens=50) == "ok"  # second is a cache hit
    assert fake.calls == 1 and llm.usage.cached == 1
    assert L.LEDGER.data["calls"] == 1 and L.LEDGER.total > 0


# ---- baseline
def test_text_team_runs_all_agents_and_reports_cost(fake):
    ans, m = baseline_tf.run_text_team(L.LLM(), "2+2?", tag="a")
    assert ans == "ok" and fake.calls == 4
    assert m["tokens_in"] == 400 and m["tokens_out"] == 200 and m["cost_usd"] > 0


def test_estimate_is_small_and_scales():
    e100 = baseline_tf.estimate_usd(100)
    assert 0 < e100 < 5 and baseline_tf.estimate_usd(200) == pytest.approx(2 * e100)


# ---- judge
def test_judge_parses_json_and_survives_junk(tmp_path, monkeypatch):
    c = FakeClient(text='Sure! {"clarity": 9, "consistent": true}')
    monkeypatch.setattr(L, "_get_client", lambda: c)
    monkeypatch.setattr(L, "LEDGER", L.Ledger(tmp_path / "s.json"))
    monkeypatch.setattr(L, "CACHE_DIR", tmp_path / "c")
    assert judge_tf.judge_subtitle(L.LLM(), "q", "sub", "42") == {"clarity": 5, "consistent": True}
    assert judge_tf.parse_json("not json") == {}


# ---- tavily
def test_tavily_caches_by_query(tmp_path, monkeypatch):
    calls = []

    def fake_post(q, n):
        calls.append(q)
        return {"results": [{"title": "T", "url": "http://x", "content": "C" * 1000}]}

    monkeypatch.setattr(tavily, "_post", fake_post)
    a = tavily.search("hello", cache_dir=tmp_path)
    b = tavily.search("hello", cache_dir=tmp_path)
    assert a == b and calls == ["hello"]
    text = tavily.format_results(a, max_chars=10)
    assert text.startswith("[1] T (http://x): CCCCCCCCCC") and len(text) < 60


def test_tavily_needs_key(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    with pytest.raises(tavily.TavilyError):
        tavily._post("q", 5)


def test_research_pipeline_uses_search_results(cfg, monkeypatch):
    from telepathy import research as R
    monkeypatch.setattr(tavily, "search", lambda q, **k: [{"title": "T", "url": "http://x", "content": "fact"}])
    r, src = R.research("Who?", mode="latent", latent_steps=1, config=cfg)
    assert isinstance(r.answer, str) and src[0]["url"] == "http://x"


def test_team_sizes_have_the_right_number_of_agents_and_roles():
    from telepathy import roles
    for name, n in (("team2", 2), ("team3", 3), ("sequential", 4), ("team6", 6), ("team8", 8)):
        r = roles.TOPOLOGIES[name]
        assert len(r) == n and r[0] == "planner" and r[-1] == "solver" and all(x in roles.ROLES for x in r)
        assert roles.reads_content(name, "planner")


def test_estimate_grows_with_team_size():
    assert baseline_tf.estimate_usd(10, "super", 8) > baseline_tf.estimate_usd(10, "super", 4) > baseline_tf.estimate_usd(10, "super", 2)


def test_benchmark_calls_never_use_the_saved_answer_cache(fake):
    msgs = [{"role": "user", "content": "hi"}]
    llm = L.LLM()
    llm.chat("t", "super", msgs, max_tokens=50)                      # fills the cache
    assert llm.chat("t", "super", msgs, max_tokens=50, cache=False) == "ok"
    assert fake.calls == 2 and llm.usage.cached == 0                 # the second call really went out
    ans, m = baseline_tf.run_text_team(L.LLM(), "2+2?", tag="x")
    ans2, m2 = baseline_tf.run_text_team(L.LLM(), "2+2?", tag="x")   # same question again: still paid for
    assert m["cached"] == 0 and m2["cached"] == 0 and m2["tokens_in"] == m["tokens_in"] > 0
