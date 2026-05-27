"""Filesystem tools: read_file, write_file, list_dir. All jailed and policy-gated."""

from __future__ import annotations

from pathlib import Path

from ..context import ToolContext, ToolResult
from ..policy import PolicyError, Verdict


def read_file(args: dict, ctx: ToolContext) -> ToolResult:
    path = args.get("path", "")
    try:
        d = ctx.policy.evaluate_read(path)
    except PolicyError as e:
        return ToolResult(content=f"denied: {e}", is_error=True)
    if d.verdict is Verdict.DENY:
        return ToolResult(content=f"denied: {d.reason}", is_error=True)

    target = ctx.policy.resolve_in_jail(path)
    if not target.exists():
        return ToolResult(content=f"file not found: {path}", is_error=True)

    raw = target.read_bytes()
    cap = ctx.policy.policy.read_max_bytes
    truncated = len(raw) > cap
    text = raw[:cap].decode("utf-8", errors="replace")

    ctx.session.remember_read(path, text)

    start = args.get("start_line")
    end = args.get("end_line")
    lines = text.splitlines()
    if start or end:
        s = (start or 1) - 1
        e = end or len(lines)
        lines = lines[s:e]
        offset = s
    else:
        offset = 0
    numbered = "\n".join(f"{i + offset + 1}\t{ln}" for i, ln in enumerate(lines))
    suffix = "\n[... truncated, file exceeds read cap ...]" if truncated else ""
    return ToolResult(content=numbered + suffix)


def write_file(args: dict, ctx: ToolContext) -> ToolResult:
    path = args.get("path", "")
    content = args.get("content", "")
    try:
        d = ctx.policy.evaluate_write(path, content)
    except PolicyError as e:
        return ToolResult(content=f"denied: {e}", is_error=True)
    if d.verdict is Verdict.DENY:
        return ToolResult(content=f"denied: {d.reason}", is_error=True)
    if d.verdict is Verdict.ASK and not ctx.approve("write_file", path):
        return ToolResult(content=f"permission denied by user for write: {path}", is_error=True)

    target = ctx.policy.resolve_in_jail(path)

    # Backup before overwrite (never blind destruction).
    if target.exists() and ctx.policy.policy.backup_before_overwrite:
        backup_dir = ctx.policy.cwd / ".axon" / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        rel = target.relative_to(ctx.policy.cwd).as_posix().replace("/", "__")
        (backup_dir / f"{rel}.{ctx.session.step}").write_bytes(target.read_bytes())

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
    ctx.session.remember_read(path, content)  # writing updates what's "in context"
    return ToolResult(content=f"wrote {path} ({len(content)} bytes)")


def list_dir(args: dict, ctx: ToolContext) -> ToolResult:
    path = args.get("path", ".")
    recursive = args.get("recursive", False)
    try:
        d = ctx.policy.evaluate_read(path)
    except PolicyError as e:
        return ToolResult(content=f"denied: {e}", is_error=True)
    if d.verdict is Verdict.DENY:
        return ToolResult(content=f"denied: {d.reason}", is_error=True)

    target = ctx.policy.resolve_in_jail(path)
    if not target.exists():
        return ToolResult(content=f"path not found: {path}", is_error=True)

    entries: list[str] = []
    cap = 500
    base = target
    walker = base.rglob("*") if recursive else base.iterdir()
    for p in sorted(walker):
        if ".git" in p.parts or ".axon" in p.parts:
            continue
        rel = p.relative_to(base).as_posix()
        entries.append(rel + ("/" if p.is_dir() else ""))
        if len(entries) >= cap:
            entries.append(f"[... truncated at {cap} entries ...]")
            break
    return ToolResult(content="\n".join(entries) or "(empty)")
