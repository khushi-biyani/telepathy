"""Auto-mode and safety rules. Pure functions, no LLM: the policy cannot be argued with.
Every decision is logged to the event stream by the engine. The safety rules (Section 8a) sit in the
same policy and take priority over the auto-mode rules: the most restrictive outcome wins."""
from __future__ import annotations

import random
from dataclasses import dataclass, field, fields
from pathlib import Path

import yaml

HONESTY = ("off", "sample", "always")
ON_UNFAITHFUL = ("switch_to_text", "flag_only")
SHARES = ("full", "thoughts_only")
SCANS = ("off", "demo_only", "always")
SCAN_ACTIONS = ("warn", "block")
POLICY_FILE = Path(__file__).resolve().parent.parent / "policy.yaml"


@dataclass
class Policy:
    # auto mode
    honesty_check: str = "sample"        # off | sample | always
    sample_rate: float = 0.3             # fraction of handoffs audited in sample mode
    on_unfaithful: str = "switch_to_text"
    high_stakes_roles: list = field(default_factory=list)  # always hand off in text
    max_text_fallbacks: int = 2
    # safety (Section 8a)
    tainted_handoff: str = "text"        # mandatory: an agent that read outside content hands off in text
    agent_tools: str = "none"            # mandatory: agents cannot act; only our code calls read-only tools
    share_default: str = "thoughts_only"  # for handoffs that cross roles with different context
    untrusted_scan: str = "demo_only"    # off | demo_only | always
    scan_action: str = "warn"            # warn | block

    def __post_init__(self):
        assert self.honesty_check in HONESTY, self.honesty_check
        assert self.on_unfaithful in ON_UNFAITHFUL, self.on_unfaithful
        if self.tainted_handoff != "text":
            raise ValueError("tainted_handoff must be 'text': a tainted agent may never hand off silently")
        if self.agent_tools != "none":
            raise ValueError("agent_tools must be 'none': Telepathy agents only produce text")
        if self.share_default not in SHARES:
            raise ValueError(f"share_default must be one of {SHARES}")
        if self.untrusted_scan not in SCANS:
            raise ValueError(f"untrusted_scan must be one of {SCANS}")
        if self.scan_action not in SCAN_ACTIONS:
            raise ValueError(f"scan_action must be one of {SCAN_ACTIONS}")

    @classmethod
    def load(cls, path: Path | str = POLICY_FILE) -> "Policy":
        """Policy from policy.yaml (or the defaults if there is no file). Config only: nothing at run
        time, and no model output, can change these values."""
        p = Path(path)
        data = (yaml.safe_load(p.read_text()) or {}) if p.exists() else {}
        known = {f.name for f in fields(cls)}
        # YAML reads an unquoted `off` as False; a developer who writes `honesty_check: off` means the word
        clean = {k: ("off" if v is False else v) for k, v in data.items() if k in known}
        return cls(**clean)


@dataclass
class Plan:
    forced_text: set   # handoff indexes that must be written in English
    audited: set       # handoff indexes whose subtitle gets the honesty check
    reasons: dict = field(default_factory=dict)  # handoff index -> "tainted" | "high_stakes" | "unfaithful"


def make_plan(policy: Policy, early_roles: list, rng: random.Random, tainted=()) -> Plan:
    """`tainted`: indexes of agents that read outside content. They are always forced to text."""
    tainted = set(tainted)
    high = {i for i, r in enumerate(early_roles) if r in policy.high_stakes_roles}
    forced = high | tainted
    reasons = {i: "high_stakes" for i in high}
    reasons.update({i: "tainted" for i in tainted})  # the stricter reason wins
    candidates = [i for i in range(len(early_roles)) if i not in forced]
    if policy.honesty_check == "always":
        audited = set(candidates)
    elif policy.honesty_check == "sample":
        audited = {i for i in candidates if rng.random() < policy.sample_rate}
    else:
        audited = set()
    return Plan(forced, audited, reasons)


def decide(policy: Policy, faithful: bool, fallbacks_used: int) -> str:
    """'ok' | 'flag' | 'switch_to_text'. Most restrictive outcome wins."""
    if faithful:
        return "ok"
    if policy.on_unfaithful == "switch_to_text" and fallbacks_used < policy.max_text_fallbacks:
        return "switch_to_text"
    return "flag"
