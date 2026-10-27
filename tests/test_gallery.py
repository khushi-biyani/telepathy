import pytest

from bench.gallery import boxed, grade_item, load_gallery, run_code_tests
from telepathy.roles import ROLES, role_prompt

G = {i["id"]: i for i in load_gallery()}
GOOD = """```python
def merge_slots(slots):
    out = []
    for a, b in sorted(slots):
        if out and a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out
```"""
BAD = GOOD.replace("a <= out", "a < out")


def test_math_roles_are_untouched_by_other_tasks():
    assert role_prompt("solver") == ROLES["solver"]
    assert role_prompt("solver", "logic") != ROLES["solver"] and "boxed" in role_prompt("solver", "logic")


def test_code_grader_accepts_good_and_rejects_subtle_bug():
    assert run_code_tests(GOOD, G["merge"]["tests"]) == (7, 7)
    assert run_code_tests(BAD, G["merge"]["tests"])[0] < 7
    assert run_code_tests("no code here", G["merge"]["tests"])[0] == 0


def test_code_grader_survives_an_infinite_loop():
    assert run_code_tests("```python\ndef merge_slots(s):\n    while True: pass\n```", G["merge"]["tests"], timeout=3)[0] == 0


def test_other_graders():
    assert grade_item(G["bakery"], "so \\boxed{1890}")[1] is True
    assert grade_item(G["bakery"], "so \\boxed{3150}")[1] is False
    assert grade_item(G["pets"], "\\boxed{Asha}")[1] is True and grade_item(G["pets"], "\\boxed{Dev}")[1] is False
    assert boxed("no box") is None
    assert grade_item(G["eiffel_burj"], "1889 and 2010 [1][4]. Final answer: 121")[:2] == ("121", True)
    assert grade_item(G["eiffel_burj"], "Final answer: 120")[1] is False


@pytest.mark.parametrize("kind", ["logic", "code"])
def test_engine_accepts_task(cfg, kind):
    from telepathy import Policy, TelepathyTeam
    team = TelepathyTeam("sequential", "latent", 2, config=cfg, task=kind, policy=Policy(honesty_check="off"))
    assert isinstance(team.run("Say hi.").answer, str)


# ---- the gallery itself is checked by computer, so what we say about it is true
import itertools
import json
from pathlib import Path

ITEMS = load_gallery()


def test_gallery_shape():
    assert len(ITEMS) == 18 and len({i["id"] for i in ITEMS}) == 18
    kinds = {i["kind"] for i in ITEMS}
    assert kinds == {"math", "logic", "code", "research", "science"}
    for i in ITEMS:
        assert i.get("question") or i.get("source")
        if i["kind"] == "research":
            pages = json.loads(Path(i["fixture"]).read_text())
            assert len(pages) >= 4 and i["answer"] and i.get("task") == "research_cot"
        if i["kind"] == "code":
            assert i["tests"] and i["func"]


def test_logic_puzzles_have_exactly_one_solution():
    people = ["Asha", "Bilal", "Chen", "Dev", "Esha"]; pets = ["cat", "dog", "fish", "bird", "rabbit"]
    found = []
    for pp in itertools.permutations(range(1, 6)):
        H = dict(zip(people, pp))
        if not (H["Chen"] == 1 and H["Dev"] == H["Esha"] + 1 and H["Bilal"] != 0):
            continue
        for qq in itertools.permutations(range(1, 6)):
            P = dict(zip(pets, qq))
            if (P["bird"] == 5 and H["Bilal"] == P["dog"] and abs(H["Asha"] - P["cat"]) == 1 and H["Esha"] != P["fish"]
                    and P["rabbit"] + 1 == P["dog"] and H["Chen"] != P["cat"]):
                found.append([n for n in people if H[n] == P["fish"]][0])
    assert found == [G["pets"]["answer"]]
    runners = ["Ana", "Bo", "Cy", "Di", "Ed"]
    race = []
    for p in itertools.permutations(range(1, 6)):
        R = dict(zip(runners, p))
        if (R["Ana"] < R["Bo"] and R["Cy"] == R["Di"] + 1 and R["Ed"] not in (1, 5) and R["Bo"] > R["Cy"]
                and R["Ana"] < R["Di"] and R["Ed"] < R["Cy"]):
            race.append([n for n in runners if R[n] == 3][0])
    assert race == [G["race"]["answer"]]
    suspects = ["Mia", "Noah", "Omar", "Pia"]
    cake = []
    for c in suspects:
        noah = c == "Omar"
        st = [c == "Noah", noah, not noah, c != "Pia"]
        if sum(st) == 1:
            cake.append(c)
    assert cake == [G["cake"]["answer"]]


def _is_balanced(s):
    st, m = [], {")": "(", "]": "[", "}": "{"}
    for ch in s:
        if ch in "([{":
            st.append(ch)
        elif ch in m and (not st or st.pop() != m[ch]):
            return False
    return not st


def _roman(s):
    v = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    return sum(-v[c] if i + 1 < len(s) and v[c] < v[s[i + 1]] else v[c] for i, c in enumerate(s))


def _flat(x):
    return [j for i in x for j in (_flat(i) if isinstance(i, list) else [i])]


def test_code_tests_pass_for_a_correct_solution_and_fail_for_a_plausible_bug():
    refs = {"brackets": (_is_balanced, lambda s: s.count("(") == s.count(")") and s.count("[") == s.count("]") and s.count("{") == s.count("}")),
            "roman": (_roman, lambda s: sum({"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}[c] for c in s)),
            "flatten": (_flat, lambda x: [j for i in x for j in (i if isinstance(i, list) else [i])])}
    for cid, (good, bad) in refs.items():
        tests = G[cid]["tests"]
        assert all(good(*t["args"]) == t["expect"] for t in tests), cid
        assert not all(bad(*t["args"]) == t["expect"] for t in tests), cid


def test_research_grader_ignores_citation_numbers():
    assert grade_item(G["burj_shanghai"], "828 m [1] minus 632 m [4] is 196 m.")[:2] == ("196", True)
    assert grade_item(G["moon_curiosity"], "Final answer: 43")[1] is True


def test_research_pages_contain_the_facts():
    from telepathy.tools import tavily
    need = {"eiffel_burj": ["1889", "2010"], "burj_shanghai": ["828", "632"], "moon_curiosity": ["1969", "2012"]}
    for gid, facts in need.items():
        seen = " ".join(c.text for c in tavily.as_content(json.loads(Path(G[gid]["fixture"]).read_text())))
        assert all(f in seen for f in facts), gid


def test_science_grader():
    item = {"kind": "science", "answer": "D"}
    assert grade_item(item, "so \\boxed{D}")[1] is True and grade_item(item, "so \\boxed{B}")[1] is False
