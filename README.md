# axon

A local coding agent that recreates Google Antigravity's **plan → tool → verify** pattern, powered by **Gemma 4** via Ollama. No Gemini API, no cloud, no code egress. Apache-2.0.

> Open r/ollama and you'll find the same unanswered question more than once: *"can I run Google Antigravity with a local model?"* The short answer is no — the Antigravity SDK talks to Google's cloud and that's that. The long answer is the one nobody wrote: you don't need the SDK to have the brain. Antigravity's brain is a three-beat pattern — plan, use tools, verify — and that pattern is public, it's in the papers, and it runs entirely on your laptop with Gemma 4, the Apache-2.0 open-weight model Google published. This repo is that.

## What it is

`axon` is the agent **harness** — the loop, the toolset, the safety policy — that turns a local model into an agent that *does the work and verifies it*, instead of an autocomplete that suggests. It is deliberately framework-free (no LangChain): the point is to show the harness naked.

The agent is the runtime: it plans, calls tools (read/write files, run shell, run tests), executes, verifies (runs the tests itself), and repeats until done or a cut fires.

## Quick start

```bash
# 1. Have Ollama running with Gemma 4:
ollama pull gemma4:26b

# 2. Install (PyYAML is the only runtime dependency; Ollama is reached over HTTP):
pip install -e .

# 3. Run the agent against a workspace:
axon "Fix the failing test in test_calc.py and confirm it passes" --cwd ./myproject

# Or the end-to-end example (creates a buggy repo and fixes it):
python examples/fix_bug.py
```

## The pattern (and why it works)

Each design decision is grounded in AI-engineering literature, not vibes:

| Decision | Why | Source |
|---|---|---|
| Harness, not just model | A better harness beats a better model on the same task | harness-design research |
| Verify in the loop | Agents can't self-evaluate reliably; verification must be a step | code-as-agent-harness (Ning et al. 2026) |
| Security framing in the system prompt | Framing the agent as a senior security engineer reduces vulnerable output | Pearce et al. 2022 (IEEE S&P) |
| The model is untrusted input | All security lives in the policy engine + jail, never in the prompt | OWASP LLM Top 10 |
| Subagents for context isolation | Offload heavy reads; the parent keeps a clean window | Antigravity's `start_subagent` |

## Architecture

```
axon/
  policy.py      # PolicyEngine: allow/ask/deny, filesystem jail, non-overridable deny layer
  client.py      # Ollama over HTTP (stdlib only). Validates tool-call shape.
  session.py     # state: messages, step counter, token budget, redundancy caches
  loop.py        # the agentic loop + four cuts: done / max_steps / stalled / repetition
  dispatch.py    # single path for tools: cache, repetition nudge, budget, transcript
  prompt.py      # TemplatedSystemInstructions (fixed security scaffold + injectable role)
  tools/         # read_file, write_file, list_dir, run_shell, run_tests, start_subagent, done
  artifacts.py   # the structured, verifiable transcript (artifacts over raw logs)
```

### Safety

The model is treated as untrusted input. Every shell command and file path passes through `PolicyEngine` (`policy.yaml`):

- **Non-overridable deny layer**: `rm -rf /`, fork bombs, `curl | sh`, `git push`, etc. are blocked regardless of how they're phrased. No config can turn them into ALLOW.
- **Filesystem jail**: paths are resolved and must stay inside the workspace. Traversal and symlink escape are rejected.
- **deny_paths**: `.env`, `.git/`, keys, `.ssh` are never readable or writable.
- **ASK → DENY in non-interactive mode**: nothing that would prompt a human gets auto-approved in CI / `--yolo`.
- **Backup before overwrite**: files are backed up before being overwritten. Never blind destruction.

Recommended for autonomous runs: wrap the process in an OS sandbox (firejail / container) with no network. The regexes catch the obvious; the sandbox catches what they don't.

## Tests

```bash
pytest -q   # 55 tests; the security suite (test_policy.py) is the most important.
```

## Status

Harness functional and verified end-to-end against `gemma4:26b` (fixes a failing test in 6 steps, autonomously). Evaluation suite (`Gemma-Harness-Bench`) in progress — see the eval protocol.

---

*Built as a study in AI engineering: replicating the brain of a managed Google tool with open Google parts.*
