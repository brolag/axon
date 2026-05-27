"""start_subagent: launch an isolated-context loop and return only its synthesis.

Depth is capped at 1 (a subagent has no start_subagent), so recursion can't explode.
The actual loop is injected via ctx.run_subagent to avoid a circular import with loop.py.
"""

from __future__ import annotations

from ..context import ToolContext, ToolResult


def start_subagent(args: dict, ctx: ToolContext) -> ToolResult:
    task = args.get("task", "")
    allowed = args.get("allowed_paths")
    max_steps = int(args.get("max_steps", ctx.policy.policy.subagent_max_steps))

    if ctx.depth >= ctx.policy.policy.subagent_max_depth:
        return ToolResult(
            content="denied: subagent depth limit reached (no nested subagents)",
            is_error=True,
        )
    if not task:
        return ToolResult(content="error: 'task' is required", is_error=True)

    synthesis = ctx.run_subagent(task, allowed, max_steps)
    return ToolResult(content=f"[subagent synthesis]\n{synthesis}")
