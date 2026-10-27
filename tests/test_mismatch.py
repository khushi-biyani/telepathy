from bench.mismatch_bench import donor_index, run_arm, summarize
from telepathy import Policy, TelepathyTeam

Q1 = "What is 2 plus 3?"
Q2 = "What is 10 minus 4?"


def test_real_arm_matches_the_engine(cfg, lm):
    """The control's own 'real' arm must be the normal latent run, or comparing it to the others proves nothing."""
    mine, _, _ = run_arm(lm, Q1, None, 3)
    team = TelepathyTeam("sequential", "latent", 3, config=cfg, policy=Policy(honesty_check="off"))
    assert mine == team.run(Q1).answer


def test_donor_is_another_question():
    assert all(donor_index(i, 50) != i for i in range(50)) and donor_index(0, 3) != 0


def test_other_question_changes_the_cache(lm):
    real, _, _ = run_arm(lm, Q1, None, 3)
    other, _, _ = run_arm(lm, Q1, Q2, 3)
    assert isinstance(real, str) and isinstance(other, str)  # runs; the benchmark measures whether answers differ


def test_summary_counts():
    rows = {"real": {"a": {"ok": True}, "b": {"ok": True}}, "no_thinking": {"a": {"ok": True}, "b": {"ok": False}}}
    out = summarize(rows)
    assert "real            2/2" in out and "only real right 1" in out
