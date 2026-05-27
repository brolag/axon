"""Shell tools: run_shell, run_tests. The most dangerous surface — fully policy-gated."""

from __future__ import annotations

import subprocess

from ..context import ToolContext, ToolResult
from ..policy import Verdict

MAX_OUTPUT = 4000  # chars; truncate head+tail beyond this to protect the context window


def _truncate(text: str) -> str:
    if len(text) <= MAX_OUTPUT:
        return text
    head = text[: MAX_OUTPUT // 2]
    tail = text[-MAX_OUTPUT // 2:]
    return f"{head}\n[... truncated {len(text) - MAX_OUTPUT} chars ...]\n{tail}"


def _run(command: str, ctx: ToolContext, timeout: int) -> ToolResult:
    d = ctx.policy.evaluate_shell(command)
    if d.verdict is Verdict.DENY:
        return ToolResult(content=f"denied by policy: {d.reason}", is_error=True)
    if d.verdict is Verdict.ASK and not ctx.approve("run_shell", command):
        return ToolResult(content=f"permission denied by user for: {command}", is_error=True)

    cap = ctx.policy.policy.shell_timeout_max_sec
    timeout = min(timeout, cap)
    try:
        proc = subprocess.run(
            command,
            shell=True,
            cwd=str(ctx.policy.cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return ToolResult(content=f"command timed out after {timeout}s", is_error=True)

    out = _truncate((proc.stdout or "") + (proc.stderr or ""))
    body = out or "(no output)"
    return ToolResult(content=f"exit={proc.returncode}\n{body}", is_error=proc.returncode != 0)


def run_shell(args: dict, ctx: ToolContext) -> ToolResult:
    command = args.get("command", "")
    timeout = int(args.get("timeout_sec", ctx.policy.policy.shell_timeout_sec))
    return _run(command, ctx, timeout)


def run_tests(args: dict, ctx: ToolContext) -> ToolResult:
    cmd = args.get("test_command", "pytest -q")
    target = args.get("target")
    if target:
        cmd = f"{cmd} {target}"
    return _run(cmd, ctx, ctx.policy.policy.shell_timeout_sec)
