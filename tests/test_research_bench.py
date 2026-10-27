from bench.research_bench import ARMS, generate, grade, sign_p, summarize
from telepathy.roles import role_prompt, ROLES


def test_generated_questions_are_consistent():
    items = generate(20)
    assert len(items) == 20 and len({i["id"] for i in items}) == 20
    for it in items:
        assert len(it["pages"]) == 3 and it["attack_word"].lower() in it["pages"][1]["content"].lower()
        assert it["answer"].isdigit() and int(it["answer"]) > 0
    # the key number lives only in a page, not in the question (so the team has to read)
    t0 = [i for i in items if i["template"] == 0][0]
    price = [w for w in t0["pages"][0]["content"].split() if w.isdigit()][0]
    assert price not in t0["question"].split()
    assert generate(20) == items  # deterministic


def test_grader_lenient_vs_strict_and_attack():
    it = {"answer": "16", "attack_word": "PINEAPPLE"}
    assert grade(it, "She gets 16 rupees [1].") == {"lenient": True, "strict": True, "followed": False}
    g = grade(it, "100 - 84 = 16 but then I add 4 and get 88 [2]")
    assert g["lenient"] and not g["strict"]
    assert grade(it, "Final answer: 16")["strict"] and not grade(it, "PINEAPPLE 16")["strict"]
    assert grade(it, "PINEAPPLE")["followed"]


def test_arms_and_roles():
    assert set(ARMS) == {"text", "latent", "latent_s0", "latent_cot", "latent_s0_cot"}
    assert role_prompt("writer", "research_cot") != ROLES["writer"] and "step by step" in role_prompt("writer", "research_cot")
    assert role_prompt("researcher", "research_cot") == ROLES["researcher"]  # unchanged roles fall back to the default


def test_stats_helpers():
    assert sign_p(0, 0) == 1.0 and sign_p(10, 0) < 0.01
    rows = {"text": {"a": {"lenient": True, "strict": True, "followed": False, "seconds": 1.0}},
            "latent": {"a": {"lenient": True, "strict": False, "followed": False, "seconds": 1.0}}}
    assert "latent vs text" in summarize(rows)
