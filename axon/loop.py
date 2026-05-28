"""The agentic loop — plan -> tool -> execute -> verify -> repeat.

A while-loop, never recursive (recursion only happens inside subagents, which run
their own bounded loop). Owns the four termination cuts: done, max_steps, stalled,
repetition.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .client import OllamaClient
from .context import ToolContext
from .dispatch import dispatch
from .policy import Policy, PolicyEngine
from .prompt import build_system_prompt, tools_doc
from .session import Session
from .tools import SCHEMAS, subagent_schemas


@dataclass
class LoopResult:
    done: bool
    reason: str
    steps: int
    session: Session


def _default_approve(kind: str, detail: str) -> bool:
    try:
        ans = input(f"[axon] the agent wants to {kind}: {detail}\n  Allow? [y/N/always] ").strip().lower()
    except EOFError:
        return False
    return ans in {"y", "yes", "always"}


def run_agent(
    task: str,
    cwd: str | Path,
    *,
    model: str = "gemma4:26b",
    host: str | None = None,
    temperature: float = 0.0,
    policy_path: str = "policy.yaml",
    identity: str = "You are a maintenance agent for this repository.",
    sections: list[str] | None = None,
    interactive: bool = True,
    approve: Callable[[str, str], bool] | None = None,
    client: OllamaClient | None = None,
    naive: bool = False,
) -> LoopResult:
    policy = Policy.load(policy_path)
    cwd = Path(cwd).resolve()
    engine = PolicyEngine(policy, cwd=cwd, interactive=interactive)
    client = client or OllamaClient(model=model, host=host, temperature=temperature)
    approve = approve or (_default_approve if interactive else (lambda *_: False))

    schemas = SCHEMAS
    system = build_system_prompt(identity, str(cwd), tools_doc(schemas), sections, naive=naive)
    session = Session(
        cwd=cwd,
        max_steps=policy.max_steps,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": task}],
    )

    def run_subagent(sub_task: str, allowed: list[str] | None, max_steps: int) -> str:
        return _run_subagent_loop(sub_task, engine, client, max_steps, depth=1)

    return _loop(session, engine, client, schemas, approve, run_subagent, depth=0, naive=naive)


def run_repl(
    cwd: str | Path,
    *,
    model: str = "gemma4:26b",
    host: str | None = None,
    temperature: float = 0.0,
    policy_path: str = "policy.yaml",
    identity: str = "You are a coding agent for this repository.",
    sections: list[str] | None = None,
    interactive: bool = True,
    approve: Callable[[str, str], bool] | None = None,
    client: OllamaClient | None = None,
    first_task: str | None = None,
) -> None:
    """Conversational session: keep one Session alive across turns.

    Context (history, read-file cache) carries over between tasks, so the agent
    does not re-read what it already knows. Commands: /exit, /quit, /reset.
    If first_task is given, it runs as the opening turn before prompting.
    """
    policy = Policy.load(policy_path)
    cwd = Path(cwd).resolve()
    engine = PolicyEngine(policy, cwd=cwd, interactive=interactive)
    client = client or OllamaClient(model=model, host=host, temperature=temperature)
    approve = approve or (_default_approve if interactive else (lambda *_: False))

    schemas = SCHEMAS
    system = build_system_prompt(identity, str(cwd), tools_doc(schemas), sections)

    def fresh_session() -> Session:
        return Session(
            cwd=cwd,
            max_steps=policy.max_steps,
            messages=[{"role": "system", "content": system}],
        )

    session = fresh_session()

    def run_subagent(sub_task: str, allowed: list[str] | None, max_steps: int) -> str:
        return _run_subagent_loop(sub_task, engine, client, max_steps, depth=1)

    def run_turn(line: str) -> None:
        # Continue the same session: append the task, reset per-turn counters.
        session.messages.append({"role": "user", "content": line})
        session.step = 0
        session.done = False
        session.done_reason = None
        session.recent_calls = []
        result = _loop(session, engine, client, schemas, approve, run_subagent, depth=0)
        flag = "✓" if result.done else "✗"
        print(f"{flag} {result.reason} in {result.steps} steps "
              f"(~{max(session.budget_tokens, 0)} context tokens left)\n")

    print(f"axon REPL  ·  model={client.model}  ·  workspace={cwd}")
    print("Type a task. Commands: /exit, /quit, /reset.\n")

    if first_task:
        print(f"axon › {first_task}")
        run_turn(first_task)

    while True:
        try:
            line = input("axon › ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        if line in {"/exit", "/quit"}:
            break
        if line == "/reset":
            session = fresh_session()
            print("(session reset)\n")
            continue
        run_turn(line)
    print("bye")


def _loop(session, engine, client, schemas, approve, run_subagent, depth, naive=False) -> LoopResult:
    nudged = False
    while not session.done and session.step < session.max_steps:
        session.step += 1

        # Inject an ephemeral "files in context" reminder (not persisted). Off in naive mode.
        reminder = "" if naive else session.files_in_context()
        messages = session.messages + ([{"role": "system", "content": reminder}] if reminder else [])

        turn = client.chat(messages, schemas)

        if not turn.tool_calls:
            # Text-only turn: ambiguous. One nudge, then cut as stalled.
            session.messages.append({"role": "assistant", "content": turn.content})
            if nudged:
                session.done_reason = "stalled"
                session.log("cut", "stalled")
                return LoopResult(False, "stalled", session.step, session)
            session.messages.append({
                "role": "user",
                "content": "Did you finish? Call done(summary). If not, call a tool to make progress.",
            })
            nudged = True
            continue

        nudged = False
        session.messages.append({
            "role": "assistant",
            "content": turn.content,
            "tool_calls": [{"function": {"name": c.name, "arguments": c.arguments}} for c in turn.tool_calls],
        })

        ctx = ToolContext(session=session, policy=engine, approve=approve, run_subagent=run_subagent, depth=depth, naive=naive)
        for call in turn.tool_calls:
            # Repetition cut: 3 identical calls in a row (off in naive mode).
            key = session.call_key(call.name, call.arguments)
            if not naive and session.recent_calls.count(key) >= 2 and session.recent_calls[-1:] == [key]:
                session.done_reason = "repetition_detected"
                session.log("cut", "repetition_detected", tool=call.name)
                return LoopResult(False, "repetition_detected", session.step, session)

            result = dispatch(call, ctx)
            session.messages.append({"role": "tool", "content": result.content})
            if session.done:
                session.log("cut", "done")
                return LoopResult(True, "done", session.step, session)

        # Budget cut: force synthesis before the window explodes.
        if session.budget_tokens <= 1000:
            session.messages.append({
                "role": "user",
                "content": "You are near your context limit. Call done(summary) with what you have.",
            })

    reason = session.done_reason or ("done" if session.done else "max_steps_exceeded")
    session.log("cut", reason)
    return LoopResult(session.done, reason, session.step, session)


def _run_subagent_loop(task, engine, client, max_steps, depth) -> str:
    """Isolated-context subagent: fresh Session, reduced read-only toolset, no nesting."""
    schemas = subagent_schemas()
    system = build_system_prompt(
        "You are a subagent. Investigate the task and return a concise synthesis. You are read-only.",
        str(engine.cwd),
        tools_doc(schemas),
    )
    sub = Session(
        cwd=engine.cwd,
        max_steps=min(max_steps, engine.policy.subagent_max_steps),
        messages=[{"role": "system", "content": system}, {"role": "user", "content": task}],
    )

    def no_subagent(*_):
        return "denied: nested subagents are not allowed"

    result = _loop(sub, engine, client, schemas, lambda *_: False, no_subagent, depth=depth)
    # Return the last assistant content as the synthesis.
    for msg in reversed(result.session.messages):
        if msg.get("role") == "assistant" and msg.get("content"):
            return msg["content"]
    return "(subagent produced no synthesis)"
