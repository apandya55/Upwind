#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

# Kill stale server on port 8000 if lingering
kill -9 $(lsof -t -i:8000) 2>/dev/null || true

PYTHON_BIN=".venv/bin/python"
if [ ! -x "$PYTHON_BIN" ]; then
  PYTHON_BIN="$(which python3)"
fi

UVICORN_BIN=".venv/bin/uvicorn"
if [ ! -x "$UVICORN_BIN" ]; then
  UVICORN_BIN="$PYTHON_BIN -m uvicorn"
fi

export PYTHONPATH="backend:${PYTHONPATH:-}"

# Bind to loopback: private, unauthenticated local application.
$UVICORN_BIN upwind.api:app --app-dir backend --host 127.0.0.1 --port 8000 &
upwind_api_pid=$!
cleanup() { kill "$upwind_api_pid" 2>/dev/null || true; }
trap cleanup EXIT INT TERM

$PYTHON_BIN - <<'PY'
import time, urllib.request
for _ in range(50):
    try:
        with urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=1) as r:
            if r.status == 200:
                break
    except OSError:
        time.sleep(.2)
else:
    raise SystemExit('API did not become ready within 10 seconds')
PY

kill -0 "$upwind_api_pid" 2>/dev/null || { echo 'API process exited; check whether port 8000 is already occupied.' >&2; exit 1; }
cd frontend
npm run dev -- --port 5173 --strictPort
