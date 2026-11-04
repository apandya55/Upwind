"""Create a lightweight synthetic national dataset fixture for automated tests."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, ElementTree


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = ROOT / ".local" / "test-release"
FIXTURE_RELEASE = "upwind-test-fixture-3"


def _estimate(value: float, monitor: str, distance: float) -> dict:
    return {
        "value_ug_m3": value,
        "interval90_low_ug_m3": max(0.0, value - 3.2),
        "interval90_high_ug_m3": value + 3.2,
        "evidence_status": "estimated",
        "model_id": "upwind-test-fixture-model",
        "nearest_monitor_km": distance,
        "reference_monitor_id": monitor,
        "reference_monitor_value_ug_m3": value,
        "support": "Synthetic test fixture; not a measured or production release.",
    }


def _place(geoid: str, name: str, state: str, state_fips: str, latitude: float,
           longitude: float, population: int, value: float | None,
           monitor: str | None = None) -> dict:
    estimates = {"2024": population}
    model = {"2024": _estimate(value, monitor or "fixture", 4.0)} if value is not None else {}
    return {
        "id": geoid,
        "name": name,
        "state": state,
        "state_fips": state_fips,
        "place_type": "City",
        "latitude": latitude,
        "longitude": longitude,
        "population_vintage": 2024,
        "estimates": estimates,
        "model_estimates": model,
        "withheld_reason": None if model else "No supported estimate is published for this fixture year.",
    }


def _build_release() -> dict[str, object]:
    # Keep the actual Census IDs used by the UI workflows. Raleigh and Durham
    # are real place labels; the values and evidence are synthetic test data.
    places = [
        _place("3712000", "Charlotte city", "North Carolina", "37", 35.209045, -80.830990, 900000, 9.4, "37-119-0001"),
        _place("3755000", "Raleigh city", "North Carolina", "37", 35.779600, -78.638200, 480000, 8.8, "37-183-0002"),
        _place("3719000", "Durham city", "North Carolina", "37", 35.977928, -78.898109, 300000, 8.4, "37-183-0001"),
        _place("0800000", "Denver", "Colorado", "08", 39.739200, -104.990300, 700000, 7.9, "08-031-0001"),
        _place("0604400", "Test withheld place", "California", "06", 34.05, -118.25, 1000000, None),
    ]
    # Several nearby points force a deterministic aggregate cell in the map
    # test without pretending that the cluster is a real geography.
    for index, (lat, lon) in enumerate(((35.98, -78.90), (35.975, -78.895), (35.985, -78.905)), 1):
        places.append(_place(str(3719000 + index * 10), f"Synthetic test point {index}", "North Carolina", "37", lat, lon, 1000 + index, 8.0 + index / 10, "37-183-0001"))

    monitors = []
    monitor_sites = [
        ("37-183-0001", 35.9800, -78.9000, "Durham"),
        ("37-183-0002", 35.7800, -78.6400, "Raleigh"),
        ("37-119-0001", 35.2100, -80.8300, "Charlotte"),
        ("08-031-0001", 39.7400, -104.9900, "Denver"),
    ]
    for site_id, latitude, longitude, _ in monitor_sites:
        for year, value in ((2022, 9.2), (2023, 8.9), (2024, 8.4), (2025, 8.1)):
            monitors.append({
                "id": site_id, "year": year, "latitude": latitude, "longitude": longitude,
                "pm25_ug_m3": value, "units": "µg/m³", "sample_completeness": "Y",
                "event_treatment": "Events Included", "pollutant_standard": "Annual PM2.5",
                "metric": "Annual mean", "evidence_type": "Synthetic test fixture",
                "source": "Synthetic test fixture", "url": "https://example.test/aqs",
            })

    sources = [
        {"id": "EIS-DURHAM-1", "name": "Durham fixture facility A", "company": "Fixture", "latitude": 35.980, "longitude": -78.900, "pollutant": "PM25", "pollutant_code": "PM25-PRI", "emissions": 12.0, "units": "TON", "category": "Synthetic facility", "inventory_year": 2023, "source": "Synthetic test fixture", "url": "https://example.test/nei"},
        {"id": "EIS-DURHAM-2", "name": "Durham fixture facility B", "company": "Fixture", "latitude": 35.975, "longitude": -78.895, "pollutant": "PM25", "pollutant_code": "PM25-PRI", "emissions": 6.0, "units": "TON", "category": "Synthetic facility", "inventory_year": 2023, "source": "Synthetic test fixture", "url": "https://example.test/nei"},
        {"id": "EIS-RALEIGH-1", "name": "Raleigh fixture facility", "company": "Fixture", "latitude": 35.780, "longitude": -78.640, "pollutant": "PM25", "pollutant_code": "PM25-PRI", "emissions": 4.0, "units": "TON", "category": "Synthetic facility", "inventory_year": 2023, "source": "Synthetic test fixture", "url": "https://example.test/nei"},
    ]
    supported_places = sum(bool(place["model_estimates"]) for place in places)
    covered_population = sum(
        place["estimates"]["2024"] for place in places if place["model_estimates"]
    )
    state_count = len({place["state_fips"] for place in places})
    manifest = {
        "release": FIXTURE_RELEASE,
        "built_utc": "2026-01-01T00:00:00Z",
        "selected_modeling_year": 2024,
        "model": {"model_id": "upwind-test-fixture-model", "method": "nearest eligible EPA AQS monitor", "target": "synthetic test PM2.5", "features": []},
        "model_evaluation_v2": {
            "protocol": "UW-NATIONAL-TEST-FIXTURE",
            "status": "synthetic fixture only",
            "years": {"2024": {"nearest_monitor": {"n": 4, "mae_ug_m3": 0.0, "rmse_ug_m3": 0.0, "bias_ug_m3": 0.0}}, "2025": {"nearest_monitor": {"n": 4, "mae_ug_m3": 0.0, "rmse_ug_m3": 0.0, "bias_ug_m3": 0.0}}},
            "selection": {"selected_model": "nearest_monitor", "fold_wins_vs_nearest_by_year": {"2024": 0, "2025": 0}},
            "deployment": {"calibration_abs_residual_90pct_ug_m3": 3.2, "oof_nearest_monitor_distance_p90_support_km": 100.0, "supported_places": supported_places, "withheld_places": len(places) - supported_places},
        },
        "annual_monitor_audit": {str(year): {"unique_spatial_site_years": 4, "state_count": state_count} for year in (2022, 2023, 2024, 2025)},
        "place_audit": {"gazetteer_places": len(places), "population_joined_places": len(places), "population_join_rate": 1.0},
        "source_audit": {"facility_summary_rows": len(sources)},
        "counts": {"searchable_census_places": len(places), "monitor_site_years": len(monitors), "monitor_sites_selected_year": 4, "modeled_places": supported_places, "supported_model_places": supported_places, "population_covered": covered_population},
        "dataset_sources": {
            "EPA AQS annual PM2.5 monitor summaries": {"url": "https://example.test/aqs", "period": "synthetic fixture"},
            "Census place Gazetteer": {"url": "https://example.test/census", "vintage": 2024},
            "Census population": {"url": "https://example.test/census", "vintage": "synthetic fixture"},
            "EPA National Emissions Inventory": {"url": "https://example.test/nei", "vintage": 2023},
        },
    }
    model = {"training_monitor_coordinates": [[row["latitude"], row["longitude"]] for row in monitors if row["year"] == 2024], "max_supported_nearest_monitor_km": 100.0}
    return {"manifest.json": manifest, "places.json": places, "model.json": model, "monitors.json": monitors, "sources.json": sources}


def _write_osm(path: Path, city: str, center_lat: float, center_lon: float, roads: list[tuple[str, str, float]]) -> None:
    root = Element("osm", version="0.6", generator="upwind-test-fixture")
    SubElement(root, "bounds", minlat=str(center_lat - 0.02), minlon=str(center_lon - 0.02), maxlat=str(center_lat + 0.02), maxlon=str(center_lon + 0.02))
    node_id = 1
    for name, highway, delta in roads:
        # Keep each synthetic corridor close to, but not exactly on, the
        # anchor point so distance assertions exercise the geometry path.
        coords = [(center_lat + delta, center_lon - 0.004), (center_lat + delta, center_lon + 0.004)]
        way = SubElement(root, "way", id=str(node_id), timestamp="2026-01-01T00:00:00Z")
        for latitude, longitude in coords:
            node = SubElement(root, "node", id=str(node_id), lat=str(latitude), lon=str(longitude))
            SubElement(way, "nd", ref=str(node_id))
            node_id += 1
        SubElement(way, "tag", k="highway", v=highway)
        SubElement(way, "tag", k="name", v=name)
    path.parent.mkdir(parents=True, exist_ok=True)
    ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)
    path.with_suffix(".metadata.json").write_text(json.dumps({
        "retrieved_utc": "2026-01-01T00:00:00Z", "dataset": "Synthetic test fixture",
        "source": "Synthetic test fixture", "source_url": "https://example.test/osm-fixture",
        "endpoint": "https://example.test/osm-fixture", "license": "Test fixture only (not ODbL)",
        "attribution": "Synthetic test geometry; no upstream OSM data",
        "center_wgs84": [center_lat, center_lon], "extract_bounds_wgs84": {"minlat": center_lat - 0.02, "minlon": center_lon - 0.02, "maxlat": center_lat + 0.02, "maxlon": center_lon + 0.02},
    }, indent=2) + "\n")


def create(root: Path) -> None:
    release_dir = root / "release"
    roads_dir = root / "context" / "osm_roads" / "raw"
    existing_manifest = release_dir / "manifest.json"
    if existing_manifest.exists():
        try:
            existing_release = json.loads(existing_manifest.read_text()).get("release", "")
            if not str(existing_release).startswith("upwind-test-fixture-"):
                return
        except (OSError, json.JSONDecodeError):
            return
    release_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in _build_release().items():
        (release_dir / name).write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")
    _write_osm(roads_dir / "durham.osm", "Durham", 35.977928, -78.898109, [("Fayetteville Road", "primary", 0.002), ("NC 147", "trunk", 0.004)])
    _write_osm(roads_dir / "charlotte.osm", "Charlotte", 35.209045, -80.830990, [("South Boulevard", "primary", 0.002), ("Independence Boulevard", "trunk", 0.004)])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    create(args.output_root.expanduser().resolve())


if __name__ == "__main__":
    main()
