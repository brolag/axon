"""Loop logic tests with a scripted fake client (no Ollama needed)."""

import pytest

from localgravity.client import ModelTurn, ToolCall
from localgravity.loop import run_agent

POLICY = "policy.yaml"


class FakeClient:
    """Returns a scripted sequence of ModelTurns."""

    def __init__(self, turns):
        self._turns = list(turns)
        self.calls = 0

    def chat(self, messages, tools):
        if self.calls < len(self._turns):
            turn = self._turns[self.calls]
        else:
            turn = ModelTurn(content="(no more script)", tool_calls=[])
        self.calls += 1
        return turn


def tc(name, **args):
    return ToolCall(name=name, arguments=args)


def run(turns, tmp_path, **kw):
    return run_agent(
        task="do the thing",
        cwd=tmp_path,
        policy_path=POLICY,
        interactive=False,
        client=FakeClient(turns),
        **kw,
    )


def test_done_terminates_happy_path(tmp_path):
    turns = [
        ModelTurn("listing", [tc("list_dir", path=".")]),
        ModelTurn("done", [tc("done", summary="all good", verified=True)]),
    ]
    res = run(turns, tmp_path)
    assert res.done is True
    assert res.reason == "done"
    assert res.steps == 2


def test_max_steps_cut(tmp_path):
    # Never calls done; alternate paths so repetition doesn't fire first. Should hit max_steps.
    turns = [
        ModelTurn("loop", [tc("list_dir", path="." if i % 2 else "sub")])
        for i in range(50)
    ]
    res = run(turns, tmp_path)
    assert res.done is False
    assert res.reason == "max_steps_exceeded"
    assert res.steps == 25


def test_stalled_cut_after_one_nudge(tmp_path):
    # Text-only turns: one nudge, then stalled.
    turns = [ModelTurn("just talking", []), ModelTurn("still talking", [])]
    res = run(turns, tmp_path)
    assert res.done is False
    assert res.reason == "stalled"


def test_repetition_cut(tmp_path):
    # Same write_file call repeated -> repetition_detected.
    same = lambda: ModelTurn("again", [tc("write_file", path="a.txt", content="x")])
    turns = [same(), same(), same(), same()]
    res = run(turns, tmp_path)
    assert res.reason == "repetition_detected"
    assert res.done is False
