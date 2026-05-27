"""Example: the agent fixes a failing test end-to-end, through the full harness.

This recreates the gate test, but now with policy gating, hooks, anti-redundancy
and verification all in the loop. Run it against a local Gemma 4 via Ollama:

    python examples/fix_bug.py
"""

import tempfile
from pathlib import Path

from axon.artifacts import to_markdown
from axon.loop import run_agent

BUGGY = "def add(a, b):\n    return a - b  # BUG: subtracts instead of adding\n"
TEST = "from calc import add\n\n\ndef test_add():\n    assert add(2, 3) == 5\n"


def main():
    with tempfile.TemporaryDirectory() as d:
        ws = Path(d)
        (ws / "calc.py").write_text(BUGGY)
        (ws / "test_calc.py").write_text(TEST)

        result = run_agent(
            task="test_calc.py fails. Find the bug, fix it, and confirm the test passes by running it.",
            cwd=ws,
            policy_path=str(Path(__file__).parent.parent / "policy.yaml"),
            identity="You are a bug-fixing agent for a small Python project.",
            interactive=False,  # autonomous; ASK -> DENY
        )

        print(to_markdown(result))
        print("\n--- final calc.py ---")
        print((ws / "calc.py").read_text())
        print(f"--- result: {result.reason} in {result.steps} steps, verified={result.done} ---")


if __name__ == "__main__":
    main()
