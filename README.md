# axon

A local coding agent that recreates Google Antigravity's **plan, use tools, verify** pattern, powered by **Gemma 4** via Ollama. No Gemini API, no cloud, no code egress. Apache-2.0.

> Open r/ollama and you will find the same unanswered question more than once: *"can I run Google Antigravity with a local model?"* The short answer is no. The Antigravity SDK talks to Google's cloud and that is that. The long answer is the one nobody wrote down: you do not need the SDK to have the brain. Antigravity's brain is a three-beat pattern, plan then use tools then verify, and that pattern is public, documented in the research, and it runs entirely on your laptop with Gemma 4, the Apache-2.0 open-weight model Google published. This repo is that.

## What it is

`axon` is the agent **harness**: the loop, the toolset, the safety policy that turns a local model into an agent that *does the work and verifies it*, instead of an autocomplete that suggests. It is deliberately framework-free (no LangChain). The point is to show the harness naked.

The agent is the runtime. It plans, calls tools (read and write files, run shell, run tests), executes, verifies by running the tests itself, and repeats until done or a cut fires.

## Quick start

```bash
# 1. Have Ollama running with Gemma 4:
ollama pull gemma4:26b

# 2. Install (PyYAML is the only runtime dependency; Ollama is reached over HTTP):
pip install -e .

# 3a. Chat mode (default): open a conversational session in your project
axon --cwd ./myproject

# 3b. Print mode (-p): run one task and exit (for scripts and CI)
axon -p "Fix the failing test in test_calc.py and confirm it passes" --cwd ./myproject

# Or the end-to-end example (creates a buggy repo and fixes it):
python examples/fix_bug.py
```

### Two ways to run it

`axon` works like a familiar agent CLI:

- **`axon`** opens an interactive **chat** session. Context carries across turns, so
  the agent does not re-read what it already knows. A positional task seeds the first turn.
- **`axon -p "task"`** is **print mode**: run the task once, print the result, exit.
  Non-conversational, for scripts and CI.

```
$ axon --cwd ./myproject
axon › fix the login bug
  ✓ done in 6 steps
axon › now add a test for the empty-password case
  ✓ done in 4 steps
axon › /exit
```

Commands in chat: `/exit`, `/quit`, `/reset` (clear the session).

## The pattern (and why it works)

Each design decision is grounded in AI-engineering literature, not vibes:

| Decision | Why | Source |
|---|---|---|
| Harness, not just model | A better harness beats a better model on the same task | harness-design research |
| Verify in the loop | Agents cannot self-evaluate reliably, so verification must be a step | code-as-agent-harness (Ning et al. 2026) |
| Security framing in the system prompt | Framing the agent as a senior security engineer reduces vulnerable output | Pearce et al. 2022 (IEEE S&P) |
| The model is untrusted input | All security lives in the policy engine and jail, never in the prompt | OWASP LLM Top 10 |
| Subagents for context isolation | Offload heavy reads so the parent keeps a clean window | Antigravity's `start_subagent` |

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

- **Non-overridable deny layer**: `rm -rf /`, fork bombs, `curl | sh`, `git push` and similar are blocked regardless of how they are phrased. No config can turn them into ALLOW.
- **Filesystem jail**: paths are resolved and must stay inside the workspace. Traversal and symlink escape are rejected.
- **deny_paths**: `.env`, `.git/`, keys and `.ssh` are never readable or writable.
- **ASK becomes DENY in non-interactive mode**: nothing that would prompt a human gets auto-approved in CI or `--yolo`.
- **Backup before overwrite**: files are backed up before being overwritten. Never blind destruction.

Recommended for autonomous runs: wrap the process in an OS sandbox (firejail or a container) with no network. The regexes catch the obvious; the sandbox catches what they do not.

## Evaluation

`axon` ships with **Gemma-Harness-Bench**: 12 synthetic tasks across 4 categories (bug fixes, features, refactors, multi-step), each verified by execution (a test that must pass), with a pre-registered protocol in `eval/PROTOCOL.md`.

Early results (temp 0, 10 runs per task, same harness):

| Model | Completion | Median steps |
|---|---|---|
| Gemma 4 26B (Q4_K_M) | 120/120 (100%) | 7 to 9 |
| Qwen 3.6 35B | 120/120 (100%) | 5 to 6 |

Both local models sustain agentic loops, including multi-step tool chains, at 100% completion. This runs against the community consensus that Gemma 4 "fails tool-calling": with a harness built for the model, it does not. The no-harness baseline and the full 30-run sweep are next.

```bash
python eval/run_eval.py --model gemma4:26b --temp 0 --runs 30
python eval/run_eval.py --model gemma4:26b --temp 0 --runs 30 --naive   # baseline
```

## Tests

```bash
pytest -q   # 55 tests; the security suite (test_policy.py) is the most important.
```

## License

Apache-2.0. See `LICENSE`.

---

*A study in AI engineering: replicating the brain of a managed Google tool with open Google parts.*
