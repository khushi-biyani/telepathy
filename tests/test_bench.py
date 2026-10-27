import pytest
import json

from bench import metrics
from bench.datasets import grade
from bench.run_bench import done_ids, result_path
from telepathy.answers import extract_choice


def test_grade_number_and_choice():
    assert grade({"kind": "number", "gold": "1260"}, r"\boxed{1,260}") == ("1260", True)
    assert grade({"kind": "choice", "gold": "B"}, r"so \boxed{B}") == ("B", True)
    assert grade({"kind": "choice", "gold": "B"}, "I think C") == ("C", False)
    assert extract_choice("no letters here at all, 12") is None


def test_resume_and_summary(tmp_path):
    p = result_path(tmp_path, "gsm8k", "dev", "latent", 5)
    assert p.name == "gsm8k_dev_latent_s5.jsonl"
    assert result_path(tmp_path, "gsm8k", "dev", "text", 5).name == "gsm8k_dev_text.jsonl"
    rows = [{"id": f"q{i}", "ok": i % 2 == 0, "seconds": 1.0 + i, "tokens_written": 10, "latent_steps": 5}
            for i in range(4)]
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    assert done_ids(p) == {"q0", "q1", "q2", "q3"}
    s = metrics.summarize(metrics.read(p))
    assert s["n"] == 4 and s["accuracy"] == 0.5 and s["sec_avg"] == 2.5
    base = {"n": 1, "accuracy": 0.8, "sec_avg": 10, "tokens_written": 100}
    new = {"n": 1, "accuracy": 0.78, "sec_avg": 2.5, "tokens_written": 20}
    assert metrics.compare(base, new) == "4.00x faster, 80% fewer tokens written, accuracy -2.0 points"


def test_gate_verdict():
    from bench.gate import verdict
    text = {"n": 20, "sec_avg": 100, "accuracy": 0.80}
    assert verdict(text, {"n": 20, "sec_avg": 50, "accuracy": 0.78}) == "PASS"
    assert verdict(text, {"n": 20, "sec_avg": 90, "accuracy": 0.80}) == "NOT YET"   # too slow
    assert verdict(text, {"n": 20, "sec_avg": 40, "accuracy": 0.60}) == "NOT YET"   # too inaccurate
    assert verdict(text, {"n": 0}) == "NO DATA"


def test_honesty_summary():
    h = lambda f, js, s, c: {"faithful": f, "js": js, "shuffled_caught": s, "corrupted_caught": c}  # noqa: E731
    rows = [{"handoffs": [h(True, 0.1, True, True), h(False, 0.5, None, False)]},
            {"handoffs": [h(True, 0.3, False, None)]}]
    s = metrics.honesty_summary(rows)
    assert s["handoffs"] == 3 and s["faithful_rate"] == pytest.approx(2 / 3)
    assert s["shuffled_catch_rate"] == 0.5 and s["shuffled_n"] == 2
    assert s["corrupted_catch_rate"] == 0.5 and s["corrupted_n"] == 2
    assert s["mean_js_faithful"] == pytest.approx(0.2) and s["mean_js_unfaithful"] == 0.5


def test_honesty_summary_splits_by_correctness():
    h = lambda f: {"faithful": f, "js": 0.1, "shuffled_caught": None, "corrupted_caught": None}  # noqa: E731
    rows = [{"ok": True, "handoffs": [h(True), h(True), h(False)]},
            {"ok": False, "handoffs": [h(False), h(False), h(True)]}]
    s = metrics.honesty_summary(rows)
    assert s["faithful_rate_when_correct"] == pytest.approx(2 / 3)
    assert s["faithful_rate_when_wrong"] == pytest.approx(1 / 3)
    assert s["flagged_that_were_wrong"] == pytest.approx(2 / 3)  # 3 flagged: 1 on a right run, 2 on a wrong run


def test_auroc():
    assert metrics.auroc([0.1, 0.2], [0.5, 0.9]) == 1.0
    assert metrics.auroc([0.5, 0.9], [0.1, 0.2]) == 0.0
    assert metrics.auroc([0.3, 0.3], [0.3, 0.3]) == 0.5
    assert metrics.auroc([], [1.0]) is None


def test_team_size_summary_uses_only_questions_common_to_every_size(tmp_path):
    from bench.teamsize import by_size
    import json
    def row(i, agents, ok=True):
        return {"id": f"q{i}", "agents": agents, "ok": ok, "seconds": 2.0, "tokens_in": 100 * agents, "tokens_out": 50 * agents, "cost_usd": 0.001 * agents}
    (tmp_path / "gsm8k_tokenfactory_text.jsonl").write_text("\n".join(json.dumps(row(i, 4)) for i in range(5)))
    (tmp_path / "gsm8k_tokenfactory_text-team2.jsonl").write_text("\n".join(json.dumps(row(i, 2)) for i in range(2, 4)))
    res = by_size(tmp_path)
    assert res[2]["questions"] == res[4]["questions"] == 2          # only q2 and q3 appear in both
    assert res[4]["tokens_in"] == 400 and res[2]["tokens_in"] == 200
