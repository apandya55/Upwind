"""Bounded OpenStreetMap major-road context for Durham and Charlotte.

These extracts are deliberately local demonstrations, not national coverage.
Road distance/length are geographic descriptors and are never model inputs.
"""
from __future__ import annotations

import math
import os
from functools import lru_cache
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[3]
ROAD_DIR = ROOT / "data" / "national" / "context" / "osm_roads" / "raw"


def road_dir() -> Path:
    """Resolve the configured bounded OSM extract directory at request time."""
    return Path(os.environ.get("UPWIND_OSM_ROADS_DIR", str(ROAD_DIR))).expanduser()
SUPPORTED = {
    "3719000": ("Durham", 35.977928, -78.898109),
    "3712000": ("Charlotte", 35.209045, -80.830990),
}
MAJOR = {"motorway", "trunk", "primary", "secondary"}
RADIUS_KM = 0.65


@lru_cache(maxsize=2)
def _extract(geoid: str) -> dict:
    name, center_lat, center_lon = SUPPORTED[geoid]
    path = road_dir() / f"{name.lower()}.osm"
    metadata = __import__("json").loads(path.with_suffix(".metadata.json").read_text())
    root = ElementTree.parse(path).getroot()
    bounds = root.find("bounds")
    if bounds is None:
        raise ValueError(f"OSM extract has no bounds: {path}")
    nodes = {node.get("id"): (float(node.get("lat")), float(node.get("lon"))) for node in root.findall("node")}
    roads = []
    for way in root.findall("way"):
        tags = {tag.get("k"): tag.get("v") for tag in way.findall("tag")}
        kind = tags.get("highway")
        if kind not in MAJOR:
            continue
        coords = [nodes[ref.get("ref")] for ref in way.findall("nd") if ref.get("ref") in nodes]
        if len(coords) < 2:
            continue
        roads.append({"id": way.get("id"), "highway": kind, "name": tags.get("name"), "ref": tags.get("ref"),
                      "timestamp": way.get("timestamp"), "coordinates": coords})
    return {"name": name, "center": (center_lat, center_lon), "bounds": {key: float(value) for key, value in bounds.attrib.items()},
            "roads": roads, "extract_timestamp": metadata["retrieved_utc"], "metadata": metadata}


def _xy(lat: float, lon: float, origin_lat: float, origin_lon: float) -> tuple[float, float]:
    return ((lon - origin_lon) * 111.320 * math.cos(math.radians(origin_lat)), (lat - origin_lat) * 110.574)


def _distance_point_segment(point: tuple[float, float], a: tuple[float, float], b: tuple[float, float]) -> float:
    dx, dy = b[0] - a[0], b[1] - a[1]
    denom = dx * dx + dy * dy
    t = 0.0 if denom == 0 else max(0.0, min(1.0, ((point[0] - a[0]) * dx + (point[1] - a[1]) * dy) / denom))
    return math.hypot(point[0] - (a[0] + t * dx), point[1] - (a[1] + t * dy))


def _inside_length(a: tuple[float, float], b: tuple[float, float], radius: float) -> float:
    """Approximate line length inside a circle using deterministic 25 m samples."""
    length = math.hypot(b[0] - a[0], b[1] - a[1])
    if length == 0:
        return 0.0
    steps = max(1, min(500, math.ceil(length / 0.025)))
    inside = 0
    for i in range(steps):
        t = (i + 0.5) / steps
        if math.hypot(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t) <= radius:
            inside += 1
    return length * inside / steps


def major_road_context(geoid: str, latitude: float | None = None, longitude: float | None = None) -> dict:
    if geoid not in SUPPORTED:
        return {"available": False, "coverage": "not covered", "reason": "OSM road analysis is currently available only for the bounded Durham and Charlotte demonstration extracts."}
    data = _extract(geoid)
    center_lat, center_lon = data["center"]
    latitude, longitude = latitude if latitude is not None else center_lat, longitude if longitude is not None else center_lon
    # Road metrics are anchored to the Census point the extract was acquired for.
    if math.hypot(*_xy(latitude, longitude, center_lat, center_lon)) > 0.01:
        return {"available": False, "coverage": "not covered", "reason": "This extract is tied to the supported Census place internal point; the selected point is outside its 10 m anchor tolerance."}
    bounds = data["bounds"]
    if not (bounds["minlat"] <= latitude <= bounds["maxlat"] and bounds["minlon"] <= longitude <= bounds["maxlon"]):
        return {"available": False, "coverage": "not covered", "reason": "Selected point is outside the downloaded OSM extract bounds."}
    origin_lat, origin_lon = latitude, longitude
    corridors: dict[tuple[str, str], dict] = {}
    total_km = 0.0
    by_class: dict[str, float] = {}
    for road in data["roads"]:
        xy = [_xy(lat, lon, origin_lat, origin_lon) for lat, lon in road["coordinates"]]
        distance = min((_distance_point_segment((0.0, 0.0), xy[i - 1], xy[i]) for i in range(1, len(xy))), default=math.inf)
        inside_km = sum(_inside_length(xy[i - 1], xy[i], RADIUS_KM) for i in range(1, len(xy)))
        if inside_km > 0:
            total_km += inside_km
            by_class[road["highway"]] = by_class.get(road["highway"], 0.0) + inside_km
        if distance <= RADIUS_KM:
            road_name = road["name"] or road["ref"] or f"Unnamed {road['highway']} road"
            corridor_key = (road_name, road["highway"])
            corridor = corridors.setdefault(corridor_key, {"name": road_name, "road_class": road["highway"],
                "distance_km": distance, "way_ids": [], "osm_version_timestamps": [], "mapped_length_km_within_radius": 0.0})
            corridor["distance_km"] = min(corridor["distance_km"], distance)
            corridor["way_ids"].append(road["id"])
            if road["timestamp"]:
                corridor["osm_version_timestamps"].append(road["timestamp"])
            corridor["mapped_length_km_within_radius"] += inside_km
    nearest = [{**item, "distance_km": round(item["distance_km"], 3),
                "osm_way_id": item["way_ids"][0], "segment_count": len(item["way_ids"]),
                "mapped_length_km_within_radius": round(item["mapped_length_km_within_radius"], 3)}
               for item in corridors.values()]
    nearest.sort(key=lambda item: (item["distance_km"], item["name"], item["road_class"]))
    radius = RADIUS_KM
    return {
        "available": True, "coverage": f"{data['name']} bounded extract; metrics within {radius:.2f} km of Census Gazetteer internal point",
        "city": data["name"], "radius_km": radius,
        "nearest_major_road": nearest[0] if nearest else None,
        "nearby_major_roads": nearest[:8], "major_road_length_km_within_radius": round(total_km, 3),
        "major_road_length_km_per_km2": round(total_km / (math.pi * radius * radius), 3),
        "length_by_road_class_km": {key: round(value, 3) for key, value in sorted(by_class.items())},
        "road_way_count_within_radius": sum(item["segment_count"] for item in nearest),
        "major_road_corridor_count_within_radius": len(nearest),
        "provenance": {"dataset": data["metadata"].get("dataset", "OpenStreetMap road network"),
                       "source": data["metadata"].get("source", "OpenStreetMap contributors via OpenStreetMap API"),
                       "source_url": data["metadata"].get("source_url", "https://www.openstreetmap.org/"),
                       "api_url": data["metadata"].get("endpoint", "https://api.openstreetmap.org/api/0.6/map"),
                       "license": data["metadata"].get("license", "Open Database License (ODbL) 1.0"),
                       "attribution": data["metadata"].get("attribution", "© OpenStreetMap contributors"),
                       "extract_timestamp": data["extract_timestamp"], "osm_way_timestamps_retained": True,
                       "highway_classes": sorted(MAJOR), "extract_bounds_wgs84": data["bounds"],
                       "coverage_center_wgs84": data["metadata"]["center_wgs84"]},
        "interpretation": "Mapped road proximity and length are geographic context only. They do not measure traffic, tailpipe emissions, ambient concentration, or a road's contribution to PM2.5.",
    }
