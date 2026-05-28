"""Session — the single piece of state that flows through the agentic loop.

Holds the message history (the contract with Ollama) plus harness bookkeeping the
model does not see directly: step counter, token budget, caches that kill the
re-read redundancy observed in the gate test, and the structured transcript.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


@dataclass
class Event:
    """One entry in the structured transcript (the verifiable artifact)."""

    step: int
    kind: str           # "tool_call", "tool_result", "assistant", "verdict", "cut"
    name: str
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass
class Session:
    cwd: Path
    messages: list[dict] = field(default_factory=list)
    step: int = 0
    max_steps: int = 25
    budget_tokens: int = 32_000
    done: bool = False
    done_reason: str | None = None
    tests_passed: bool = False   # a verification (run_tests / pytest) returned success
    tool_cache: dict[str, str] = field(default_factory=dict)   # hash(tool+args) -> result
    read_files: dict[str, str] = field(default_factory=dict)   # path -> content hash
    recent_calls: list[str] = field(default_factory=list)      # hashes for repetition detection
    transcript: list[Event] = field(default_factory=list)

    # ---- token budget (rough estimate: ~4 chars/token) ----------------------

    def charge_tokens(self, text: str) -> None:
        self.budget_tokens -= max(1, len(text) // 4)

    # ---- caching / redundancy ----------------------------------------------

    @staticmethod
    def call_key(tool_name: str, args: dict) -> str:
        import json
        return _hash(tool_name + json.dumps(args, sort_keys=True, ensure_ascii=False))

    def remember_read(self, path: str, content: str) -> None:
        self.read_files[path] = _hash(content)

    def is_unchanged_read(self, path: str, content: str) -> bool:
        return self.read_files.get(path) == _hash(content)

    def note_call(self, key: str) -> int:
        """Record a call hash; return how many of the last 3 calls are identical."""
        self.recent_calls.append(key)
        self.recent_calls = self.recent_calls[-3:]
        return self.recent_calls.count(key)

    def files_in_context(self) -> str:
        if not self.read_files:
            return ""
        listed = ", ".join(f"{p} ({h})" for p, h in self.read_files.items())
        return f"Files already in your context: {listed}. Do not re-read them unless you expect a change."

    # ---- transcript ----------------------------------------------------------

    def log(self, kind: str, name: str, **detail: Any) -> None:
        self.transcript.append(Event(self.step, kind, name, detail))
