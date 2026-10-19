#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -c 'import sys; assert sys.version_info >= (3,12), "Python 3.12+ required"'
node -e 'const [a,b]=process.versions.node.split(".").map(Number); if(a<22||(a===22&&b<12)) throw Error("Node 22.12+ or 24 required")'
mkdir -p .local
if command -v uv >/dev/null 2>&1; then
  uv venv --python python3 --allow-existing .venv --cache-dir .local/uv-cache
  uv pip install --python .venv/bin/python -r requirements.lock --cache-dir .local/uv-cache
  uv pip install --python .venv/bin/python -e . --no-deps --cache-dir .local/uv-cache
else
  python3 -m venv .venv
  .venv/bin/python -m pip install -r requirements.lock
  .venv/bin/python -m pip install -e . --no-deps
fi
cd frontend
npm ci --cache ../.local/npm-cache --no-audit --no-fund
npm run build
