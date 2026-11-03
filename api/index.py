"""Vercel entrypoint for the public, read-only National API."""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Vercel invokes this module from the repository root. Keep the application
# package in its existing backend boundary and fail closed into public mode.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.environ["UPWIND_PUBLIC_READONLY"] = "1"
os.environ.setdefault("UPWIND_NATIONAL_RELEASE_DIR", str(ROOT / "deployment-data" / "release"))
os.environ.setdefault("UPWIND_OSM_ROADS_DIR", str(ROOT / "deployment-data" / "osm_roads" / "raw"))

from upwind.api import app  # noqa: E402

__all__ = ["app"]
