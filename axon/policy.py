"""PolicyEngine — the security core of axon.

Evaluates every tool action against a declarative policy (policy.yaml) and returns
one of three verdicts: ALLOW, ASK, DENY. DENY always wins.

Design principle: the model is untrusted input. A file's contents or a command's
origin never relaxes the policy. The hardening deny layer is non-overridable: no
configuration can turn a fork bomb into an ALLOW.
"""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import yaml


class Verdict(str, Enum):
    ALLOW = "allow"
    ASK = "ask"
    DENY = "deny"


@dataclass
class Decision:
    verdict: Verdict
    reason: str


@dataclass
class Policy:
    """Parsed policy.yaml."""

    default: Verdict = Verdict.ASK
    workspace_jail: bool = True
    deny_paths: list[str] = field(default_factory=list)
    shell_deny: list[re.Pattern] = field(default_factory=list)
    shell_allow: list[re.Pattern] = field(default_factory=list)
    shell_ask: list[re.Pattern] = field(default_factory=list)
    write_max_bytes: int = 1_048_576
    read_max_bytes: int = 262_144
    backup_before_overwrite: bool = True
    subagent_max_depth: int = 1
    subagent_default_mode: str = "read_only"
    subagent_max_steps: int = 10
    max_steps: int = 25
    shell_timeout_sec: int = 60
    shell_timeout_max_sec: int = 300

    @classmethod
    def load(cls, path: str | Path) -> "Policy":
        data = yaml.safe_load(Path(path).read_text()) or {}
        shell = data.get("shell", {})
        files = data.get("files", {})
        subs = data.get("subagents", {})
        limits = data.get("limits", {})
        return cls(
            default=Verdict(data.get("default", "ask")),
            workspace_jail=data.get("workspace_jail", True),
            deny_paths=list(data.get("deny_paths", [])),
            shell_deny=[re.compile(p) for p in shell.get("deny_patterns", [])],
            shell_allow=[re.compile(p) for p in shell.get("allow_patterns", [])],
            shell_ask=[re.compile(p) for p in shell.get("ask_patterns", [])],
            write_max_bytes=files.get("write", {}).get("max_file_bytes", 1_048_576),
            read_max_bytes=files.get("read", {}).get("max_file_bytes", 262_144),
            backup_before_overwrite=files.get("write", {}).get("backup_before_overwrite", True),
            subagent_max_depth=subs.get("max_depth", 1),
            subagent_default_mode=subs.get("default_mode", "read_only"),
            subagent_max_steps=subs.get("max_steps", 10),
            max_steps=limits.get("max_steps", 25),
            shell_timeout_sec=limits.get("shell_timeout_sec", 60),
            shell_timeout_max_sec=limits.get("shell_timeout_max_sec", 300),
        )


class PolicyError(Exception):
    """Raised on a hard policy violation that must abort the action."""


class PolicyEngine:
    """Evaluates tool actions against a Policy.

    Args:
        policy: parsed Policy.
        cwd: the workspace root. Used as the filesystem jail.
        interactive: if False (CI / --yolo), ASK is downgraded to DENY so nothing
            that would prompt a human gets auto-approved.
    """

    def __init__(self, policy: Policy, cwd: str | Path, interactive: bool = True):
        self.policy = policy
        self.cwd = Path(cwd).resolve()
        self.interactive = interactive

    # ---- shell ----------------------------------------------------------------

    def evaluate_shell(self, command: str) -> Decision:
        """Verdict for a shell command. Order: deny (hardening) -> allow -> ask -> default."""
        stripped = command.strip()

        # Layer 1: non-overridable hardening deny.
        for pat in self.policy.shell_deny:
            if pat.search(command):
                return Decision(Verdict.DENY, f"blocked by hardening rule: /{pat.pattern}/")

        # Layer 2: explicit allow.
        for pat in self.policy.shell_allow:
            if pat.search(stripped):
                return self._maybe_downgrade(Decision(Verdict.ALLOW, f"matched allow: /{pat.pattern}/"))

        # Layer 3: explicit ask.
        for pat in self.policy.shell_ask:
            if pat.search(stripped):
                return self._maybe_downgrade(Decision(Verdict.ASK, f"matched ask: /{pat.pattern}/"))

        # Layer 4: default.
        return self._maybe_downgrade(Decision(self.policy.default, "no rule matched, using default"))

    # ---- filesystem -----------------------------------------------------------

    def resolve_in_jail(self, rel_path: str) -> Path:
        """Resolve a path and ensure it stays inside the workspace jail.

        Raises PolicyError on traversal or symlink escape.
        """
        # Resolve against cwd. strict=False so non-existent files (writes) are allowed.
        target = (self.cwd / rel_path).resolve()
        if self.policy.workspace_jail and not self._is_within(target, self.cwd):
            raise PolicyError(f"path escapes workspace jail: {rel_path}")
        return target

    def evaluate_read(self, rel_path: str) -> Decision:
        target = self.resolve_in_jail(rel_path)  # raises on escape
        if self._matches_deny_path(target):
            return Decision(Verdict.DENY, f"path is in deny_paths: {rel_path}")
        return Decision(Verdict.ALLOW, "read within jail")

    def evaluate_write(self, rel_path: str, content: str = "") -> Decision:
        target = self.resolve_in_jail(rel_path)  # raises on escape
        if self._matches_deny_path(target):
            return Decision(Verdict.DENY, f"path is in deny_paths: {rel_path}")
        if len(content.encode("utf-8")) > self.policy.write_max_bytes:
            return Decision(Verdict.DENY, f"file exceeds max_file_bytes ({self.policy.write_max_bytes})")
        return self._maybe_downgrade(Decision(Verdict.ALLOW, "write within jail"))

    # ---- helpers --------------------------------------------------------------

    def _maybe_downgrade(self, decision: Decision) -> Decision:
        """In non-interactive mode, ASK becomes DENY (never auto-approve a prompt)."""
        if decision.verdict is Verdict.ASK and not self.interactive:
            return Decision(Verdict.DENY, f"ASK downgraded to DENY (non-interactive): {decision.reason}")
        return decision

    def _matches_deny_path(self, target: Path) -> bool:
        try:
            rel = target.relative_to(self.cwd).as_posix()
        except ValueError:
            # Outside cwd entirely; jail check should have caught it, but deny anyway.
            return True
        for pattern in self.policy.deny_paths:
            # Match against the relative posix path and the bare filename.
            if fnmatch.fnmatch(rel, pattern) or fnmatch.fnmatch(target.name, pattern):
                return True
            # Patterns like ".git/**" should also match a path that starts with ".git/".
            prefix = pattern.replace("/**", "")
            if pattern.endswith("/**") and (rel == prefix or rel.startswith(prefix + "/")):
                return True
        return False

    @staticmethod
    def _is_within(target: Path, root: Path) -> bool:
        try:
            target.relative_to(root)
            return True
        except ValueError:
            return False
