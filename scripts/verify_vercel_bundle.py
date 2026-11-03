#!/usr/bin/env python3
"""Verify that the Vercel National API data bundle is complete and valid."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = ROOT / "deployment-data"
RELEASE_FILES = ("manifest.json", "places.json", "model.json", "monitors.json", "sources.json")
ROAD_FILES = tuple(f"{city}.{suffix}" for city in ("durham", "charlotte") for suffix in ("osm", "metadata.json"))
# Reserve headroom for the Python runtime, application source, and dependencies
# inside Vercel's 500 MB uncompressed function bundle limit.
MAX_DATA_BYTES = 400 * 1024 * 1024


def _required_files(data_root: Path, roads_root: Path) -> list[Path]:
    return [data_root / "release" / name for name in RELEASE_FILES] + [roads_root / name for name in ROAD_FILES]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify(data_root: Path, *, roads_root: Path | None = None, allow_synthetic: bool = False, max_bytes: int = MAX_DATA_BYTES) -> dict:
    data_root = data_root.expanduser().resolve()
    roads_root = (roads_root or data_root / "osm_roads" / "raw").expanduser().resolve()
    try:
        roads_root.relative_to(data_root)
    except ValueError as exc:
        raise RuntimeError("OSM roads directory must be inside the Vercel data root") from exc
    files = _required_files(data_root, roads_root)
    missing = [str(path) for path in files if not path.is_file() or path.stat().st_size == 0]
    if missing:
        raise RuntimeError("Missing Vercel API data artifacts:\n" + "\n".join(missing))

    release_root = data_root / "release"
    try:
        decoded = {name: json.loads((release_root / name).read_text()) for name in RELEASE_FILES}
        road_metadata = {
            name: json.loads((roads_root / name).read_text())
            for name in ("durham.metadata.json", "charlotte.metadata.json")
        }
        osm_roots = {
            name: ElementTree.parse(roads_root / name).getroot()
            for name in ("durham.osm", "charlotte.osm")
        }
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ElementTree.ParseError) as exc:
        raise RuntimeError(f"Vercel API data artifacts are unreadable: {exc}") from exc

    release_id = str(decoded["manifest.json"].get("release", ""))
    if not release_id:
        raise RuntimeError("manifest.json does not declare a release identity")
    if release_id.startswith("upwind-test-fixture-") and not allow_synthetic:
        raise RuntimeError("Synthetic test fixture refused as a production Vercel data bundle")
    if not isinstance(decoded["places.json"], list) or not isinstance(decoded["monitors.json"], list) or not isinstance(decoded["sources.json"], list):
        raise RuntimeError("places.json, monitors.json, and sources.json must contain arrays")
    if not isinstance(decoded["model.json"], dict):
        raise RuntimeError("model.json must contain an object")
    for name, metadata in road_metadata.items():
        if not isinstance(metadata, dict) or not metadata.get("retrieved_utc") or not metadata.get("attribution"):
            raise RuntimeError(f"{name} must retain retrieval and attribution metadata")
    for name, root in osm_roots.items():
        if root.tag != "osm" or root.find("bounds") is None:
            raise RuntimeError(f"{name} is not a bounded OSM XML extract")

    total_bytes = sum(path.stat().st_size for path in files)
    if total_bytes > max_bytes:
        raise RuntimeError(f"Required Vercel data artifacts total {total_bytes} bytes; limit is {max_bytes}")
    hashes = {str(path.relative_to(data_root)): _sha256(path) for path in files}
    return {
        "release": release_id,
        "required_file_count": len(files),
        "required_bytes": total_bytes,
        "max_bytes": max_bytes,
        "sha256": hashes,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--roads-dir", type=Path, help="Override the OSM directory; used by the isolated test fixture")
    parser.add_argument("--allow-synthetic", action="store_true", help="Permit the isolated test fixture; never use for production deployment")
    parser.add_argument("--max-bytes", type=int, default=MAX_DATA_BYTES)
    args = parser.parse_args()
    print(json.dumps(verify(args.data_root, roads_root=args.roads_dir, allow_synthetic=args.allow_synthetic, max_bytes=args.max_bytes), indent=2, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError) as exc:
        raise SystemExit(f"ERROR: {exc}") from exc
