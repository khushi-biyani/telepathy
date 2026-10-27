import random

import pytest
import torch

from telepathy import Policy, TelepathyTeam
from telepathy import honesty, policy as P
from telepathy.cache_utils import length
from telepathy.subtitles import subtitle
from telepathy.latent import think

Q = "A pen costs 12 rupees. Asha buys 7 pens. How much does she pay?"


# ---- test 6: policy table
def test_policy_plan_and_decide():
    roles = ["planner", "critic", "refiner"]
    assert P.make_plan(Policy(honesty_check="off"), roles, random.Random(0)).audited == set()
    assert P.make_plan(Policy(honesty_check="always"), roles, random.Random(0)).audited == {0, 1, 2}
    hs = P.make_plan(Policy(honesty_check="always", high_stakes_roles=["critic"]), roles, random.Random(0))
    assert hs.forced_text == {1} and hs.audited == {0, 2}  # a high-stakes handoff is never audited as latent
    s = P.make_plan(Policy(honesty_check="sample", sample_rate=0.0), roles, random.Random(0))
    assert s.audited == set()
    assert P.decide(Policy(), True, 0) == "ok"
    assert P.decide(Policy(), False, 0) == "switch_to_text"
    assert P.decide(Policy(max_text_fallbacks=1), False, 1) == "flag"
    assert P.decide(Policy(on_unfaithful="flag_only"), False, 0) == "flag"


# ---- subtitles
def test_turn_suffix_is_a_user_turn(lm):
    text = lm.tok.decode(lm.turn_suffix_ids("SAY HI")[0])
    assert "SAY HI" in text and "\u00a7" not in text


def test_subtitle_does_not_touch_the_cache(lm):
    ids = lm.prompt_ids("planner", Q)
    past = think(lm.model, ids, None, 2, lm.target_norm)
    n0 = length(past)
    key0 = past.layers[0].keys.clone()
    sub = subtitle(lm, past, max_new=8)
    assert isinstance(sub, str)
    assert length(past) == n0 and torch.equal(past.layers[0].keys, key0)


# ---- test 3: same final answer with and without subtitles
def test_subtitles_do_not_change_the_answer(cfg):
    a = TelepathyTeam("sequential", "latent", latent_steps=2, config=cfg, subtitles=False).run(Q)
    b = TelepathyTeam("sequential", "latent", latent_steps=2, config=cfg, subtitles=True).run(Q)
    assert a.answer == b.answer
    assert all(h.subtitle is not None for h in b.handoffs) and all(h.subtitle is None for h in a.handoffs)


# ---- honesty math + logic (test 4)
def test_js_divergence():
    p = torch.tensor([1.0, 0.0])
    q = torch.tensor([0.0, 1.0])
    assert honesty.js_divergence(p, p) == pytest.approx(0.0, abs=1e-6)
    assert honesty.js_divergence(p, q) == pytest.approx(1.0, abs=1e-6)


def test_corrupt_changes_a_number_or_declines():
    assert honesty.corrupt("Total is 84 rupees") == "Total is 91 rupees"
    assert honesty.corrupt("no digits") is None


def test_check_logic_with_stubbed_replay(cfg, monkeypatch):
    team = TelepathyTeam("sequential", "auto", latent_steps=1, config=cfg,
                         policy=Policy(honesty_check="always"))
    state = team.run(Q).state
    # replay identical by construction -> faithful; different final answer -> unfaithful
    monkeypatch.setattr(team, "_run_from", lambda *a, **k: (state.answer, state.first_probs, 0))
    res = honesty.check(team, state, 0)
    assert res.faithful and res.js == pytest.approx(0.0, abs=1e-6)
    monkeypatch.setattr(team, "_run_from", lambda *a, **k: (r"\boxed{999999}", state.first_probs, 0))
    assert honesty.check(team, state, 0).faithful is False


def test_check_runs_for_real_and_controls_return(cfg):
    team = TelepathyTeam("sequential", "auto", latent_steps=1, config=cfg,
                         policy=Policy(honesty_check="always", on_unfaithful="flag_only"))
    r = team.run(Q)
    assert all(h.faithful is not None and 0.0 <= h.js <= 1.0 for h in r.handoffs)
    c = honesty.controls(team, r.state, 0, other_subs={0: "Total is 5 rupees"})
    assert set(c) == {"shuffled", "corrupted", "empty", "shuffled_gap", "corrupted_gap", "empty_gap"}


# ---- auto mode fallback
def test_auto_switches_to_text_when_unfaithful(cfg, monkeypatch):
    events = []
    team = TelepathyTeam("sequential", "auto", latent_steps=1, config=cfg, on_event=events.append,
                         policy=Policy(honesty_check="always", max_text_fallbacks=2))
    monkeypatch.setattr(honesty, "check", lambda *a, **k: honesty.CheckResult(False, 0.9, "x", 1.0))
    r = team.run(Q)
    assert r.metrics["fallbacks"] == 2 and [h.mode_used for h in r.handoffs].count("text") == 2
    kinds = [e["type"] for e in events]
    assert kinds.count("fallback") == 2 and "honesty" in kinds and kinds[-2:] == ["final", "run_finished"]


def test_high_stakes_role_is_written_in_english(cfg):
    r = TelepathyTeam("sequential", "auto", latent_steps=1, config=cfg,
                      policy=Policy(honesty_check="off", high_stakes_roles=["critic"])).run(Q)
    assert [h.mode_used for h in r.handoffs] == ["latent", "text", "latent"]


# ---- teacher-forced scoring and the strict variant
def test_score_matches_the_decode_logprobs(lm):
    from telepathy.cache_utils import fork
    ids = lm.prompt_ids("planner", Q)
    past = think(lm.model, ids, None, 1, lm.target_norm)
    final = lm.prompt_ids("solver", Q, first=False)
    _, _, _ = lm.decode(final, fork(past), max_new=6)
    ans, lps = list(lm.last_ids), list(lm.last_logps)
    assert len(ans) == len(lps) > 0
    assert lm.score(final, fork(past), ans) == pytest.approx(sum(lps) / len(lps), abs=1e-3)


def test_check_reports_a_gap_and_strict_variant_runs(cfg):
    team = TelepathyTeam("sequential", "auto", latent_steps=1, config=cfg,
                         policy=Policy(honesty_check="always", on_unfaithful="flag_only"))
    st = team.run(Q).state
    assert st.answer_ids and st.answer_lp is not None
    res = honesty.check(team, st, 0)
    assert res.gap is not None
    strict = honesty.check(team, st, 0, hide_question=True)
    assert strict.gap is not None and strict.gap != res.gap
    c = honesty.controls(team, st, 0, {0: "Total is 5 rupees"}, hide_question=True)
    assert c["shuffled_gap"] is not None


def test_rich_subtitles_and_the_empty_control(cfg):
    from telepathy import subtitles
    assert "numbers" in subtitles.INSTRUCTION_RICH and subtitles.INSTRUCTION_RICH != subtitles.INSTRUCTION
    plain = TelepathyTeam("sequential", "latent", latent_steps=1, config=cfg, subtitles=True).run(Q)
    rich = TelepathyTeam("sequential", "latent", latent_steps=1, config=cfg, subtitles=True,
                         subtitle_style="rich").run(Q)
    assert plain.answer == rich.answer                       # the style never changes the real run
    team = TelepathyTeam("sequential", "auto", latent_steps=1, config=cfg,
                         policy=Policy(honesty_check="always", on_unfaithful="flag_only"))
    st = team.run(Q).state
    c = honesty.controls(team, st, 1, {})
    assert c["empty_gap"] is not None
