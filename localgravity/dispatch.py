"""Dispatcher — the single path through which every tool runs.

Wraps tool handlers with the cross-cutting harness behaviors the model can't be
trusted to do: redundancy cache (kills the re-read loop seen in the gate test),
repetition detection, token accounting, and the structured transcript. The policy
gate lives inside each tool (it knows its own args best); dispatch enforces the
behaviors that span all tools.
"""

from __future__ import annotations

from .client import ToolCall
from .context import ToolContext, ToolResult
from .tools import HANDLERS

# Idempotent reads: identical calls can be served from cache.
CACHEABLE = {"read_file", "list_dir"}


def dispatch(call: ToolCall, ctx: ToolContext) -> ToolResult:
    session = ctx.session
    name = call.name
    args = call.arguments

    if name not in HANDLERS:
        valid = ", ".join(HANDLERS)
        return ToolResult(content=f"unknown tool '{name}'. Valid tools: {valid}", is_error=True)

    key = session.call_key(name, args)
    repeats = session.note_call(key)

    # PRE: redundancy cache for idempotent reads.
    if name in CACHEABLE and key in session.tool_cache:
        session.log("tool_result", name, cached=True)
        return ToolResult(
            content=f"[cache] you already ran this and nothing changed:\n{session.tool_cache[key]}",
            from_cache=True,
        )

    session.log("tool_call", name, args=args)
    result = HANDLERS[name](args, ctx)

    # POST: cache idempotent successes.
    if name in CACHEABLE and not result.is_error:
        session.tool_cache[key] = result.content

    # POST: repetition nudge (defense over the loop's repetition cut).
    if repeats >= 2 and not result.from_cache:
        result.content += "\n[harness] you are repeating the same action. Move to the next step."

    # POST: token accounting + transcript.
    session.charge_tokens(result.content)
    session.log("tool_result", name, is_error=result.is_error, chars=len(result.content))
    return result
