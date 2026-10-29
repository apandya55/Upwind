from fastapi.testclient import TestClient

from upwind.api import app
from upwind.national.roads import major_road_context


def test_durham_osm_extract_has_real_major_road_measurements_and_provenance():
    result = major_road_context("3719000")
    assert result["available"] is True
    assert result["road_way_count_within_radius"] > 0
    assert result["nearest_major_road"]["name"] == "Fayetteville Road"
    assert 0 < result["nearest_major_road"]["distance_km"] < 0.65
    assert result["major_road_length_km_within_radius"] > 0
    assert result["provenance"]["license"] == "Open Database License (ODbL) 1.0"
    assert result["provenance"]["osm_way_timestamps_retained"] is True


def test_charlotte_osm_extract_is_bounded_and_distinct_from_durham():
    result = major_road_context("3712000")
    assert result["available"] is True
    assert result["city"] == "Charlotte"
    assert result["road_way_count_within_radius"] > 0
    assert result["provenance"]["extract_bounds_wgs84"] != major_road_context("3719000")["provenance"]["extract_bounds_wgs84"]


def test_investigation_context_combines_release_evidence_with_osm_roads():
    response = TestClient(app).get("/api/national/context", params={
        "latitude": 35.977928, "longitude": -78.898109, "radius_km": 25,
        "monitor_year": 2024, "geoid": "3719000",
    })
    assert response.status_code == 200
    body = response.json()
    assert body["place_evidence"]["place"]["name"].startswith("Durham")
    assert body["place_evidence"]["estimate"] is not None
    assert body["road_context"]["available"] is True
    assert body["road_context"]["provenance"]["source_url"] == "https://www.openstreetmap.org/"
    assert any(item["evidence_class"] == "measured_monitor_summary" for item in body["items"])
    assert any("road proximity" in limitation.lower() and "geographic context only" in limitation.lower() for limitation in body["limitations"])


def test_osm_context_is_explicitly_unavailable_outside_demo_coverage():
    result = major_road_context("0604400")
    assert result["available"] is False
    assert "Durham and Charlotte" in result["reason"]
