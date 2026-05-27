# Gemma-Harness-Bench v1 — Evaluation Protocol (pre-registered)

> Pre-register this protocol (git tag) BEFORE running the full sweep. All runs are
> reported, never best-of-N. This document is frozen; results go in `results/`.

## Claim under test

Not "Gemma 4 is better than people say." The defensible claim:

> With a purpose-built harness and under the reproducible conditions below, Gemma 4 26B
> (Q4_K_M, local via Ollama) sustains agentic coding loops — including multi-step tool
> chains — at completion rate Y (CI Z). The community consensus that "Gemma 4 fails
> tool-calling" likely reflects generic harnesses and/or aggressive quantization, not the
> model. We document the conditions under which it works and where it still fails.

## Task set

12 tasks, 4 categories, private and synthetic (anti-contamination — not in public training data):
- **bugfix** (4): A1 pagination, A2 dates, A3 mutable-default, A4 counter
- **feature** (4): B1 slugify, B2 health, B3 cli_json, B4 retry
- **refactor** (2): C1 extract-helper, C2 rename
- **multistep** (2): D1 tax-rate, D2 logging

Each task: a seed repo (frozen), `input.md` (the prompt), `verify.sh` (exit 0 iff solved,
verification by execution not inspection), `meta.json` (category, optimal_steps). Tests are
the executable spec.

## Conditions

- **Runs:** 30 per task per configuration (12 × 30 = 360 runs/config). 30 ≥ CLT threshold.
- **Temperature:** report both temp=0 (deterministic baseline) and temp=0.7 (realistic use).
- **Configurations (the matrix):**
  1. Gemma 4 + harness (the system under test)
  2. Gemma 4 + naive baseline (`--naive`: same security, no harness smarts) — isolates the harness effect
  3. Qwen + harness (same harness, different model) — isolates the model effect
- **Seeds:** fixed and recorded per run.

## Metrics (by category, never a single global headline)

- `completion_rate` per category (with Wilson CI in the writeup)
- `tool_call_success` (separate invalid_format from invalid_action)
- `median_steps` + IQR; `efficiency_ratio` = steps / optimal_steps
- `latency` p50/p90; `cost` = $0 API + GPU-seconds (compute is not free)
- failure taxonomy: solved / wrong_solution / task_limit_exceeded / stalled / repetition_detected / harness_error

## Honesty rules (anti cherry-picking)

- Task set pre-registered before any run (this file's git tag proves it).
- ALL runs reported. Raw JSONL published in `results/`.
- No best-of-N as a headline.
- Declare limits: where Gemma fails (long loops, complex schemas, high temp, aggressive quant).
- Do NOT claim human productivity gains (METR: perception ≠ reality). We measure agent
  capability on controlled tasks, not developer speedup.

## Running

```bash
git tag bench-v1-preregistered            # freeze the task set first
python eval/run_eval.py --model gemma4:26b --temp 0   --runs 30
python eval/run_eval.py --model gemma4:26b --temp 0   --runs 30 --naive
python eval/run_eval.py --model gemma4:26b --temp 0.7 --runs 30
python eval/run_eval.py --model qwen3.6:35b --temp 0  --runs 30
```

## Preliminary (smoke, n=1/task, harness, temp=0)

12/12 solved across all four categories. Not evidence (n=1) — it validates the pipeline
and motivates the full sweep. See `results/`.
