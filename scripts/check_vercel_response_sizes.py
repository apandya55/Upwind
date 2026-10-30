#!/usr/bin/env python3
"""Measure representative National API JSON bodies against Vercel's limit."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.environ["UPWIND_PUBLIC_READONLY"] = "1"
os.environ.setdefault("UPWIND_NATIONAL_RELEASE_DIR", str(ROOT / "deployment-data" / "release"))
os.environ.setdefault("UPWIND_OSM_ROADS_DIR", str(ROOT / "deployment-data" / "osm_roads" / "raw"))

from upwind import api  # noqa: E402


def serialized_size(payload: dict) -> int:
    return len(JSONResponse(content=jsonable_encoder(payload)).body)


def measure() -> dict[str, int]:
    bounds = {"west": -180, "south": -85, "east": 180, "north": 85}
    payloads = {
        "places-all": api.national_places(limit=10_000),
        "places-search-a": api.national_places(q="a", limit=10_000),
        "places-search-e": api.national_places(q="e", limit=10_000),
        "places-search-r": api.national_places(q="r", limit=10_000),
        "monitors-all-years": api.national_monitors(year=-1, limit=10_000),
        "sources-global": api.national_sources(**bounds, limit=3_000),
        "viewport-estimates-global": api.national_viewport(layer="estimates", **bounds, zoom=3, budget=3_000),
        "viewport-monitors-global": api.national_viewport(layer="monitors", **bounds, zoom=3, budget=3_000),
        "viewport-sources-global": api.national_viewport(layer="sources", **bounds, zoom=3, budget=3_000),
    }
    return {name: serialized_size(payload) for name, payload in payloads.items()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-bytes", type=int, default=4 * 1024 * 1024,
                        help="Maximum response body size; defaults to 4 MiB for Vercel headroom")
    args = parser.parse_args()
    if args.max_bytes < 1:
        parser.error("--max-bytes must be positive")

    sizes = measure()
    print(json.dumps({"max_bytes": args.max_bytes, "responses": sizes}, indent=2, sort_keys=True))
    oversized = {name: size for name, size in sizes.items() if size > args.max_bytes}
    if oversized:
        details = ", ".join(f"{name}={size}" for name, size in sorted(oversized.items()))
        print(f"ERROR: response bodies exceed {args.max_bytes} bytes: {details}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
