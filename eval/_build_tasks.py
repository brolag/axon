"""Materialize the Gemma-Harness-Bench v1 task set.

Reproducible: anyone can regenerate the seed repos by running this script. The
materialized tasks/ tree is committed so the benchmark is frozen. Each task is:
  tasks/<ID>/
    seed/          starting repo state (the agent works on a copy of this)
    input.md       the prompt given to the agent
    verify.sh      exit 0 iff the task is solved (cwd-independent: takes workspace as $1)
    meta.json      {category, optimal_steps}

Tests serve as the executable spec (SWE-bench style). For bug fixes the seed test
fails; for features the test defines the target behavior.
"""

import json
from pathlib import Path

ROOT = Path(__file__).parent / "tasks"

# verify.sh boilerplate: run pytest in the workspace passed as $1.
PYTEST_VERIFY = '#!/bin/bash\ncd "$1" || exit 1\npython3 -m pytest -q {target} >/dev/null 2>&1\n'


def pytest_verify(target="tests/"):
    return PYTEST_VERIFY.format(target=target)


TASKS = {
    # ---- A: bug fixes (seed test fails; agent fixes the code) -----------------
    "A1_pagination": {
        "category": "bugfix", "optimal_steps": 5,
        "input": "tests/test_pagination.py fails. Find the off-by-one bug in get_page and fix it. Do not modify the test. Confirm tests pass.",
        "seed": {
            "paginate.py": (
                "def get_page(items, page, size):\n"
                "    # page is 1-indexed\n"
                "    start = page * size  # BUG: off by one, should be (page-1)*size\n"
                "    return items[start:start + size]\n"
            ),
            "tests/test_pagination.py": (
                "from paginate import get_page\n\n"
                "def test_first_page():\n"
                "    assert get_page(list(range(10)), 1, 3) == [0, 1, 2]\n\n"
                "def test_second_page():\n"
                "    assert get_page(list(range(10)), 2, 3) == [3, 4, 5]\n"
            ),
        },
        "verify": pytest_verify(),
    },
    "A2_dates": {
        "category": "bugfix", "optimal_steps": 5,
        "input": "tests/test_dates.py fails: parse_date crashes on empty input instead of returning None. Fix it without changing the test. Confirm tests pass.",
        "seed": {
            "dates.py": (
                "from datetime import date\n\n"
                "def parse_date(s):\n"
                "    y, m, d = s.split('-')  # BUG: ValueError on ''\n"
                "    return date(int(y), int(m), int(d))\n"
            ),
            "tests/test_dates.py": (
                "from dates import parse_date\nfrom datetime import date\n\n"
                "def test_valid():\n    assert parse_date('2026-05-27') == date(2026, 5, 27)\n\n"
                "def test_empty_returns_none():\n    assert parse_date('') is None\n"
            ),
        },
        "verify": pytest_verify(),
    },
    "A3_mutable_default": {
        "category": "bugfix", "optimal_steps": 5,
        "input": "tests/test_accumulator.py fails intermittently due to a mutable default argument bug in accumulate. Fix it. Confirm tests pass.",
        "seed": {
            "accumulator.py": (
                "def accumulate(x, lst=[]):  # BUG: shared mutable default\n"
                "    lst.append(x)\n"
                "    return lst\n"
            ),
            "tests/test_accumulator.py": (
                "from accumulator import accumulate\n\n"
                "def test_independent_calls():\n"
                "    assert accumulate(1) == [1]\n"
                "    assert accumulate(2) == [2]\n"
            ),
        },
        "verify": pytest_verify(),
    },
    "A4_counter": {
        "category": "bugfix", "optimal_steps": 5,
        "input": "tests/test_counter.py fails with KeyError because count() does not initialize missing keys. Fix it. Confirm tests pass.",
        "seed": {
            "counter.py": (
                "def count(items):\n"
                "    counts = {}\n"
                "    for it in items:\n"
                "        counts[it] += 1  # BUG: KeyError on first sight\n"
                "    return counts\n"
            ),
            "tests/test_counter.py": (
                "from counter import count\n\n"
                "def test_count():\n    assert count(['a', 'b', 'a']) == {'a': 2, 'b': 1}\n"
            ),
        },
        "verify": pytest_verify(),
    },
    # ---- B: small features (test = spec) --------------------------------------
    "B1_slugify": {
        "category": "feature", "optimal_steps": 5,
        "input": "Implement slugify(text) in slugify.py so the tests in tests/test_slugify.py pass: lowercase ASCII kebab-case, non-alphanumerics become single hyphens, trimmed.",
        "seed": {
            "slugify.py": "def slugify(text):\n    raise NotImplementedError\n",
            "tests/test_slugify.py": (
                "from slugify import slugify\n\n"
                "def test_basic():\n    assert slugify('Hello World') == 'hello-world'\n\n"
                "def test_collapse():\n    assert slugify('  A--B  c ') == 'a-b-c'\n"
            ),
        },
        "verify": pytest_verify(),
    },
    "B2_health": {
        "category": "feature", "optimal_steps": 4,
        "input": "Implement health() in service.py returning {'status': 'ok'} so tests/test_service.py passes.",
        "seed": {
            "service.py": "def health():\n    raise NotImplementedError\n",
            "tests/test_service.py": (
                "from service import health\n\n"
                "def test_health():\n    assert health() == {'status': 'ok'}\n"
            ),
        },
        "verify": pytest_verify(),
    },
    "B3_cli_json": {
        "category": "feature", "optimal_steps": 6,
        "input": "Add a function format_output(data, as_json=False) in formatter.py: when as_json is True return a JSON string, else 'key: value' lines. Make tests/test_formatter.py pass.",
        "seed": {
            "formatter.py": "def format_output(data, as_json=False):\n    raise NotImplementedError\n",
            "tests/test_formatter.py": (
                "import json\nfrom formatter import format_output\n\n"
                "def test_plain():\n    assert format_output({'a': 1}) == 'a: 1'\n\n"
                "def test_json():\n    assert json.loads(format_output({'a': 1}, as_json=True)) == {'a': 1}\n"
            ),
        },
        "verify": pytest_verify(),
    },
    "B4_retry": {
        "category": "feature", "optimal_steps": 6,
        "input": "Implement retry(fn, n) in retry.py: call fn up to n times until it returns without raising; re-raise the last exception if all attempts fail. Make tests/test_retry.py pass.",
        "seed": {
            "retry.py": "def retry(fn, n):\n    raise NotImplementedError\n",
            "tests/test_retry.py": (
                "import pytest\nfrom retry import retry\n\n"
                "def test_succeeds_after_failures():\n"
                "    calls = {'n': 0}\n"
                "    def fn():\n        calls['n'] += 1\n        if calls['n'] < 3:\n            raise ValueError('boom')\n        return 'ok'\n"
                "    assert retry(fn, 5) == 'ok'\n    assert calls['n'] == 3\n\n"
                "def test_reraises():\n"
                "    def always_fail():\n        raise KeyError('x')\n"
                "    with pytest.raises(KeyError):\n        retry(always_fail, 2)\n"
            ),
        },
        "verify": pytest_verify(),
    },
    # ---- C: refactors (behavior invariant) ------------------------------------
    "C1_extract_helper": {
        "category": "refactor", "optimal_steps": 6,
        "input": "shapes.py has three functions that duplicate area-then-format logic. Extract the shared logic into a helper and make all three use it. Tests must stay green.",
        "seed": {
            "shapes.py": (
                "def square_label(s):\n    a = s * s\n    return f'area={a:.2f}'\n\n"
                "def rect_label(w, h):\n    a = w * h\n    return f'area={a:.2f}'\n\n"
                "def circle_label(r):\n    a = 3.14159 * r * r\n    return f'area={a:.2f}'\n"
            ),
            "tests/test_shapes.py": (
                "from shapes import square_label, rect_label, circle_label\n\n"
                "def test_labels():\n"
                "    assert square_label(2) == 'area=4.00'\n"
                "    assert rect_label(2, 3) == 'area=6.00'\n"
                "    assert circle_label(1) == 'area=3.14'\n"
            ),
        },
        "verify": pytest_verify(),
    },
    "C2_rename": {
        "category": "refactor", "optimal_steps": 6,
        "input": "In store.py, rename the variable 'data' to 'records' everywhere without breaking anything. Tests must stay green and the identifier 'data' must not remain.",
        "seed": {
            "store.py": (
                "def load():\n    data = [1, 2, 3]\n    return data\n\n"
                "def total():\n    data = load()\n    return sum(data)\n"
            ),
            "tests/test_store.py": (
                "from store import load, total\n\n"
                "def test_store():\n    assert load() == [1, 2, 3]\n    assert total() == 6\n"
            ),
        },
        "verify": (
            '#!/bin/bash\ncd "$1" || exit 1\n'
            "python3 -m pytest -q tests/ >/dev/null 2>&1 || exit 1\n"
            "! grep -qE '\\bdata\\b' store.py\n"
        ),
    },
    # ---- D: multi-step (require chained tool use) -----------------------------
    "D1_tax_rate": {
        "category": "multistep", "optimal_steps": 7,
        "input": "The sales tax rate must change from 0.10 to 0.13. Find where calculate_tax is defined, update the rate, run the tests, and if fixtures assume the old rate update them too. Confirm all tests pass.",
        "seed": {
            "billing/__init__.py": "",
            "billing/tax.py": (
                "RATE = 0.10  # update to 0.13\n\n"
                "def calculate_tax(amount):\n    return round(amount * RATE, 2)\n"
            ),
            "tests/test_tax.py": (
                "from billing.tax import calculate_tax\n\n"
                "def test_tax():\n"
                "    # fixture assumes 0.13 rate\n"
                "    assert calculate_tax(100) == 13.0\n"
            ),
        },
        "verify": pytest_verify(),
    },
    "D2_logging": {
        "category": "multistep", "optimal_steps": 8,
        "input": "Add a print-based log line 'CALL <funcname>' at the start of each of the three functions in payments.py, then run tests/test_payments.py which checks the log output. Confirm tests pass.",
        "seed": {
            "payments.py": (
                "def charge(amount):\n    return amount\n\n"
                "def refund(amount):\n    return -amount\n\n"
                "def balance(a, b):\n    return a + b\n"
            ),
            "tests/test_payments.py": (
                "import io\nfrom contextlib import redirect_stdout\nimport payments\n\n"
                "def _logs(fn, *args):\n"
                "    buf = io.StringIO()\n"
                "    with redirect_stdout(buf):\n        fn(*args)\n"
                "    return buf.getvalue()\n\n"
                "def test_logs():\n"
                "    assert 'CALL charge' in _logs(payments.charge, 10)\n"
                "    assert 'CALL refund' in _logs(payments.refund, 5)\n"
                "    assert 'CALL balance' in _logs(payments.balance, 1, 2)\n"
            ),
        },
        "verify": pytest_verify(),
    },
}


def build():
    for tid, spec in TASKS.items():
        tdir = ROOT / tid
        seed = tdir / "seed"
        seed.mkdir(parents=True, exist_ok=True)
        for rel, content in spec["seed"].items():
            f = seed / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(content)
        (tdir / "input.md").write_text(spec["input"] + "\n")
        vf = tdir / "verify.sh"
        vf.write_text(spec["verify"])
        vf.chmod(0o755)
        (tdir / "meta.json").write_text(json.dumps(
            {"id": tid, "category": spec["category"], "optimal_steps": spec["optimal_steps"]}, indent=2
        ) + "\n")
    print(f"built {len(TASKS)} tasks into {ROOT}")


if __name__ == "__main__":
    build()
