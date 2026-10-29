#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PYTHON="${UPWIND_PYTHON:-.venv/bin/python}"
DATA_ROOT="${UPWIND_DEPLOYMENT_DATA_DIR:-deployment-data}"
RELEASE_DIR="$DATA_ROOT/release"
RAW_DIR="$DATA_ROOT/raw"
OSM_DIR="$DATA_ROOT/osm_roads/raw"

"$PYTHON" scripts/build_national_dataset.py \
  --start-year 2018 --end-year 2025 \
  --raw-dir "$RAW_DIR" --release-dir "$RELEASE_DIR"
"$PYTHON" scripts/evaluate_national_v2.py --release-dir "$RELEASE_DIR"
"$PYTHON" scripts/acquire_osm_roads.py --output-dir "$OSM_DIR"
"$PYTHON" scripts/verify_release_bundle.py --release-dir "$RELEASE_DIR" --roads-dir "$OSM_DIR"
