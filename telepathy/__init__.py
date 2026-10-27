"""Telepathy: agent teams that share thoughts instead of words, with readable, checked handoffs."""
from .config import Config
from .engine import Handoff, RunResult, TelepathyTeam
from .policy import Policy

__all__ = ["TelepathyTeam", "Config", "RunResult", "Handoff", "Policy"]
