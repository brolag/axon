"""Shared context passed to every tool. Avoids circular imports between tools and dispatch."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .policy import PolicyEngine
from .session import Session


@dataclass
class ToolContext:
    session: Session
    policy: PolicyEngine
    # Asks the human to approve a command/path. Returns True to allow.
    approve: Callable[[str, str], bool]
    # Runs a subagent loop with isolated context; returns its synthesis string.
    run_subagent: Callable[[str, list[str] | None, int], str]
    # Subagent recursion guard: current nesting depth.
    depth: int = 0


@dataclass
class ToolResult:
    content: str
    is_error: bool = False
    from_cache: bool = False
