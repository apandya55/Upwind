"""Use isolated synthetic release data when backend tests run without a bundle."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

from scripts.create_test_release import create


def pytest_configure(config) -> None:
    temporary = tempfile.TemporaryDirectory(prefix="upwind-test-release-")
    root = Path(temporary.name)
    release_dir = os.environ.get("UPWIND_NATIONAL_RELEASE_DIR")
    roads_dir = os.environ.get("UPWIND_OSM_ROADS_DIR")
    if release_dir and roads_dir and (Path(release_dir) / "manifest.json").is_file():
        os.environ["UPWIND_NATIONAL_RELEASE_DIR"] = release_dir
        os.environ["UPWIND_OSM_ROADS_DIR"] = roads_dir
    else:
        create(root)
        os.environ["UPWIND_NATIONAL_RELEASE_DIR"] = str(root / "release")
        os.environ["UPWIND_OSM_ROADS_DIR"] = str(root / "context" / "osm_roads" / "raw")
    os.environ["UPWIND_DATA_DIR"] = str(root / "workspace")
    config._upwind_test_release = temporary
