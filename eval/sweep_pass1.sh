#!/bin/bash
# First-pass sweep: 10 runs/task, temp 0, harness vs naive. Validates the signal
# before committing to the full 30-run sweep.
set -e
cd "$(dirname "$0")/.."
PY=/opt/homebrew/bin/python3.11
export PYTHONPATH=.

echo "=== PASS 1: harness, 10 runs, temp 0 ==="
"$PY" eval/run_eval.py --model gemma4:26b --temp 0 --runs 10

echo "=== PASS 1: naive baseline, 10 runs, temp 0 ==="
"$PY" eval/run_eval.py --model gemma4:26b --temp 0 --runs 10 --naive

echo "=== PASS 1 COMPLETE ==="
