#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

# Locate a suitable Python 3.12 interpreter
PYTHON_BIN=""
if command -v uv >/dev/null 2>&1; then
  PYTHON_BIN="$(uv python find 3.12 2>/dev/null || true)"
fi
if [ -z "$PYTHON_BIN" ] && command -v python3.12 >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python3.12)"
fi
if [ -z "$PYTHON_BIN" ] && command -v python3 >/dev/null 2>&1; then
  if python3 -c 'import sys; sys.exit(0 if sys.version_info[:2] == (3, 12) else 1)' 2>/dev/null; then
    PYTHON_BIN="$(command -v python3)"
  fi
fi

if [ -z "$PYTHON_BIN" ]; then
  echo "Error: Python 3.12 is required but could not be located." >&2
  echo "Install Python 3.12 or run: uv python install 3.12" >&2
  exit 1
fi

node -e 'const [a,b]=process.versions.node.split(".").map(Number); if(a<22||(a===22&&b<12)) throw Error("Node 22.12+ or 24 required")'
mkdir -p .local

if command -v uv >/dev/null 2>&1; then
  UV_VENV_CLEAR=1 uv venv --python "$PYTHON_BIN" --clear .venv --cache-dir .local/uv-cache
  uv pip install --python .venv/bin/python -r requirements.lock --cache-dir .local/uv-cache
  uv pip install --python .venv/bin/python -e . --no-deps --cache-dir .local/uv-cache
else
  "$PYTHON_BIN" -m venv .venv
  .venv/bin/python -m pip install -r requirements.lock
  .venv/bin/python -m pip install -e . --no-deps
fi
cd frontend
npm ci --cache ../.local/npm-cache --no-audit --no-fund
npm run build
