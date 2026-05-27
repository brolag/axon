"""Gemma-Harness-Bench runner.

Runs each task N times, classifies the outcome (failure taxonomy), and writes raw
JSONL plus an aggregated summary by category. Supports the harness vs naive-baseline
comparison and arbitrary local models, so the same script produces the whole
{Gemma+harness, Gemma+naive, Qwen+harness} matrix.

Usage:
    python eval/run_eval.py --model gemma4:26b --temp 0 --runs 30
    python eval/run_eval.py --model gemma4:26b --temp 0 --runs 30 --naive   # baseline
    python eval/run_eval.py --runs 1 --smoke                                 # quick pipeline check

Reproducibility: pre-register the task set (git tag) before running. All runs are
recorded, not best-of-N.
"""

from __future__ import annotations

import argparse
import json
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO))

from localgravity.loop import run_agent  # noqa: E402

TASKS_DIR = Path(__file__).parent / "tasks"
POLICY = str(REPO / "policy.yaml")

# Failure taxonomy (AgentBench-style).
SOLVED = "solved"
WRONG = "wrong_solution"            # agent called done but verify failed
LIMIT = "task_limit_exceeded"
STALLED = "stalled"
REPETITION = "repetition_detected"
ERROR = "harness_error"


def load_tasks(only: list[str] | None = None) -> list[dict]:
    tasks = []
    for tdir in sorted(TASKS_DIR.iterdir()):
        if not tdir.is_dir():
            continue
        if only and tdir.name not in only:
            continue
        meta = json.loads((tdir / "meta.json").read_text())
        meta["dir"] = tdir
        meta["input"] = (tdir / "input.md").read_text().strip()
        tasks.append(meta)
    return tasks


def verify(task: dict, workspace: Path) -> bool:
    proc = subprocess.run(
        ["bash", str(task["dir"] / "verify.sh"), str(workspace)],
        capture_output=True, text=True, timeout=120,
    )
    return proc.returncode == 0


def classify(done: bool, reason: str, passed: bool) -> str:
    if passed:
        return SOLVED
    if done and not passed:
        return WRONG
    if reason == "max_steps_exceeded":
        return LIMIT
    if reason in (STALLED, REPETITION):
        return reason
    return ERROR


def run_one(task: dict, args, run_idx: int) -> dict:
    with tempfile.TemporaryDirectory() as d:
        ws = Path(d)
        shutil.copytree(task["dir"] / "seed", ws, dirs_exist_ok=True)
        t0 = time.time()
        outcome = {"reason": "harness_error", "done": False, "steps": 0, "tool_calls": 0}
        try:
            result = run_agent(
                task=task["input"],
                cwd=ws,
                model=args.model,
                host=args.host,
                temperature=args.temp,
                policy_path=POLICY,
                identity="You are a coding agent solving a bounded task in this repository.",
                interactive=False,
                naive=args.naive,
            )
            tool_calls = sum(1 for e in result.session.transcript if e.kind == "tool_call")
            outcome = {"reason": result.reason, "done": result.done, "steps": result.steps, "tool_calls": tool_calls}
            passed = verify(task, ws)
        except Exception as e:  # noqa: BLE001 - record, don't crash the sweep
            passed = False
            outcome["error"] = repr(e)[:200]
        latency = round(time.time() - t0, 2)

    rec = {
        "task": task["id"],
        "category": task["category"],
        "optimal_steps": task["optimal_steps"],
        "run": run_idx,
        "model": args.model,
        "temp": args.temp,
        "naive": args.naive,
        "passed": passed,
        "outcome": classify(outcome["done"], outcome["reason"], passed),
        "reason": outcome["reason"],
        "steps": outcome["steps"],
        "tool_calls": outcome["tool_calls"],
        "latency_sec": latency,
    }
    if "error" in outcome:
        rec["error"] = outcome["error"]
    return rec


def aggregate(records: list[dict]) -> dict:
    by_cat: dict[str, list[dict]] = {}
    for r in records:
        by_cat.setdefault(r["category"], []).append(r)

    summary = {}
    for cat, recs in sorted(by_cat.items()):
        n = len(recs)
        solved = sum(1 for r in recs if r["passed"])
        steps = [r["steps"] for r in recs if r["steps"]]
        lat = [r["latency_sec"] for r in recs]
        fails: dict[str, int] = {}
        for r in recs:
            if not r["passed"]:
                fails[r["outcome"]] = fails.get(r["outcome"], 0) + 1
        summary[cat] = {
            "runs": n,
            "completion_rate": round(solved / n, 3) if n else 0,
            "median_steps": statistics.median(steps) if steps else None,
            "p50_latency": round(statistics.median(lat), 1) if lat else None,
            "failure_classes": fails,
        }
    total = len(records)
    overall = sum(1 for r in records if r["passed"])
    summary["_overall"] = {"runs": total, "completion_rate": round(overall / total, 3) if total else 0}
    return summary


def main(argv=None):
    p = argparse.ArgumentParser(description="Gemma-Harness-Bench runner")
    p.add_argument("--model", default="gemma4:26b")
    p.add_argument("--host", default=None)
    p.add_argument("--temp", type=float, default=0.0)
    p.add_argument("--runs", type=int, default=30)
    p.add_argument("--naive", action="store_true", help="Baseline: no harness smarts.")
    p.add_argument("--tasks", nargs="*", default=None, help="Subset of task IDs.")
    p.add_argument("--smoke", action="store_true", help="1 run per task, ignore --runs.")
    p.add_argument("--out", default=None, help="Output dir (default: results/<tag>).")
    args = p.parse_args(argv)

    runs = 1 if args.smoke else args.runs
    tasks = load_tasks(args.tasks)
    tag = f"{args.model.replace(':', '_').replace('/', '_')}_temp{args.temp}_{'naive' if args.naive else 'harness'}"
    out_dir = Path(args.out) if args.out else (Path(__file__).parent.parent / "results" / tag)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"running {len(tasks)} tasks x {runs} runs | model={args.model} temp={args.temp} naive={args.naive}")
    records = []
    jsonl_path = out_dir / "runs.jsonl"
    with jsonl_path.open("w") as jf:
        for task in tasks:
            for i in range(runs):
                rec = run_one(task, args, i)
                records.append(rec)
                jf.write(json.dumps(rec, ensure_ascii=False) + "\n")
                jf.flush()
                mark = "PASS" if rec["passed"] else f"FAIL({rec['outcome']})"
                print(f"  {task['id']} run {i}: {mark} {rec['steps']}st {rec['latency_sec']}s")

    summary = aggregate(records)
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    print("\n=== SUMMARY by category ===")
    for cat, s in summary.items():
        print(f"  {cat}: {json.dumps(s, ensure_ascii=False)}")
    print(f"\nraw: {jsonl_path}\nsummary: {out_dir / 'summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
