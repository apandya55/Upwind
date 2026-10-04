from fastapi.testclient import TestClient
import json

from upwind import api
from upwind.national import data as national_data


def test_national_places_support_search_geoid_and_viewport(monkeypatch):
    places = [
        {"id": "3712000", "name": "Raleigh", "state": "North Carolina", "state_fips": "37", "latitude": 35.78, "longitude": -78.64, "estimates": {"2024": 470000}},
        {"id": "3719000", "name": "Durham", "state": "North Carolina", "state_fips": "37", "latitude": 35.99, "longitude": -78.90, "estimates": {"2024": 300000}},
        {"id": "0600000", "name": "Raleigh", "state": "California", "state_fips": "06", "latitude": 37.0, "longitude": -120.0, "estimates": {"2024": 2000}},
    ]
    monkeypatch.setattr(api, "read_release", lambda name: places if name == "places.json" else [])
    monkeypatch.setattr(national_data, "read_release", lambda name: places if name == "places.json" else [])
    national_data._spatial_buckets.cache_clear()
    client = TestClient(api.app)

    result = client.get("/api/national/places", params={"q": "raleigh", "state": "North Carolina", "year": 2024}).json()
    assert result["total"] == 1
    assert result["items"][0]["id"] == "3712000"
    assert result["items"][0]["estimate"] == 470000

    result = client.get("/api/national/places", params={"geoid": "3719000"}).json()
    assert [p["name"] for p in result["items"]] == ["Durham"]

    result = client.get("/api/national/places", params={"west": -78.8, "east": -78, "south": 35, "north": 36}).json()
    assert {p["id"] for p in result["items"]} == {"3712000"}


def test_national_places_and_monitors_clamp_page_sizes_and_preserve_pagination(monkeypatch):
    places = [
        {"id": f"37{i:05d}", "name": f"Place {i}", "state": "North Carolina",
         "state_fips": "37", "latitude": 35.0, "longitude": -79.0}
        for i in range(2_105)
    ]
    monitors = [
        {"id": f"37-001-{i:04d}", "year": 2024, "latitude": 35.0, "longitude": -79.0}
        for i in range(5_005)
    ]
    monkeypatch.setattr(api, "read_release", lambda name: places if name == "places.json" else monitors)
    monkeypatch.setattr(national_data, "read_release", lambda name: places if name == "places.json" else monitors)
    national_data._spatial_buckets.cache_clear()
    client = TestClient(api.app)

    first_places = client.get("/api/national/places", params={"limit": 10_000}).json()
    assert len(first_places["items"]) == 2_000
    assert first_places["limit"] == 2_000
    assert first_places["total"] == 2_105
    assert first_places["next_offset"] == 2_000
    second_places = client.get("/api/national/places", params={"limit": 10_000, "offset": 2_000}).json()
    assert len(second_places["items"]) == 105
    assert second_places["next_offset"] is None

    first_monitors = client.get("/api/national/monitors", params={"year": 2024, "limit": 10_000}).json()
    assert len(first_monitors["items"]) == 5_000
    assert first_monitors["limit"] == 5_000
    assert first_monitors["total"] == 5_005
    assert first_monitors["next_offset"] == 5_000
    second_monitors = client.get("/api/national/monitors", params={"year": 2024, "limit": 10_000, "offset": 5_000}).json()
    assert len(second_monitors["items"]) == 5
    assert second_monitors["next_offset"] is None
    national_data._spatial_buckets.cache_clear()


def test_national_monitor_history_and_source_bounds(monkeypatch):
    monitors = [
        {"id": "37-183-0001", "year": 2023, "latitude": 35.8, "longitude": -78.6},
        {"id": "37-183-0001", "year": 2024, "latitude": 35.8, "longitude": -78.6},
        {"id": "06-001-0001", "year": 2024, "latitude": 37.0, "longitude": -120.0},
    ]
    sources = [
        {"id": "facility-1", "pollutant": "PM25", "longitude": -78.6, "latitude": 35.8},
        {"id": "facility-2", "pollutant": "NOX", "longitude": -78.6, "latitude": 35.8},
    ]
    release = lambda name: monitors if name == "monitors.json" else sources
    monkeypatch.setattr(api, "read_release", release)
    monkeypatch.setattr(national_data, "read_release", release)
    national_data._spatial_buckets.cache_clear()
    client = TestClient(api.app)

    result = client.get("/api/national/monitors", params={"site_id": "37-183-0001", "year": -1}).json()
    assert [r["year"] for r in result["items"]] == [2023, 2024]
    result = client.get("/api/national/sources", params={"west": -79, "east": -78, "south": 35, "north": 36}).json()
    assert [r["id"] for r in result["items"]] == ["facility-1"]
    assert result["total"] == 1 and result["truncated"] is False


def test_national_viewport_rejects_invalid_bounds():
    result = TestClient(api.app).get("/api/national/sources", params={"west": 10, "east": -10, "south": 0, "north": 10})
    assert result.status_code == 422


def test_public_readonly_mode_exposes_national_gets_and_hides_legacy_api(monkeypatch):
    monkeypatch.setenv("UPWIND_PUBLIC_READONLY", "1")
    client = TestClient(api.app)
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["version"] == "0.1.0"
    assert health.json()["product"] == "national-explorer"
    assert health.json()["model_version"] == "upwind-nearest-monitor-annual-pm25-0.3.0"
    assert health.json()["protocol_version"] == "UW-NATIONAL-SPATIAL-2026-04"
    # Allowed route reaches the data layer; the 503 here is the expected result
    # because unit tests intentionally do not package the national release.
    assert client.get("/api/national/manifest").status_code in (200, 503)
    assert client.get("/api/demo").status_code == 404
    assert client.get("/api/investigations").status_code == 404
    assert client.post("/api/analyze", json={}).status_code == 404


def test_public_app_import_does_not_load_local_engine():
    import os
    import subprocess
    import sys

    environment = os.environ.copy()
    environment["UPWIND_PUBLIC_READONLY"] = "1"
    environment["PYTHONPATH"] = "backend"
    subprocess.run(
        [sys.executable, "-c", "import sys; import upwind.api; assert 'upwind.engine' not in sys.modules"],
        check=True,
        env=environment,
        capture_output=True,
        text=True,
    )


def test_configured_cors_allows_only_declared_origin():
    import os
    import subprocess
    import sys

    environment = os.environ.copy()
    environment.update({"UPWIND_PUBLIC_READONLY": "1", "UPWIND_CORS_ORIGINS": "https://upwind.example"})
    environment["PYTHONPATH"] = "backend"
    subprocess.run(
        [sys.executable, "-c", "from fastapi.testclient import TestClient; from upwind.api import app; c=TestClient(app); a=c.get('/api/health', headers={'Origin':'https://upwind.example'}); p=c.options('/api/health', headers={'Origin':'https://upwind.example','Access-Control-Request-Method':'GET'}); b=c.get('/api/health', headers={'Origin':'https://attacker.example'}); assert a.headers.get('access-control-allow-origin') == 'https://upwind.example'; assert p.status_code == 200 and p.headers.get('access-control-allow-origin') == 'https://upwind.example'; assert 'access-control-allow-origin' not in b.headers"],
        check=True,
        env=environment,
        capture_output=True,
        text=True,
    )


def test_ready_requires_release_and_bounded_osm_artifacts(monkeypatch, tmp_path):
    release, roads = tmp_path / "release", tmp_path / "roads"
    release.mkdir(); roads.mkdir()
    monkeypatch.setenv("UPWIND_NATIONAL_RELEASE_DIR", str(release))
    monkeypatch.setenv("UPWIND_OSM_ROADS_DIR", str(roads))
    client = TestClient(api.app)
    assert client.get("/api/ready").status_code == 503
    for name in ("manifest.json", "places.json", "model.json", "monitors.json", "sources.json"):
        (release / name).write_text("{}")
    for city in ("durham", "charlotte"):
        (roads / f"{city}.osm").write_text("<osm/>")
        (roads / f"{city}.metadata.json").write_text("{}")
    assert client.get("/api/ready").json()["status"] == "ready"


def test_ready_rejects_malformed_release_json(monkeypatch, tmp_path):
    release, roads = tmp_path / "release", tmp_path / "roads"
    release.mkdir(); roads.mkdir()
    monkeypatch.setenv("UPWIND_NATIONAL_RELEASE_DIR", str(release))
    monkeypatch.setenv("UPWIND_OSM_ROADS_DIR", str(roads))
    for name in ("manifest.json", "places.json", "model.json", "monitors.json", "sources.json"):
        (release / name).write_text("{}")
    (release / "places.json").write_text("{")
    for city in ("durham", "charlotte"):
        (roads / f"{city}.osm").write_text("<osm/>")
        (roads / f"{city}.metadata.json").write_text("{}")
    response = TestClient(api.app).get("/api/ready")
    assert response.status_code == 503
    assert str(release / "places.json") in response.json()["malformed_files"]


def test_public_read_limit_is_per_client_ip(monkeypatch):
    monkeypatch.setenv("UPWIND_PUBLIC_READONLY", "1")
    monkeypatch.setenv("UPWIND_TRUST_PROXY", "1")
    api._public_rate_windows.clear()
    client = TestClient(api.app)
    for _ in range(120):
        assert client.get("/api/health", headers={"X-Forwarded-For": "198.51.100.20"}).status_code == 200
    limited = client.get("/api/health", headers={"X-Forwarded-For": "198.51.100.20"})
    assert limited.status_code == 429
    assert limited.headers["retry-after"]
    assert client.get("/api/health", headers={"X-Forwarded-For": "198.51.100.21"}).status_code == 200


def test_public_read_limit_ignores_forwarded_header_without_trusted_proxy(monkeypatch):
    monkeypatch.setenv("UPWIND_PUBLIC_READONLY", "1")
    monkeypatch.delenv("UPWIND_TRUST_PROXY", raising=False)
    monkeypatch.setattr(api.time, "monotonic", lambda: 120.0)
    api._public_rate_windows.clear()
    client = TestClient(api.app)
    for _ in range(120):
        assert client.get("/api/health", headers={"X-Forwarded-For": f"198.51.100.{_ + 1}"}).status_code == 200
    assert client.get("/api/health", headers={"X-Forwarded-For": "203.0.113.1"}).status_code == 429


def test_public_rate_limit_bounds_client_key_state(monkeypatch):
    monkeypatch.setenv("UPWIND_PUBLIC_READONLY", "1")
    monkeypatch.setenv("UPWIND_TRUST_PROXY", "1")
    api._public_rate_windows.clear()
    monkeypatch.setattr(api, "_PUBLIC_RATE_MAX_CLIENTS", 2)
    client = TestClient(api.app)
    assert client.get("/api/health", headers={"X-Forwarded-For": "198.51.100.1"}).status_code == 200
    assert client.get("/api/health", headers={"X-Forwarded-For": "198.51.100.2"}).status_code == 200
    assert client.get("/api/health", headers={"X-Forwarded-For": "198.51.100.3"}).status_code == 200
    assert len(api._public_rate_windows) == 3


def test_public_write_is_rejected_before_body_validation(monkeypatch):
    monkeypatch.setenv("UPWIND_PUBLIC_READONLY", "1")
    response = TestClient(api.app).post("/api/analyze", content="{" + ("[" * 80))
    assert response.status_code == 404


def test_public_api_reports_separate_national_model_identity(monkeypatch):
    monkeypatch.setenv("UPWIND_PUBLIC_READONLY", "1")
    payload = TestClient(api.app).get("/api/health").json()
    assert payload["product"] == "national-explorer"
    assert payload["model_version"] == "upwind-nearest-monitor-annual-pm25-0.3.0"
    assert payload["protocol_version"] == "UW-NATIONAL-SPATIAL-2026-04"


def test_local_health_retains_plume_engine_identity(monkeypatch):
    monkeypatch.delenv("UPWIND_PUBLIC_READONLY", raising=False)
    payload = TestClient(api.app).get("/api/health").json()
    assert payload["product"] == "local-research-engine"
    assert payload["model_version"].startswith("plume-")
    assert payload["protocol_version"].startswith("UW-ENGINE-")


def test_national_context_keeps_evidence_classes_and_distance_ranking(monkeypatch):
    monitors = [
        {"id": "monitor-far", "year": 2024, "latitude": 35.1, "longitude": -78.9,
         "pm25_ug_m3": 8.2, "units": "µg/m³", "sample_completeness": "Y",
         "event_treatment": "Events Included", "source": "EPA AQS", "url": "https://example.test/aqs"},
        {"id": "monitor-close", "year": 2023, "latitude": 35.01, "longitude": -78.99,
         "pm25_ug_m3": 7.0},
    ]
    sources = [
        {"id": "facility-far", "pollutant": "PM25", "latitude": 35.08, "longitude": -78.92,
         "pollutant_code": "PM25-PRI", "emissions": 500, "units": "TON", "inventory_year": 2023,
         "category": "Industrial", "url": "https://example.test/nei"},
        {"id": "facility-close", "pollutant": "PM25", "latitude": 35.01, "longitude": -78.99,
         "pollutant_code": "PM25-PRI", "emissions": 1, "units": "TON", "inventory_year": 2023,
         "category": "Other", "url": "https://example.test/nei"},
        {"id": "other-pollutant", "pollutant": "NOX", "latitude": 35.001, "longitude": -78.999,
         "emissions": 1000},
    ]
    release = lambda name: monitors if name == "monitors.json" else sources
    monkeypatch.setattr(api, "read_release", release)
    monkeypatch.setattr(national_data, "read_release", release)
    national_data._spatial_buckets.cache_clear()
    response = TestClient(api.app).get("/api/national/context", params={
        "latitude": 35, "longitude": -79, "radius_km": 20, "pollutant": "pm25",
    })
    assert response.status_code == 200
    body = response.json()
    assert body["counts"] == {"measured_monitor_summaries": 1, "facility_inventory_summary_rows": 2, "distinct_facilities": 2}
    assert [item["id"] for item in body["items"]] == ["facility-close", "facility-far", "monitor-far"]
    assert body["items"][0]["evidence_class"] == "facility_inventory_estimate"
    assert body["items"][0]["relation"] == "near_point"
    assert "not ambient concentration" in body["items"][0]["interpretation"]
    assert "measured_monitor_summary" == body["items"][-1]["evidence_class"]
    assert "great-circle distance ascending" in body["provenance"]["ranking"]
    assert "does not mean inside a place boundary" in body["limitations"][1]
    national_data._spatial_buckets.cache_clear()


def test_national_context_caps_radius_and_validates_point(monkeypatch):
    client = TestClient(api.app)
    assert client.get("/api/national/context", params={"latitude": 35, "longitude": -79, "radius_km": 251}).status_code == 422
    assert client.get("/api/national/context", params={"latitude": 91, "longitude": -79}).status_code == 422


def test_context_paginates_all_candidates_and_ranks_only_compatible_inventory(monkeypatch):
    monitors = [
        {"id": "site-2023", "year": 2023, "latitude": 35.0, "longitude": -79.0, "pm25_ug_m3": 8.0},
        {"id": "site-2024", "year": 2024, "latitude": 35.0, "longitude": -79.0, "pm25_ug_m3": 9.0},
    ]
    sources = [
        {"id": f"facility-{i:05d}", "pollutant": "PM25", "pollutant_code": "PM25-PRI",
         "latitude": 35.0, "longitude": -79.0, "emissions": float(i), "units": "TON",
         "inventory_year": 2023, "category": "Industrial", "url": "https://example.test/nei"}
        for i in range(10005)
    ]
    release = lambda name: monitors if name == "monitors.json" else sources
    monkeypatch.setattr(api, "read_release", release)
    monkeypatch.setattr(national_data, "read_release", release)
    national_data._spatial_buckets.cache_clear()
    body = TestClient(api.app).get("/api/national/context", params={
        "latitude": 35, "longitude": -79, "radius_km": 25, "monitor_year": 2023, "limit": 4,
    }).json()
    assert body["counts"] == {"measured_monitor_summaries": 1, "facility_inventory_summary_rows": 10005, "distinct_facilities": 10005}
    assert body["nearest_monitors"][0]["id"] == "site-2023"
    assert body["largest_compatible_inventory_groups"][0]["records"][0]["id"] == "facility-10004"
    assert body["largest_compatible_inventory_groups"][0]["compatible_record_count"] == 10005
    assert body["monitoring_gap"]["status"] == "monitor_summaries_within_radius"
    assert body["provenance"]["monitor_year"] == 2023
    national_data._spatial_buckets.cache_clear()


def test_national_source_viewport_is_bounded_and_ranked(monkeypatch):
    rows = [{"id": str(i), "pollutant": "PM25", "latitude": 35.0, "longitude": -79.0, "emissions": float(i)} for i in range(3105)]
    monkeypatch.setattr(api, "read_release", lambda name: rows)
    monkeypatch.setattr(national_data, "read_release", lambda name: rows)
    national_data._spatial_buckets.cache_clear()
    result = TestClient(api.app).get("/api/national/sources", params={"west": -80, "east": -78, "south": 34, "north": 36}).json()
    assert result["total"] == 3105 and result["truncated"] is True
    assert len(result["items"]) == 3000
    assert result["items"][0]["emissions"] == 3104
    assert result["items"][-1]["emissions"] == 105
    national_data._spatial_buckets.cache_clear()


def test_aggregated_viewport_is_complete_filtered_and_progressive(monkeypatch):
    rows = []
    for i in range(3200):
        rows.append({"id": f"p{i}", "name": f"place {i}", "state": "Test", "latitude": 35 + (i % 100) * .0001,
                     "longitude": -79 + (i % 100) * .0001,
                     "model_estimates": {"2024": {"value_ug_m3": 8, "estimate_latitude": 35 + (i % 100) * .0001,
                                                     "estimate_longitude": -79 + (i % 100) * .0001}}})
    monkeypatch.setattr(api, "read_release", lambda name: rows)
    monkeypatch.setattr(national_data, "read_release", lambda name: rows)
    national_data._spatial_buckets.cache_clear()
    client = TestClient(api.app)
    params = {"layer": "estimates", "west": -80, "east": -78, "south": 34, "north": 36, "year": 2024}
    national = client.get("/api/national/viewport", params={**params, "zoom": 3}).json()
    local = client.get("/api/national/viewport", params={**params, "zoom": 12}).json()
    assert national["complete"] is True
    assert national["represented_records"] == 3200
    assert sum(item["member_count"] for item in national["items"]) == 3200
    # This fixture has only 100 distinct coordinates, so coincident records
    # intentionally remain inspectable through member lists instead of being
    # rendered as overlapping dots.
    assert national["symbol_count"] <= 3000
    assert national["symbol_count"] < local["symbol_count"]
    assert local["represented_records"] == 3200
    assert local["filters"]["year"] == 2024
    assert local["aggregation_version"] == "mercator-grid-v3-real-anchor"
    assert local["evidence_explanation"]["evidence_class"] == "modeled_place_point_estimate"
    assert "Census Gazetteer internal point" in local["evidence_explanation"]["why_this_appears"]
    assert all("emissions" not in item for item in local["items"])
    cluster = next(item for item in national["items"] if item["member_count"] > 1)
    members = client.get("/api/national/viewport-members", params={
        "layer": "estimates", "cluster_id": cluster["cluster_id"], "west": -80, "east": -78,
        "south": 34, "north": 36, "year": 2024, "limit": 10,
    }).json()
    assert members["total"] == cluster["member_count"]
    assert len(members["items"]) == 10
    assert members["next_offset"] == 10
    national_data._spatial_buckets.cache_clear()


def test_national_overview_uses_dot_budget_when_locations_are_distinct(monkeypatch):
    rows = []
    for i in range(3200):
        lat = 25 + (i // 80) * .25
        lon = -124 + (i % 80) * .25
        rows.append({"id": f"p{i}", "name": f"place {i}", "state": "Test", "latitude": lat,
                     "longitude": lon,
                     "model_estimates": {"2024": {"value_ug_m3": 8, "estimate_latitude": lat,
                                                     "estimate_longitude": lon}}})
    monkeypatch.setattr(api, "read_release", lambda name: rows)
    monkeypatch.setattr(national_data, "read_release", lambda name: rows)
    national_data._spatial_buckets.cache_clear()
    result = TestClient(api.app).get("/api/national/viewport", params={
        "layer": "estimates", "west": -125, "east": -100, "south": 24, "north": 40,
        "zoom": 3.1, "year": 2024,
    }).json()
    assert result["represented_records"] == 3200
    assert result["symbol_count"] <= 3000
    assert sum(item["member_count"] for item in result["items"]) == 3200
    national_data._spatial_buckets.cache_clear()


def test_aggregate_dots_use_real_member_coordinates(monkeypatch):
    rows = [
        {"id": "a", "name": "west", "latitude": 40.0, "longitude": -100.0,
         "model_estimates": {"2024": {"value_ug_m3": 7, "estimate_latitude": 40.0, "estimate_longitude": -100.0}}},
        {"id": "b", "name": "east", "latitude": 40.1, "longitude": -99.9,
         "model_estimates": {"2024": {"value_ug_m3": 9, "estimate_latitude": 40.1, "estimate_longitude": -99.9}}},
    ]
    monkeypatch.setattr(api, "read_release", lambda name: rows)
    monkeypatch.setattr(national_data, "read_release", lambda name: rows)
    national_data._spatial_buckets.cache_clear()
    result = TestClient(api.app).get("/api/national/viewport", params={
        "layer": "estimates", "west": -101, "east": -99, "south": 39, "north": 42,
        "zoom": 3, "year": 2024,
    }).json()
    assert result["represented_records"] == 2
    assert any(item["member_count"] == 2 for item in result["items"])
    aggregate = next(item for item in result["items"] if item["member_count"] == 2)
    assert (aggregate["latitude"], aggregate["longitude"]) in {(40.0, -100.0), (40.1, -99.9)}
    national_data._spatial_buckets.cache_clear()


def test_aggregated_viewport_applies_year_and_pollutant_before_grouping(monkeypatch):
    rows = [
        {"id": "a", "year": 2024, "latitude": 35, "longitude": -79, "pm25_ug_m3": 7},
        {"id": "a", "year": 2023, "latitude": 35, "longitude": -79, "pm25_ug_m3": 9},
    ]
    sources = [
        {"id": "x", "pollutant": "PM25", "latitude": 35, "longitude": -79, "emissions": 2},
        {"id": "y", "pollutant": "NOX", "latitude": 35, "longitude": -79, "emissions": 5},
    ]
    release = lambda name: rows if name == "monitors.json" else sources if name == "sources.json" else []
    monkeypatch.setattr(api, "read_release", release)
    monkeypatch.setattr(national_data, "read_release", release)
    national_data._spatial_buckets.cache_clear()
    client = TestClient(api.app)
    base = {"west": -80, "east": -78, "south": 34, "north": 36, "zoom": 12}
    monitors = client.get("/api/national/viewport", params={**base, "layer": "monitors", "year": 2024}).json()
    facilities = client.get("/api/national/viewport", params={**base, "layer": "sources", "year": 2024, "pollutant": "PM25"}).json()
    assert monitors["represented_records"] == 1
    assert monitors["items"][0]["id"] == "a"
    assert facilities["represented_records"] == 1
    assert facilities["items"][0]["id"] == "x"
    assert facilities["filters"]["pollutant"] == "PM25"
    national_data._spatial_buckets.cache_clear()


def test_national_viewport_requires_complete_valid_bounds():
    client = TestClient(api.app)
    for route in ("places", "monitors", "sources"):
        result = client.get(f"/api/national/{route}", params={"west": -80, "east": -78, "south": 34})
        assert result.status_code == 422
    result = client.get("/api/national/places", params={"west": float("nan"), "east": -78, "south": 34, "north": 36})
    assert result.status_code == 422


def test_national_viewport_accepts_bounded_symbol_budget(monkeypatch):
    rows = [{"id": str(i), "name": str(i), "latitude": 35 + i * .00001, "longitude": -79,
             "model_estimates": {"2024": {"value_ug_m3": 8}}} for i in range(25)]
    monkeypatch.setattr(api, "read_release", lambda name: rows)
    monkeypatch.setattr(national_data, "read_release", lambda name: rows)
    national_data._spatial_buckets.cache_clear()
    client = TestClient(api.app)
    query = {"layer": "estimates", "west": -80, "east": -78, "south": 34, "north": 36, "zoom": 12, "budget": 5}
    body = client.get("/api/national/viewport", params=query).json()
    assert body["represented_records"] == 25
    assert body["symbol_count"] <= 5
    assert body["budget"] == 5
    assert client.get("/api/national/viewport", params={**query, "budget": 3001}).status_code == 422
    national_data._spatial_buckets.cache_clear()


def test_place_map_pagination_has_stable_counts_and_offset(monkeypatch):
    places = [
        {"id": "3712000", "name": "Raleigh", "state": "North Carolina", "state_fips": "37", "latitude": 35.78, "longitude": -78.64, "estimates": {}},
        {"id": "3719000", "name": "Durham", "state": "North Carolina", "state_fips": "37", "latitude": 35.99, "longitude": -78.90, "estimates": {}},
        {"id": "3714000", "name": "Cary", "state": "North Carolina", "state_fips": "37", "latitude": 35.79, "longitude": -78.78, "estimates": {}},
    ]
    monkeypatch.setattr(api, "read_release", lambda name: places)
    monkeypatch.setattr(national_data, "read_release", lambda name: places)
    national_data._spatial_buckets.cache_clear()
    response = TestClient(api.app).get("/api/national/places", params={
        "west": -80, "east": -78, "south": 35, "north": 36, "limit": 1, "offset": 1,
    })
    body = response.json()
    assert body["total"] == 3
    assert body["items"][0]["id"] == "3719000"
    assert body["offset"] == 1 and body["limit"] == 1 and body["next_offset"] == 2
    assert body["truncated"] is True
    national_data._spatial_buckets.cache_clear()


def test_source_count_distinguishes_summary_rows_and_traceable_facilities(monkeypatch):
    rows = [
        {"id": "EIS-1", "pollutant": "PM25", "pollutant_code": "PM25-PRI", "latitude": 35.5, "longitude": -78.5, "emissions": 3.0, "url": "https://example.test/archive"},
        {"id": "EIS-1", "pollutant": "PM25", "pollutant_code": "PM25-PRI", "latitude": 35.6, "longitude": -78.6, "emissions": 2.0, "url": "https://example.test/archive"},
        {"id": "EIS-2", "pollutant": "NOX", "latitude": 35.5, "longitude": -78.5, "emissions": 90.0},
    ]
    monkeypatch.setattr(api, "read_release", lambda name: rows)
    monkeypatch.setattr(national_data, "read_release", lambda name: rows)
    national_data._spatial_buckets.cache_clear()
    result = TestClient(api.app).get("/api/national/sources", params={
        "west": -79, "east": -78, "south": 35, "north": 36, "pollutant": " pm25 ",
    }).json()
    assert result["summary_rows"] == result["total"] == 2
    assert result["facility_count"] == 1
    assert result["items"][0]["facility_id"] == "EIS-1"
    assert result["items"][0]["facility_record_url"] is None
    assert result["items"][0]["canonical_facility_id"] == "epa-eis:EIS-1"
    assert result["items"][0]["provider_record_id"] == "EIS-1"
    assert result["items"][0]["original_coordinates"] == [-78.5, 35.5]
    assert "not a verified release point" in result["items"][0]["coordinate_role"]
    assert result["items"][0]["match_method"] == "exact EPA EIS facility identifier"
    assert result["items"][0]["verified_footprint"] is None
    assert result["items"][0]["url"] == "https://example.test/archive"
    # Responses must not mutate the cached source records.
    assert "facility_id" not in rows[0]
    national_data._spatial_buckets.cache_clear()


def test_national_snapshot_json_csv_geojson_and_validation(monkeypatch):
    manifest = {
        "release": "upwind-national-test", "built_utc": "2026-10-20T00:00:00Z", "selected_modeling_year": 2024,
        "model": {"model_id": "test-model", "method": "nearest eligible monitor"},
        "dataset_sources": {"EPA AQS annual PM2.5 monitor summaries": {"period": "2018-2025"},
                            "Census place Gazetteer": {"vintage": 2024}, "Census population": {"vintage": "2020-2024"},
                            "EPA National Emissions Inventory": {"vintage": 2023}},
    }
    places = [
        {"id": "3712000", "name": "=2+2", "state": "North Carolina", "state_fips": "37", "place_type": "City",
         "latitude": 35.78, "longitude": -78.64, "population_vintage": 2024, "estimates": {"2024": 500},
         "model_estimates": {"2024": {"value_ug_m3": 8.0, "interval90_low_ug_m3": 4.0,
             "interval90_high_ug_m3": 12.0, "evidence_status": "estimated", "model_id": "test-model",
             "nearest_monitor_km": 12.5, "reference_monitor_id": "37-183-0001", "reference_monitor_value_ug_m3": 8.0,
             "support": "test support"}}},
        {"id": "0200065", "name": "Adak city", "state": "Alaska", "state_fips": "02", "place_type": "City",
         "latitude": 51.9, "longitude": -176.6, "population_vintage": 2024, "estimates": {}, "model_estimates": {}},
    ]
    sources = [{"id": "EIS-1", "name": "Test facility", "latitude": 35.8, "longitude": -78.7,
                "pollutant_code": "PM25-PRI", "inventory_year": 2023, "emissions": 1.2, "units": "TON",
                "category": "Test", "url": "https://example.test/nei.zip"}]
    release = {"manifest.json": manifest, "places.json": places, "model.json": {"training_monitor_coordinates": [[35.5, -78.5]], "max_supported_nearest_monitor_km": 100}, "sources.json": sources, "monitors.json": []}
    monkeypatch.setattr(api, "read_release", lambda name: release[name])
    monkeypatch.setattr(api, "read_release_set", lambda names: national_data.ReleaseSet(
        {name: release[name] for name in names},
        {name: national_data.release_identity(name) for name in names},
    ))
    client = TestClient(api.app)

    result = client.get("/api/national/snapshot", params={"geoids": "3712000,0200065", "year": 2024})
    assert result.status_code == 200
    body = result.json()
    assert body["release_id"].startswith("upwind-national-test:")
    assert body["unknown_geoids"] == []
    assert body["items"][0]["coordinates"] == [-78.64, 35.78]
    assert body["items"][0]["estimate"]["reference_monitor_id"] == "37-183-0001"
    assert body["items"][0]["evidence_explanation"]["evidence_class"] == "modeled_place_point_estimate"
    assert "internal point" in body["items"][0]["evidence_explanation"]["why_this_appears"]
    assert body["items"][0]["nearby_inventory_records"][0]["facility_id"] == "EIS-1"
    inventory_why = body["items"][0]["nearby_inventory_records"][0]["evidence_explanation"]
    assert inventory_why["evidence_class"] == "facility_inventory_estimate"
    assert "not ambient concentration" in inventory_why["emissions_meaning"]
    assert "does not establish" in body["items"][0]["nearby_inventory_records"][0]["interpretation"]
    assert body["items"][1]["estimate"] is None
    assert "outside" in body["items"][1]["unsupported_reason"]

    csv_response = client.get("/api/national/snapshot.csv", params={"geoids": "3712000", "year": 2024})
    assert "attachment; filename=\"upwind-national-2024-snapshot.csv\"" in csv_response.headers["content-disposition"]
    assert "'=2+2" in csv_response.text
    assert "Evidence class" in csv_response.text and "modeled_place_point_estimate" in csv_response.text
    assert "Evidence limits JSON" in csv_response.text
    geo_response = client.get("/api/national/snapshot.geojson", params={"geoids": "3712000", "year": 2024})
    geo = geo_response.json()
    assert "upwind-national-2024-snapshot.geojson" in geo_response.headers["content-disposition"]
    assert geo["features"][0]["geometry"]["coordinates"] == [-78.64, 35.78]
    assert geo["features"][0]["properties"]["estimate"]["value_ug_m3"] == 8.0
    assert client.get("/api/national/snapshot", params={"geoids": "3712000,3712000"}).status_code == 422
    assert client.get("/api/national/snapshot", params={"geoids": "123"}).status_code == 422
    assert client.get("/api/national/snapshot", params={"geoids": "9999999"}).json()["unknown_geoids"] == ["9999999"]


def test_release_file_replacement_invalidates_reader_and_spatial_index(monkeypatch, tmp_path):
    monkeypatch.delenv("UPWIND_NATIONAL_RELEASE_DIR", raising=False)
    monkeypatch.setattr(national_data, "RELEASE", tmp_path)
    national_data._read_release.cache_clear()
    national_data._spatial_buckets.cache_clear()
    path = tmp_path / "places.json"
    first = [{"id": "0100001", "latitude": 35.0, "longitude": -78.0}]
    path.write_text(json.dumps(first))
    assert national_data.query_bounds("places.json", -79, 34, -77, 36)[0] == first
    replacement = [{"id": "0100002", "latitude": 35.0, "longitude": -78.0}]
    new_path = tmp_path / "replacement.json"
    new_path.write_text(json.dumps(replacement))
    new_path.replace(path)
    assert national_data.query_bounds("places.json", -79, 34, -77, 36)[0] == replacement
    national_data._read_release.cache_clear()
    national_data._spatial_buckets.cache_clear()


def test_release_set_retries_if_files_are_replaced_mid_snapshot(monkeypatch):
    identities = {name: 1 for name in ("manifest.json", "places.json")}
    values = {"manifest.json": {"release": "old"}, "places.json": [{"id": "old"}]}
    calls = {name: 0 for name in identities}

    def identity(name):
        calls[name] += 1
        # The first validation detects that places changed during the read.
        if name == "places.json" and calls[name] == 2:
            identities[name] = 2
            values[name] = [{"id": "new"}]
        return identities[name]

    monkeypatch.setattr(national_data, "release_identity", identity)
    monkeypatch.setattr(national_data, "_read_release", lambda name, release_id: values[name] if release_id == identities[name] else [{"id": "stale"}])
    result = national_data.read_release_set(("manifest.json", "places.json"))
    assert result["places.json"] == [{"id": "new"}]
