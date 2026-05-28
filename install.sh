#!/bin/bash
# axon installer.
# Verifies prerequisites, pulls the model, installs the package, runs the tests.
set -e

MODEL="${AXON_MODEL:-gemma4:26b}"
HOST="${AXON_HOST:-http://localhost:11434}"

say() { printf "\033[1;36m==>\033[0m %s\n" "$1"; }
warn() { printf "\033[1;33m!!\033[0m %s\n" "$1"; }
die() { printf "\033[1;31mxx\033[0m %s\n" "$1" >&2; exit 1; }

cd "$(dirname "$0")"

# 1. Python >= 3.10
say "Checking Python..."
PY="$(command -v python3 || true)"
[ -n "$PY" ] || die "python3 not found. Install Python 3.10+."
"$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' \
  || die "Python 3.10+ required (found $($PY --version))."
say "Python OK: $($PY --version)"

# 2. Ollama present
say "Checking Ollama..."
if ! command -v ollama >/dev/null 2>&1; then
  warn "ollama not found on PATH. Install it from https://ollama.com and re-run."
  warn "(If Ollama runs on another host, set AXON_HOST and skip the pull.)"
else
  say "Ollama OK: $(ollama --version 2>/dev/null | head -1)"
fi

# 3. Ollama reachable + model present
say "Checking Ollama at $HOST ..."
if curl -sf "$HOST/api/tags" >/dev/null 2>&1; then
  if curl -sf "$HOST/api/tags" 2>/dev/null | grep -q "${MODEL%%:*}"; then
    say "Model '$MODEL' is available."
  else
    say "Pulling model '$MODEL' (this can take a while)..."
    ollama pull "$MODEL" || warn "Could not pull $MODEL automatically. Pull it manually: ollama pull $MODEL"
  fi
else
  warn "Ollama not reachable at $HOST. Start it with 'ollama serve', then pull: ollama pull $MODEL"
fi

# 4. Install the package. pipx gives a real global command (isolated, on PATH,
#    independent of this repo) like Claude Code. Falls back to pip if pipx is absent.
if command -v pipx >/dev/null 2>&1; then
  say "Installing axon globally with pipx..."
  pipx install --force . || die "pipx install failed."
  GLOBAL=1
else
  warn "pipx not found. Installing editable with pip (the 'axon' command is tied to this repo)."
  warn "For a clean global install: 'brew install pipx' (or 'pip install pipx'), then re-run."
  "$PY" -m pip install -e . -q || die "pip install failed."
  GLOBAL=0
fi

# 5. Verify with the test suite (no model calls)
say "Running tests..."
"$PY" -m pytest -q || die "tests failed — installation is not healthy."

say "Done. axon is on your PATH; run it from any project:"
echo "    axon --cwd ./your-project              # interactive chat"
echo "    axon -p \"fix the failing test\" --cwd ./your-project   # one-shot"
[ "${GLOBAL:-0}" = "1" ] && echo "    (installed globally via pipx, independent of this repo)"
