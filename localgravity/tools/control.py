"""Control tools: done."""

from __future__ import annotations

from ..context import ToolContext, ToolResult


def done(args: dict, ctx: ToolContext) -> ToolResult:
    summary = args.get("summary", "")
    verified = args.get("verified", False)
    ctx.session.done = True
    ctx.session.done_reason = "done"
    return ToolResult(content=f"DONE (verified={verified}): {summary}")
