"""MedQA and MBPP+ loaders and the code grader. These read the public datasets (cached after the first run)."""
import pytest

from bench.datasets import ROLES_FOR, grade, load, run_code
from telepathy.roles import role_prompt, ROLES


@pytest.fixture(scope="module")
def mbpp():
    try:
        return load("mbppplus", "all", 60)
    except Exception as e:  # no network
        pytest.skip(f"dataset not available: {e}")


@pytest.fixture(scope="module")
def medqa():
    try:
        return load("medqa", "all", 60)
    except Exception as e:
        pytest.skip(f"dataset not available: {e}")


def test_reference_solutions_pass_and_wrong_code_fails(mbpp):
    from datasets import load_dataset
    ref = {f"mbpp-{r['task_id']}": r["code"] for r in load_dataset("evalplus/mbppplus", split="test").select(range(60))}
    checked = 0
    for it in mbpp[:8]:
        assert grade(it, f"```python\n{ref[it['id']]}\n```")[1], it["id"]
        assert not grade(it, "```python\ndef nothing():\n    return None\n```")[1]
        checked += 1
    assert checked == 8
    assert not run_code("no code block", mbpp[0]["test"])


def test_code_grader_survives_a_hang(mbpp):
    name = mbpp[0]["question"].split("assert ")[1].split("(")[0].replace("set", "").strip() or "f"
    assert not run_code(f"```python\ndef {name}(*a):\n    while True: pass\n```", mbpp[0]["test"], timeout=3)


def test_medqa_items(medqa):
    assert all(i["kind"] == "choice" and i["gold"] in "ABCD" and "\nA." in i["question"] for i in medqa)
    assert grade(medqa[0], f"so \\boxed{{{medqa[0]['gold']}}}")[1]


def test_roles_for_new_tasks_only():
    assert ROLES_FOR == {"medqa": "choice", "mbppplus": "code"}
    assert "gsm8k" not in ROLES_FOR and role_prompt("solver") == ROLES["solver"]
    assert "option letter" in role_prompt("solver", "choice")


def test_grader_edge_cases(mbpp):
    from datasets import load_dataset
    it = mbpp[0]
    ref = {f"mbpp-{r['task_id']}": r["code"] for r in load_dataset("evalplus/mbppplus", split="test").select(range(60))}[it["id"]]
    assert run_code(ref, it["test"])                                   # no code fence: still graded
    assert not run_code(f"```python\nimport sys\nsys.exit(0)\n{ref}\n```", it["test"])   # quitting early is not a pass
    assert not run_code(f"```python\nx = input()\n{ref}\n```", it["test"], timeout=10)    # waiting for input fails fast
    assert run_code(f"Here you go:\n```python\n{ref}\n```\nDone.", it["test"])
