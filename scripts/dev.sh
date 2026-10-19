#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# Bind to loopback: this is a private, unauthenticated local application.
.venv/bin/uvicorn upwind.api:app --host 127.0.0.1 --port 8000 &
upwind_api_pid=$!
cleanup() { kill "$upwind_api_pid" 2>/dev/null || true; }
trap cleanup EXIT INT TERM
.venv/bin/python - <<'PY'
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
