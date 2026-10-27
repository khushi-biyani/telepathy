"""Task loaders. Each item: {id, question, gold, kind}. First 200 items per task; the first 50 are
the dev split (tune latent steps there), the rest is the report split."""
from __future__ import annotations

import re

from telepathy.answers import extract_answer, extract_choice, same_number

N_TOTAL, N_DEV = 200, 50
CHOICE_SUFFIX = "\n\nGive your final answer as the option letter inside \\boxed{}."


def load_gsm8k(n: int = N_TOTAL):
    from datasets import load_dataset
    ds = load_dataset("openai/gsm8k", "main", split="test")
    out = []
    for i, item in enumerate(ds.select(range(min(n, len(ds))))):
        gold = re.search(r"####\s*([-+]?[\d,]+(?:\.\d+)?)", item["answer"]).group(1).replace(",", "")
        out.append({"id": f"gsm8k-{i}", "question": item["question"].strip(), "gold": gold, "kind": "number"})
    return out


def load_arc(n: int = N_TOTAL):
    from datasets import load_dataset
    ds = load_dataset("allenai/ai2_arc", "ARC-Challenge", split="test")
    out = []
    for i, item in enumerate(ds.select(range(min(n, len(ds))))):
        opts = "\n".join(f"{l}. {t}" for l, t in zip(item["choices"]["label"], item["choices"]["text"]))
        out.append({"id": f"arc-{i}", "question": f"{item['question'].strip()}\n{opts}{CHOICE_SUFFIX}",
                    "gold": item["answerKey"].strip().upper(), "kind": "choice"})
    return out


def load_medqa(n: int = N_TOTAL):
    """MedQA (USMLE, 4 options), test split. Gold is the option letter."""
    from datasets import load_dataset
    ds = load_dataset("GBaker/MedQA-USMLE-4-options", split="test")
    out = []
    for i, item in enumerate(ds.select(range(min(n, len(ds))))):
        opts = "\n".join(f"{k}. {v}" for k, v in sorted(item["options"].items()))
        out.append({"id": f"medqa-{i}", "question": f"{item['question'].strip()}\n{opts}{CHOICE_SUFFIX}",
                    "gold": item["answer_idx"].strip().upper(), "kind": "choice"})
    return out


def load_mbppplus(n: int = N_TOTAL):
    """MBPP+ (EvalPlus): write a Python function; graded by running the EvalPlus test script."""
    import ast
    from datasets import load_dataset
    ds = load_dataset("evalplus/mbppplus", split="test")
    out = []
    for item in ds.select(range(min(n, len(ds)))):
        first = ast.literal_eval(item["test_list"])[0] if isinstance(item["test_list"], str) else item["test_list"][0]
        q = f"{item['prompt'].strip()}\nYour code should pass this test:\n{first}"
        out.append({"id": f"mbpp-{item['task_id']}", "question": q, "gold": "pass", "kind": "code", "test": item["test"]})
    return out


LOADERS = {"gsm8k": load_gsm8k, "arc": load_arc, "medqa": load_medqa, "mbppplus": load_mbppplus}
ROLES_FOR = {"medqa": "choice", "mbppplus": "code"}  # gsm8k and arc keep the original (measured) wording


def _limits():
    try:
        import resource
        resource.setrlimit(resource.RLIMIT_CPU, (20, 20))  # no address-space cap: on Linux it breaks numpy's import
    except Exception:
        pass


_PASSED = "__TELEPATHY_ALL_TESTS_PASSED__"


def run_code(text: str, test: str, timeout: int = 30) -> bool:
    """True if the model's last ```python block passes the test script. Runs in a separate process with a CPU
    limit, a timeout and no keyboard input. A pass needs the test script to reach its very end, so code that
    exits early is not counted as passing. Only run this where running model-written code is acceptable."""
    import os, subprocess, sys, tempfile
    from pathlib import Path
    blocks = re.findall(r"```(?:python|py|Python)?[ \t]*\n(.*?)```", text, flags=re.S)
    code = blocks[-1] if blocks else (text if text.lstrip().startswith(("def ", "import ", "from ")) else None)
    if not code:
        return False
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "check.py"
        f.write_text(code + "\n\n" + test + f"\n\nprint({_PASSED!r})\n")
        env = dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")
        try:
            p = subprocess.run([sys.executable, "-I", str(f)], capture_output=True, text=True, timeout=timeout, cwd=d,
                               stdin=subprocess.DEVNULL, env=env, preexec_fn=_limits)
            return p.returncode == 0 and p.stdout.rstrip().endswith(_PASSED)
        except Exception:
            return False


def load(task: str, split: str = "test", n: int | None = None):
    items = LOADERS[task]()
    items = items[:N_DEV] if split == "dev" else items[N_DEV:] if split == "test" else items
    return items[:n] if n else items


def grade(item: dict, text: str):
    """(predicted answer, correct?)"""
    if item["kind"] == "choice":
        pred = extract_choice(text)
        return pred, pred == item["gold"]
    if item["kind"] == "code":
        ok = run_code(text, item["test"])
        return ("pass" if ok else "fail"), ok
    pred = extract_answer(text)
    return pred, same_number(pred, item["gold"])
