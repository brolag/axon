"""Anti-redundancy + dispatch tests: cached re-reads, unknown tools, jail enforcement."""

import pytest

from axon.client import ToolCall
from axon.context import ToolContext
from axon.dispatch import dispatch
from axon.policy import Policy, PolicyEngine
from axon.session import Session

POLICY = "policy.yaml"


@pytest.fixture
def ctx(tmp_path):
    (tmp_path / "hello.txt").write_text("hello world\nsecond line\n")
    policy = Policy.load(POLICY)
    engine = PolicyEngine(policy, cwd=tmp_path, interactive=False)
    session = Session(cwd=tmp_path, max_steps=policy.max_steps)
    return ToolContext(
        session=session,
        policy=engine,
        approve=lambda *_: False,
        run_subagent=lambda *_: "synthesis",
    )


def test_reread_served_from_cache(ctx):
    call = ToolCall(name="read_file", arguments={"path": "hello.txt"})
    first = dispatch(call, ctx)
    assert not first.from_cache
    assert "hello world" in first.content

    second = dispatch(call, ctx)
    assert second.from_cache is True
    assert "[cache]" in second.content


def test_unknown_tool_returns_error_not_crash(ctx):
    call = ToolCall(name="nonexistent_tool", arguments={})
    res = dispatch(call, ctx)
    assert res.is_error is True
    assert "unknown tool" in res.content


def test_write_then_read_jailed(ctx):
    w = dispatch(ToolCall(name="write_file", arguments={"path": "out.txt", "content": "data"}), ctx)
    assert not w.is_error
    r = dispatch(ToolCall(name="read_file", arguments={"path": "out.txt"}), ctx)
    assert "data" in r.content


def test_write_escape_blocked(ctx):
    res = dispatch(ToolCall(name="write_file", arguments={"path": "../escape.txt", "content": "x"}), ctx)
    assert res.is_error is True
    assert "jail" in res.content.lower() or "denied" in res.content.lower()


def test_shell_denied_destructive(ctx):
    res = dispatch(ToolCall(name="run_shell", arguments={"command": "rm -rf /"}), ctx)
    assert res.is_error is True
    assert "denied" in res.content.lower()


def test_backup_created_on_overwrite(ctx, tmp_path):
    dispatch(ToolCall(name="write_file", arguments={"path": "f.txt", "content": "v1"}), ctx)
    dispatch(ToolCall(name="write_file", arguments={"path": "f.txt", "content": "v2"}), ctx)
    backups = list((tmp_path / ".axon" / "backups").glob("f.txt.*"))
    assert backups, "a backup should exist after overwrite"
    assert backups[0].read_text() == "v1"
