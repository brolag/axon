"""Tool registry: maps tool names to handlers and exposes JSON schemas to Ollama."""

from __future__ import annotations

from .control import done
from .fs import list_dir, read_file, write_file
from .shell import run_shell, run_tests
from .subagent import start_subagent

# name -> handler(args, ctx) -> ToolResult
HANDLERS = {
    "read_file": read_file,
    "write_file": write_file,
    "list_dir": list_dir,
    "run_shell": run_shell,
    "run_tests": run_tests,
    "start_subagent": start_subagent,
    "done": done,
}

# JSON schemas in Ollama/OpenAI tool format.
SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": (
                "Read a file from the workspace. Returns text with line numbers. "
                "Do NOT re-read a file already in your context unless you expect it changed."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path relative to the workspace."},
                    "start_line": {"type": "integer", "description": "Start line, 1-indexed (optional)."},
                    "end_line": {"type": "integer", "description": "End line inclusive (optional)."},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": (
                "Create or overwrite a file with the given content. Creates parent dirs. "
                "For partial edits, read-modify-write the whole file."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path relative to the workspace."},
                    "content": {"type": "string", "description": "Full file content."},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "List files and subdirectories. Prefer this over 'ls' via run_shell.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path (default: workspace root)."},
                    "recursive": {"type": "boolean", "description": "Recursive listing (default false)."},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_shell",
            "description": (
                "Run a shell command in the workspace; returns exit code, stdout and stderr. "
                "Subject to the safety policy: destructive commands are blocked."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The command to run."},
                    "timeout_sec": {"type": "integer", "description": "Timeout seconds (default 60, max 300)."},
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_tests",
            "description": (
                "Run the test suite (pytest by default) and return the result. "
                "Prefer this over invoking pytest via run_shell."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "Specific test file or node (optional)."},
                    "test_command": {"type": "string", "description": "Override command (default 'pytest -q')."},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "start_subagent",
            "description": (
                "Launch a subagent with ISOLATED context for a bounded task (e.g. read a large "
                "codebase and summarize it). It does NOT share your history and returns only its "
                "final synthesis. Use it to avoid saturating your own context window."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {"type": "string", "description": "Self-contained instruction for the subagent."},
                    "allowed_paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Paths the subagent may read (optional).",
                    },
                    "max_steps": {"type": "integer", "description": "Step cap for the subagent (default 10)."},
                },
                "required": ["task"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "done",
            "description": (
                "Signal the task is complete. Call ONLY after you verified the result "
                "(e.g. tests pass). Include a summary and the verification evidence."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string", "description": "What was done and how it was verified."},
                    "verified": {"type": "boolean", "description": "True if verification (tests/run) passed."},
                },
                "required": ["summary"],
            },
        },
    },
]

# Reduced toolset for subagents: read-only, no shell mutation, no nested subagents.
SUBAGENT_TOOL_NAMES = {"read_file", "list_dir", "run_shell", "done"}


def subagent_schemas() -> list[dict]:
    return [s for s in SCHEMAS if s["function"]["name"] in SUBAGENT_TOOL_NAMES]
