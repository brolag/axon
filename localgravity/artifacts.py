"""Turn the structured transcript into a verifiable artifact (not raw logs).

This is Antigravity's "artifacts over logs" idea: a readable record of what the
agent planned, did, and verified. Also emits raw JSONL for the eval harness
(raw traces > summaries).
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .loop import LoopResult


def to_markdown(result: LoopResult) -> str:
    s = result.session
    lines = [
        f"# localgravity run",
        f"- result: **{result.reason}** ({'verified done' if result.done else 'incomplete'})",
        f"- steps: {result.steps}/{s.max_steps}",
        f"- tokens left: {s.budget_tokens}",
        "",
        "## Trace",
    ]
    for ev in s.transcript:
        if ev.kind == "tool_call":
            lines.append(f"- step {ev.step}: → `{ev.name}` {json.dumps(ev.detail.get('args', {}), ensure_ascii=False)}")
        elif ev.kind == "tool_result":
            tag = "cache" if ev.detail.get("cached") else ("error" if ev.detail.get("is_error") else "ok")
            lines.append(f"  - {ev.name} [{tag}]")
        elif ev.kind == "cut":
            lines.append(f"- step {ev.step}: ⏹ cut = {ev.name}")
    return "\n".join(lines)


def to_jsonl(result: LoopResult) -> str:
    return "\n".join(json.dumps(asdict(ev), ensure_ascii=False) for ev in result.session.transcript)


def save(result: LoopResult, out_dir: str | Path) -> dict[str, Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    md = out / "transcript.md"
    jl = out / "transcript.jsonl"
    md.write_text(to_markdown(result))
    jl.write_text(to_jsonl(result))
    return {"markdown": md, "jsonl": jl}
