"""Role prompts and team topologies. The last role in a topology is the one that writes."""
from __future__ import annotations

ROLES = {
    "planner": "You are the Planner on a team solving a math word problem. "
               "Think about a short step-by-step plan to solve it. Do not compute the final answer.",
    "critic": "You are the Critic on the team. Check the plan so far for mistakes or missing steps "
              "and decide how to fix them.",
    "refiner": "You are the Refiner on the team. Produce an improved, corrected plan.",
    "solver": "You are the Solver on the team. Using the team's work so far, solve the problem "
              "carefully and give the final numeric answer inside \\boxed{}.",
    "checker": "You are the Checker on the team. Re-check the arithmetic and the units in the work so far "
               "and point out any mistake.",
    "reviewer": "You are the Reviewer on the team. Look at the team's work so far and say what is still "
                "unclear or missing.",
    "editor": "You are the Editor on the team. Tighten the plan so far: remove steps that are not needed "
              "and make the rest clear.",
    "auditor": "You are the Auditor on the team. Check every number in the plan against the question.",
    "researcher": "You are the Researcher on the team. Read the provided search results and pick out "
                  "the facts that matter for the question.",
    "analyst": "You are the Analyst on the team. Work out what the facts imply for the question.",
    "research_critic": "You are the Critic on the team. Check the analysis so far for unsupported "
                       "claims or gaps and decide how to fix them.",
    "writer": "You are the Writer on the team. Using the team's work so far, write a short, accurate "
              "answer that cites the sources by number.",
}

# Other kinds of task reuse the same four roles with different wording. "math" is the set we measured on
# GSM8K and is never changed by the others.
TASK_ROLES = {
    "math": {},
    "logic": {
        "planner": "You are the Planner on a team solving a logic puzzle. List the clues in short form and "
                   "suggest an order to use them. Do not give the final answer.",
        "critic": "You are the Critic on the team. Check the plan so far for a misread clue or a missed "
                  "clue and say how to fix it.",
        "refiner": "You are the Refiner on the team. Work through the clues in order and narrow down who "
                   "lives where and who owns what.",
        "solver": "You are the Solver on the team. Using the team's work so far, finish the puzzle and "
                  "give the final answer as a single name inside \\boxed{}.",
    },
    "choice": {
        "planner": "You are the Planner on a team answering a multiple-choice question. Note which facts and "
                   "ideas matter and how to compare the options. Do not give the final answer.",
        "critic": "You are the Critic on the team. Check the reasoning so far for a wrong fact or a missed "
                  "option and say how to fix it.",
        "refiner": "You are the Refiner on the team. Compare the options using the corrected reasoning.",
        "solver": "You are the Solver on the team. Using the team's work so far, choose the best option and "
                  "give the final answer as the option letter inside \\boxed{}.",
    },
    "science": {
        "planner": "You are the Planner on a team answering a science multiple-choice question. Note which "
                   "ideas matter and how to compare the options. Do not give the final answer.",
        "critic": "You are the Critic on the team. Check the plan so far for a wrong idea or a missed option "
                  "and say how to fix it.",
        "refiner": "You are the Refiner on the team. Compare the options using the corrected ideas.",
        "solver": "You are the Solver on the team. Using the team's work so far, choose the best option and "
                  "give the final answer as the option letter inside \\boxed{}.",
    },
    # Same research team, but the Analyst and the Writer are told to work the numbers out step by step.
    # (Used to test why Telepathy did badly on research questions; the default research wording is unchanged.)
    "research_cot": {
        "analyst": "You are the Analyst on the team. Work out step by step the numbers the question needs, "
                   "using the facts the Researcher found.",
        "writer": "You are the Writer on the team. Work out the answer step by step from the facts and the "
                  "team's work, then finish with a line 'Final answer: <number>' and cite the sources by number.",
    },
    "code": {
        "planner": "You are the Planner on a team writing a small Python function. Describe the approach "
                   "and the edge cases in a few steps. Do not write the final code.",
        "critic": "You are the Critic on the team. Check the approach so far for bugs and missed edge "
                  "cases and say how to fix them.",
        "refiner": "You are the Refiner on the team. Produce a corrected, improved approach.",
        "solver": "You are the Solver on the team. Using the team's work so far, write the final Python "
                  "function in one ```python code block, with no explanation after it.",
    },
}


def role_prompt(role: str, task: str = "math") -> str:
    return TASK_ROLES.get(task, {}).get(role) or ROLES[role]


TOPOLOGIES = {
    "sequential": ["planner", "critic", "refiner", "solver"],
    # teams of other sizes, for measuring how cost grows as a team gets bigger (sequential is the 4-agent team)
    "team2": ["planner", "solver"],
    "team3": ["planner", "critic", "solver"],
    "team6": ["planner", "critic", "refiner", "checker", "reviewer", "solver"],
    "team8": ["planner", "critic", "refiner", "checker", "reviewer", "editor", "auditor", "solver"],
    "research": ["researcher", "analyst", "research_critic", "writer"],
}


def split_team(topology: str):
    """(silent/early roles, final role)."""
    roles = TOPOLOGIES[topology]
    return roles[:-1], roles[-1]


# Roles allowed to read OUTSIDE content (search results, files). Everyone else only sees the team's work,
# so untrusted text has exactly one entry point, which can be forced to hand off in readable text.
READERS = {"sequential": {"planner"}, "research": {"researcher"},
           "team2": {"planner"}, "team3": {"planner"}, "team6": {"planner"}, "team8": {"planner"}}


def reads_content(topology: str, role: str) -> bool:
    return role in READERS.get(topology, set())
