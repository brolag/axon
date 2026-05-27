"""CLI entrypoint: localgravity "task" [options]."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .artifacts import to_markdown
from .loop import run_agent


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="localgravity",
        description="A local coding agent recreating Antigravity's plan-tool-verify pattern, powered by Gemma 4.",
    )
    parser.add_argument("task", help="The task for the agent.")
    parser.add_argument("--cwd", default=".", help="Workspace root (the jail). Default: current dir.")
    parser.add_argument("--model", default="gemma4:26b", help="Ollama model. Default: gemma4:26b.")
    parser.add_argument("--host", default=None, help="Ollama host (e.g. http://localhost:11434).")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--policy", default=str(Path(__file__).parent.parent / "policy.yaml"))
    parser.add_argument("--max-steps", type=int, default=None, help="Override max steps.")
    parser.add_argument("--yolo", action="store_true", help="Non-interactive: ASK becomes DENY, no prompts.")
    parser.add_argument("--identity", default="You are a maintenance agent for this repository.")
    args = parser.parse_args(argv)

    result = run_agent(
        task=args.task,
        cwd=args.cwd,
        model=args.model,
        host=args.host,
        temperature=args.temperature,
        policy_path=args.policy,
        identity=args.identity,
        interactive=not args.yolo,
    )

    print(to_markdown(result), file=sys.stderr)
    print(f"\nResult: {result.reason} in {result.steps} steps.")
    return 0 if result.done else 1


if __name__ == "__main__":
    raise SystemExit(main())
