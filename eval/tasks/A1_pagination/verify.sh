#!/bin/bash
cd "$1" || exit 1
python3 -m pytest -q tests/ >/dev/null 2>&1
