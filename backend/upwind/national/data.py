from __future__ import annotations

import json
import math
import hashlib
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[3]
RELEASE = ROOT / "data" / "national" / "release"


class ReleaseSet(dict[str, Any]):
    """Consistent group of decoded files and the identities read together."""

    def __init__(self, values: dict[str, Any], identities: dict[str, tuple[int, int, int, int]]):
        super().__init__(values)
        self.identities = identities


def release_identity(name: str) -> tuple[int, int, int, int]:
    """Return a cache identity that changes atomically with a release file."""
    path = RELEASE / name
    try:
        stat = path.stat()
    except OSError as exc:
        raise HTTPException(
            status_code=503,
            detail="National Explorer data have not been built. Run scripts/build_national_dataset.py and scripts/evaluate_national_v2.py.",
        ) from exc
    if not path.is_file():
        raise HTTPException(status_code=503, detail=f"National release file is unavailable: {name}")
    return stat.st_dev, stat.st_ino, stat.st_mtime_ns, stat.st_size


@lru_cache(maxsize=16)
def release_file_sha256(name: str, identity: tuple[int, int, int, int]) -> str:
    """Content hash for a release artifact, cached by its replacement identity."""
    del identity
    digest = hashlib.sha256()
    try:
        with (RELEASE / name).open("rb") as source:
            for block in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as exc:
        raise HTTPException(status_code=503, detail=f"National release file is unavailable: {name}") from exc
    return digest.hexdigest()


@lru_cache(maxsize=12)
def _read_release(name: str, identity: tuple[int, int, int, int]) -> Any:
    del identity  # Identity is part of the key so atomic release replacements invalidate cache.
    path = RELEASE / name
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=503, detail=f"National release is unreadable: {name}") from exc


def read_release(name: str) -> Any:
    return _read_release(name, release_identity(name))


def read_release_set(names: tuple[str, ...]) -> ReleaseSet:
    """Read related release files consistently across atomic release replacement."""
    for _ in range(2):
        before = {name: release_identity(name) for name in names}
        result = {name: _read_release(name, before[name]) for name in names}
        after = {name: release_identity(name) for name in names}
        if before == after:
            return ReleaseSet(result, before)
    raise HTTPException(status_code=503, detail="National release changed while preparing the snapshot; retry the request")


@lru_cache(maxsize=12)
def _spatial_buckets(name: str, identity: tuple[int, int, int, int]) -> dict[tuple[int, int], list[dict[str, Any]]]:
    """Build a one-degree index once per immutable release-file identity."""
    del identity
    rows = read_release(name)
    buckets: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for row in rows:
        lat, lon = float(row["latitude"]), float(row["longitude"])
        key = (math.floor(lat), math.floor(lon))
        buckets.setdefault(key, []).append(row)
    return buckets


def validate_bounds(west: float | None, south: float | None,
                    east: float | None, north: float | None) -> bool:
    values = (west, south, east, north)
    if all(value is None for value in values):
        return False
    if any(value is None for value in values):
        raise HTTPException(status_code=422, detail="Viewport requests require west, south, east, and north bounds")
    if not all(math.isfinite(float(value)) for value in values):
        raise HTTPException(status_code=422, detail="Geographic bounds must be finite")
    if not (-180 <= west <= 180 and -180 <= east <= 180 and -90 <= south <= 90 and -90 <= north <= 90) or west > east or south > north:
        raise HTTPException(status_code=422, detail="Invalid geographic bounds")
    return True


def query_bounds(name: str, west: float | None, south: float | None,
                 east: float | None, north: float | None, *, limit: int = 5000,
                 offset: int = 0, predicate=None, sort_key=None,
                 distinct_key: str | None = None):
    """Query indexed viewport buckets, returning a bounded stable page and exact counts."""
    if not validate_bounds(west, south, east, north):
        return ([], 0, 0) if distinct_key else ([], 0)
    buckets = None
    for _ in range(2):
        identity = release_identity(name)
        candidate = _spatial_buckets(name, identity)
        if identity == release_identity(name):
            buckets = candidate
            break
    if buckets is None:
        raise HTTPException(status_code=503, detail="National release changed while preparing the map query; retry the request")
    rows = []
    for lat in range(math.floor(south), math.floor(north) + 1):
        for lon in range(math.floor(west), math.floor(east) + 1):
            rows.extend(buckets.get((lat, lon), ()))
    matches = [
        row for row in rows
        if west <= row["longitude"] <= east
        and south <= row["latitude"] <= north
        and (predicate is None or predicate(row))
    ]
    if sort_key is not None:
        matches.sort(key=sort_key, reverse=True)
    start = max(0, int(offset))
    page = matches[start:start + max(1, min(int(limit), 10000))]
    if distinct_key:
        unique_count = len({str(row.get(distinct_key, "")) for row in matches if row.get(distinct_key) is not None})
        return page, len(matches), unique_count
    return page, len(matches)


def aggregate_bounds(name: str, west: float, south: float, east: float, north: float,
                    *, zoom: float, predicate=None, distinct_key: str | None = None,
                    budget: int = 3000, coordinate=None, value_for=None):
    """Return a deterministic, complete viewport representation on a global Web Mercator grid.

    Matching records are filtered before binning. Coarsening lowers the grid zoom
    until the number of symbols fits the rendering budget; no row sampling occurs.
    Grid boundaries are global, so small pans do not reshuffle unrelated groups.
    """
    if not validate_bounds(west, south, east, north):
        raise HTTPException(status_code=422, detail="Viewport aggregation requires bounds")
    buckets = None
    for _ in range(2):
        identity = release_identity(name)
        candidate = _spatial_buckets(name, identity)
        if identity == release_identity(name):
            buckets = candidate
            break
    if buckets is None:
        raise HTTPException(status_code=503, detail="National release changed while preparing the map query; retry")
    matches = []
    seen = set()
    for lat in range(math.floor(south), math.floor(north) + 1):
        for lon in range(math.floor(west), math.floor(east) + 1):
            for row in buckets.get((lat, lon), ()):
                if not (west <= row["longitude"] <= east and south <= row["latitude"] <= north):
                    continue
                if predicate is not None and not predicate(row):
                    continue
                if distinct_key:
                    key = str(row.get(distinct_key, ""))
                    if key in seen:
                        continue
                    seen.add(key)
                matches.append(row)
    # Keep coincident records in one symbol. Start with a fine national grid,
    # then coarsen deterministically to stay within the rendering budget
    # without sampling records or filling an arbitrary visual quota.
    level = max(0, min(20, math.floor(zoom + 7)))
    def cell_for(row, z):
        lat, lon = coordinate(row) if coordinate else (row["latitude"], row["longitude"])
        lat = max(-85.05112878, min(85.05112878, float(lat)))
        n = 2 ** z
        x = int((float(lon) + 180) / 360 * n)
        rad = math.radians(lat)
        y = int((1 - math.asinh(math.tan(rad)) / math.pi) / 2 * n)
        return (min(n - 1, max(0, x)), min(n - 1, max(0, y)))
    while level > 0:
        cells = {cell_for(row, level) for row in matches}
        if len(cells) <= budget:
            break
        level -= 1
    grouped = { (level, x, y): [] for x, y in {cell_for(row, level) for row in matches} }
    for row in matches:
        x, y = cell_for(row, level)
        grouped[(level, x, y)].append(row)
    items = []
    for (cell_level, x, y), members in sorted(grouped.items()):
        locations = [coordinate(row) if coordinate else (row["latitude"], row["longitude"]) for row in members]
        # Place aggregate dots on an actual source coordinate. Arithmetic
        # centroids made dense national views look like an artificial lattice
        # and could put a dot in an empty field or even outside the source
        # geography. Choose the member nearest the cell's location instead;
        # ties are resolved by the stable record id. The dot still represents
        # every member in the cell, but its visible position is real data.
        cell_lat = sum(float(p[0]) for p in locations) / len(locations)
        cell_lon = sum(float(p[1]) for p in locations) / len(locations)
        representative = min(
            zip(members, locations),
            key=lambda pair: (
                (float(pair[1][0]) - cell_lat) ** 2 + (float(pair[1][1]) - cell_lon) ** 2,
                str(pair[0].get("id", "")),
            ),
        )
        lat, lon = float(representative[1][0]), float(representative[1][1])
        key = f"{name}:{cell_level}:{x}:{y}"
        if len(members) == 1:
            item = dict(members[0])
            val = value_for(members[0]) if value_for else members[0].get("value")
            item.update({"cluster_id": key, "member_count": 1, "is_cluster": False,
                         "render_latitude": lat, "render_longitude": lon,
                         "value": val})
        else:
            item = {"id": key, "cluster_id": key, "latitude": lat, "longitude": lon,
                    "member_count": len(members), "is_cluster": True}
            values = [value_for(row) if value_for else row.get("value") for row in members]
            numeric = [float(value) for value in values if isinstance(value, (int, float)) and math.isfinite(float(value))]
            if numeric:
                item["value"] = sum(numeric) / len(numeric)
            # Preserve member identities for inspectability without transferring
            # raw records. A dedicated page endpoint can fetch details if needed.
        items.append(item)
    identity = release_identity(name)
    version = f"{identity[2]}:{identity[3]}"
    return {"items": items, "represented_records": len(matches), "symbol_count": len(items),
            "zoom": zoom, "aggregation_zoom": level, "budget": budget, "complete": True,
            "viewport": [west, south, east, north], "dataset_version": version,
            "aggregation_version": "mercator-grid-v3-real-anchor"}


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0088
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi, dlambda = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1 - a)))
