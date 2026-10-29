#!/usr/bin/env python3
"""Validate required clean-deployment artifacts and the supported city workflows."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def verify(release: Path, roads: Path) -> dict:
    required = ("manifest.json", "places.json", "model.json", "monitors.json", "sources.json")
    missing = [str(release / name) for name in required if not (release / name).is_file() or (release / name).stat().st_size == 0]
    missing += [str(roads / f"{city}.{suffix}") for city in ("durham", "charlotte") for suffix in ("osm", "metadata.json")
                if not (roads / f"{city}.{suffix}").is_file() or (roads / f"{city}.{suffix}").stat().st_size == 0]
    if missing:
        raise SystemExit("Missing deployment artifacts:\n" + "\n".join(missing))
    manifest = json.loads((release / "manifest.json").read_text())
    places = json.loads((release / "places.json").read_text())
    monitors = json.loads((release / "monitors.json").read_text())
    sources = json.loads((release / "sources.json").read_text())
    by_id = {place.get("id"): place for place in places}
    cities = {}
    for geoid, name, latitude, longitude in (
        ("3719000", "Durham", 35.977928, -78.898109),
        ("3712000", "Charlotte", 35.209045, -80.830990),
    ):
        place = by_id.get(geoid)
        if not place:
            raise SystemExit(f"Required place missing from release: {name} ({geoid})")
        estimate = (place.get("model_estimates") or {}).get("2024")
        if not estimate:
            raise SystemExit(f"Required 2024 estimate missing for {name}")
        distance = lambda row: 6371.0088 * 2 * math.asin(min(1, math.sqrt(
            math.sin(math.radians(float(row["latitude"]) - latitude) / 2) ** 2
            + math.cos(math.radians(latitude)) * math.cos(math.radians(float(row["latitude"])))
            * math.sin(math.radians(float(row["longitude"]) - longitude) / 2) ** 2)))
        nearby_monitor = any(row.get("year") == 2024 and distance(row) <= 50 for row in monitors)
        nearby_source = any(row.get("pollutant") == "PM25" and distance(row) <= 50 for row in sources)
        if not nearby_monitor or not nearby_source:
            raise SystemExit(f"Monitor or EPA NEI source context missing within 50 km for {name}")
        cities[name] = {
            "estimate": True,
            "nearby_monitor_context_available_within_50_km": nearby_monitor,
            "nearby_source_context_available_within_50_km": nearby_source,
            "osm_extract": (roads / f"{name.lower()}.osm").stat().st_size,
        }
    result = {"release": manifest.get("release"), "counts": manifest.get("counts"), "cities": cities}
    print(json.dumps(result, indent=2))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-dir", type=Path, required=True)
    parser.add_argument("--roads-dir", type=Path, required=True)
    args = parser.parse_args()
    verify(args.release_dir, args.roads_dir)


if __name__ == "__main__":
    main()
