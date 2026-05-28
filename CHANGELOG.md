# Changelog

All notable changes to axon are documented here. Format based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- **Chat by default, `-p` for print mode**: bare `axon` opens an interactive chat
  session (context carries across turns; commands `/exit`, `/quit`, `/reset`).
  `axon -p "task"` runs one task and exits, for scripts and CI. A positional task
  in chat mode seeds the first turn.
- Documentation site (Astro) under `site/`, deployable to GitHub Pages.
- Hero asset and neural-motif SVG under `assets/`.
- `axon` console entry point and `install.sh` installer with Ollama preflight checks.

## [0.1.0] - 2026-05-27

First working release. The harness recreates Google Antigravity's
plan/use-tools/verify pattern on a local model via Ollama, with no Gemini API,
no cloud, and no code egress.

### Added
- **Agentic loop** (`loop.py`) with four termination cuts: `done`, `max_steps`,
  `stalled`, `repetition_detected`. Multi-turn stateful sessions.
- **PolicyEngine** (`policy.py`): three verdicts (allow/ask/deny) with a
  non-overridable hardening deny layer, a filesystem jail, and `deny_paths`.
  `ASK` becomes `DENY` in non-interactive mode.
- **Toolset** (`tools/`): `read_file`, `write_file`, `list_dir`, `run_shell`,
  `run_tests`, `start_subagent` (depth-capped, read-only), `done`.
- **Dispatcher** (`dispatch.py`): single path for all tools with a redundancy
  cache, repetition nudge, token accounting, and a structured transcript.
- **TemplatedSystemInstructions** (`prompt.py`): fixed security scaffold plus an
  injectable role, with a naive baseline mode for evaluation.
- **Ollama client** (`client.py`): HTTP over stdlib `urllib`, no client library,
  tolerant tool-call parsing.
- **Artifacts** (`artifacts.py`): verifiable transcript as Markdown and JSONL.
- **CLI** (`axon`) with a model/host preflight check.
- **Gemma-Harness-Bench** (`eval/`): 12 synthetic tasks across 4 categories,
  a runner with failure taxonomy, a no-harness baseline mode, and a
  pre-registered protocol.
- 55 tests, security suite first.

### Verified
- End-to-end against `gemma4:26b`: fixes a failing test autonomously in 6 steps.
- Both Gemma 4 26B and Qwen 3.6 35B reach 100% completion on the benchmark with
  the harness (10 runs per task, temp 0).
