import json
import math
import asyncio
import csv
import hashlib
import io
import os
import re
import time
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from .models import Investigation, ImportRequest
from .national.data import read_release, read_release_set, release_identity, release_file_sha256, query_bounds, validate_bounds, haversine_km, aggregate_bounds
from .national.roads import major_road_context, SUPPORTED as OSM_ROAD_PLACES
from .national import data as national_data
from .national import roads as national_roads

app = FastAPI(title="UPWIND", version="0.1.0")
_cors_origins = [origin.strip() for origin in os.environ.get("UPWIND_CORS_ORIGINS", "").split(",") if origin.strip()]
if _cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "HEAD"],
        allow_headers=[],
    )
NATIONAL_MODEL_VERSION = "upwind-nearest-monitor-annual-pm25-0.3.0"
NATIONAL_PROTOCOL_VERSION = "UW-NATIONAL-SPATIAL-2026-04"
_post_capacity = asyncio.Semaphore(4)
_public_rate_windows: dict[str, tuple[int, int]] = {}
_public_rate_checks = 0
_PUBLIC_RATE_MAX_CLIENTS = 10_000
NATIONAL_PLACES_PAGE_MAX = 2_000
NATIONAL_MONITORS_PAGE_MAX = 5_000


def _public_mode() -> bool:
    return os.environ.get("UPWIND_PUBLIC_READONLY", "0").strip().lower() in {"1", "true", "yes"}


def _public_path_allowed(request: Request) -> bool:
    path = request.url.path
    return path in {"/api/health", "/api/ready"} or path.startswith("/api/national/")


def _public_preflight_allowed(request: Request) -> bool:
    return (
        request.method == "OPTIONS"
        and bool(_cors_origins)
        and request.headers.get("origin", "") in _cors_origins
        and request.headers.get("access-control-request-method", "GET") in {"GET", "HEAD"}
        and _public_path_allowed(request)
    )


def _public_client_key(request: Request) -> str:
    """Use forwarded identity only when the service explicitly trusts its proxy."""
    if os.environ.get("UPWIND_TRUST_PROXY", "0").strip().lower() in {"1", "true", "yes"}:
        forwarded = request.headers.get("x-forwarded-for", "").split(",")
        candidate = forwarded[-1].strip() if forwarded else ""
        if candidate and len(candidate) <= 128:
            return candidate
    return request.client.host if request.client and request.client.host else "unknown"


@app.middleware("http")
async def public_read_only_boundary(request: Request, call_next):
    """When deployed publicly, expose only the national read API and health."""
    if _public_mode():
        if _public_preflight_allowed(request):
            return await call_next(request)
        if request.method not in {"GET", "HEAD"} or not _public_path_allowed(request):
            return Response("Not found", status_code=404)
        # Compose exposes the API only to Caddy, which overwrites this header
        # with the socket peer address. Keep a modest per-client ceiling for
        # public reads; query results are separately bounded by each endpoint.
        client_ip = _public_client_key(request)
        now = int(time.monotonic() // 60)
        if client_ip not in _public_rate_windows and len(_public_rate_windows) >= _PUBLIC_RATE_MAX_CLIENTS:
            client_ip = "__overflow__"
        window, count = _public_rate_windows.get(client_ip, (now, 0))
        if window != now:
            window, count = now, 0
        if count >= 120:
            return Response(
                '{"detail":"Read request limit reached; retry next minute"}',
                status_code=429,
                media_type="application/json",
                headers={"Retry-After": str(60 - int(time.monotonic() % 60))},
            )
        _public_rate_windows[client_ip] = (window, count + 1)
        global _public_rate_checks
        _public_rate_checks += 1
        if _public_rate_checks % 256 == 0:
            for address, (minute, _) in tuple(_public_rate_windows.items()):
                if minute < now - 1:
                    _public_rate_windows.pop(address, None)
    return await call_next(request)


def _facility_identity(row: dict) -> dict:
    """Expose only the release's exact EIS identity; no proximity match is implied."""
    facility_id = str(row.get("facility_id") or row.get("id") or "")
    return {
        "facility_id": facility_id or None,
        "canonical_facility_id": f"epa-eis:{facility_id}" if facility_id else None,
        "provider": "EPA NEI",
        "provider_record_id": row.get("id"),
        "original_coordinates": [row.get("longitude"), row.get("latitude")],
        "coordinate_role": "reported EPA NEI facility coordinate; not a verified release point or footprint",
        "coordinate_precision": row.get("coordinate_precision", "as supplied by release; precision not independently verified"),
        "match_method": "exact EPA EIS facility identifier" if facility_id else "unresolved",
        "address": row.get("address"),
        "verified_footprint": None,
    }


@app.get("/api/national/viewport")
def national_viewport(layer: str, west: float, south: float, east: float, north: float,
                      zoom: float = 3, year: int = 2024, pollutant: str = "PM25", budget: int = 3000):
    """Complete, zoom-aware map representation; the symbol budget never caps records."""
    if not math.isfinite(zoom) or not 0 <= zoom <= 22:
        raise HTTPException(status_code=422, detail="zoom must be between 0 and 22")
    if not validate_bounds(west, south, east, north):
        raise HTTPException(status_code=422, detail="Invalid viewport bounds")
    if not 1 <= budget <= 3000:
        raise HTTPException(status_code=422, detail="budget must be between 1 and 3000 symbols")
    pollutant = pollutant.strip().upper()
    if layer == "estimates":
        name = "places.json"
        predicate = lambda row: str(year) in (row.get("model_estimates") or {})
        coordinate = lambda row: ((row.get("model_estimates") or {}).get(str(year), {}).get("estimate_latitude", row["latitude"]),
                                  (row.get("model_estimates") or {}).get(str(year), {}).get("estimate_longitude", row["longitude"]))
        value_for = lambda row: (row.get("model_estimates") or {}).get(str(year), {}).get("value_ug_m3")
    elif layer == "monitors":
        name = "monitors.json"
        predicate = lambda row: row.get("year") == year
        coordinate = None
        value_for = lambda row: row.get("pm25_ug_m3")
    elif layer == "sources":
        if not pollutant or len(pollutant) > 20:
            raise HTTPException(status_code=422, detail="Invalid pollutant filter")
        name = "sources.json"
        predicate = lambda row: row.get("pollutant", "").upper() == pollutant
        coordinate = None
        value_for = lambda row: row.get("emissions")
    else:
        raise HTTPException(status_code=422, detail="layer must be estimates, monitors, or sources")
    result = aggregate_bounds(name, west, south, east, north, zoom=zoom,
                              predicate=predicate, distinct_key="id" if layer == "sources" else None, budget=budget,
                              coordinate=coordinate, value_for=value_for)
    # Map responses carry only the fields needed to render and explain the active
    # layer. They never transfer complete national release rows to the browser.
    if layer == "estimates":
        fields = ("id", "name", "state", "state_fips", "place_type", "latitude", "longitude", "render_latitude", "render_longitude", "model_estimates", "cluster_id", "member_count", "is_cluster")
        for item in result["items"]:
            if not item.get("is_cluster"):
                estimate = (item.get("model_estimates") or {}).get(str(year))
                item["value"] = estimate.get("value_ug_m3") if estimate else None
                item["model_estimates"] = {str(year): estimate} if estimate else {}
            for key in tuple(item):
                if key not in fields and key != "value":
                    item.pop(key, None)
    elif layer == "monitors":
        fields = {"id", "year", "latitude", "longitude", "render_latitude", "render_longitude", "pm25_ug_m3", "units", "sample_completeness", "event_treatment", "source", "url", "state_fips", "county_fips", "cluster_id", "member_count", "is_cluster", "value"}
        result["items"] = [{key: value for key, value in item.items() if key in fields} for item in result["items"]]
    else:
        fields = {"id", "name", "company", "latitude", "longitude", "render_latitude", "render_longitude", "pollutant", "pollutant_code", "emissions", "units", "category", "inventory_year", "source", "url", "cluster_id", "member_count", "is_cluster", "value"}
        result["items"] = [{**{key: value for key, value in item.items() if key in fields}, **({} if item.get("is_cluster") else _facility_identity(item))} for item in result["items"]]
    explanations = {
        "estimates": {"evidence_class": "modeled_place_point_estimate", "why_this_appears": "A released annual PM2.5 model estimate is available at this Census Gazetteer internal point for the selected year.", "coordinate_meaning": "Census Gazetteer internal point; not a place boundary or area-average location.", "does_not_establish": ["current conditions", "citywide concentration", "personal exposure", "source contribution or responsibility"]},
        "monitors": {"evidence_class": "measured_monitor_summary", "why_this_appears": "An EPA AQS annual PM2.5 summary was released for this instrument site and selected year.", "coordinate_meaning": "Instrument-site coordinates; the measurement applies to the monitor, not every nearby location.", "does_not_establish": ["conditions between monitors", "personal exposure", "source contribution or responsibility"]},
        "sources": {"evidence_class": "facility_inventory_estimate", "why_this_appears": "An EPA NEI facility inventory summary row matches the selected pollutant filter.", "coordinate_meaning": "Reported facility inventory coordinates; this is an annual emissions record, not an ambient measurement.", "does_not_establish": ["ambient concentration", "contribution to a nearby monitor", "source responsibility for observed pollution"]},
    }
    result.update({"layer": layer, "filters": {"year": year, "pollutant": pollutant if layer == "sources" else None},
                  "evidence_explanation": explanations[layer]})
    return result


@app.get("/api/national/viewport-members")
def national_viewport_members(layer: str, cluster_id: str, west: float, south: float, east: float, north: float,
                              year: int = 2024, pollutant: str = "PM25", offset: int = 0, limit: int = 50):
    """Page exact members of a rendered grid cell, retaining the original viewport edge rule."""
    names = {"estimates": "places.json", "monitors": "monitors.json", "sources": "sources.json"}
    if layer not in names or not validate_bounds(west, south, east, north):
        raise HTTPException(status_code=422, detail="Invalid layer or viewport")
    try:
        name, level_s, x_s, y_s = cluster_id.split(":")
        level, target_x, target_y = int(level_s), int(x_s), int(y_s)
    except (ValueError, TypeError):
        raise HTTPException(status_code=422, detail="Invalid cluster identity") from None
    if name != names[layer] or not 0 <= level <= 20:
        raise HTTPException(status_code=422, detail="Cluster identity does not match the selected layer")
    pollutant = pollutant.strip().upper()
    n = 2 ** level
    def cell(lat, lon):
        lat = max(-85.05112878, min(85.05112878, float(lat)))
        x = int((float(lon) + 180) / 360 * n)
        y = int((1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n)
        return (min(n - 1, max(0, x)), min(n - 1, max(0, y)))
    matches, seen = [], set()
    for row in read_release(name):
        if not (west <= row["longitude"] <= east and south <= row["latitude"] <= north):
            continue
        if layer == "estimates":
            estimate = (row.get("model_estimates") or {}).get(str(year))
            if not estimate:
                continue
            lat, lon = estimate.get("estimate_latitude", row["latitude"]), estimate.get("estimate_longitude", row["longitude"])
        elif layer == "monitors":
            if row.get("year") != year:
                continue
            lat, lon = row["latitude"], row["longitude"]
        else:
            if row.get("pollutant", "").upper() != pollutant:
                continue
            if row.get("id") in seen:
                continue
            seen.add(row.get("id"))
            lat, lon = row["latitude"], row["longitude"]
        if cell(lat, lon) == (target_x, target_y):
            matches.append(row)
    start, size = max(0, offset), max(1, min(limit, 100))
    selected = matches[start:start + size]
    fields = {
        "estimates": {"id", "name", "state", "place_type", "latitude", "longitude", "model_estimates"},
        "monitors": {"id", "year", "latitude", "longitude", "pm25_ug_m3", "units", "sample_completeness", "event_treatment", "source", "url"},
        "sources": {"id", "name", "latitude", "longitude", "pollutant", "pollutant_code", "emissions", "units", "category", "inventory_year", "source", "url"},
    }[layer]
    return {"items": [{key: value for key, value in row.items() if key in fields} for row in selected],
            "total": len(matches), "offset": start, "limit": size, "next_offset": start + len(selected) if start + len(selected) < len(matches) else None,
            "cluster_id": cluster_id, "layer": layer, "year": year, "complete": True}


@app.get("/api/national/manifest")
def national_manifest():
    return read_release("manifest.json")


@app.get("/api/national/places")
def national_places(q: str = "", state: str = "", geoid: str = "", year: int = 2024, limit: int = NATIONAL_PLACES_PAGE_MAX, offset: int = 0, west: float | None = None, south: float | None = None, east: float | None = None, north: float | None = None):
    q_fold, state_fold = q.strip().casefold(), state.strip().casefold()
    geoid = geoid.strip()
    offset = max(0, offset)
    has_bounds = validate_bounds(west, south, east, north)
    limit = max(1, min(limit, NATIONAL_PLACES_PAGE_MAX))
    if has_bounds:
        data, total = query_bounds(
            "places.json", west, south, east, north, limit=limit, offset=offset,
            predicate=lambda place: (not q_fold or q_fold in place["name"].casefold())
            and (not geoid or place["id"] == geoid)
            and (not state_fold or state_fold in place["state"].casefold() or state_fold == place["state_fips"]),
        )
    else:
        data = read_release("places.json")
        matches = [place for place in data
                   if (not q_fold or q_fold in place["name"].casefold())
                   and (not geoid or place["id"] == geoid)
                   and (not state_fold or state_fold in place["state"].casefold() or state_fold == place["state_fips"])]
        total = len(matches)
        data = matches[max(0, offset):max(0, offset) + limit]
    selected = []
    for place in data:
        estimate = (place.get("model_estimates") or {}).get(str(year))
        has_estimate = estimate is not None
        selected.append({
            **place,
            "estimate": (place.get("estimates") or {}).get(str(year)),
            "evidence_explanation": {
                "evidence_class": "modeled_place_point_estimate" if has_estimate else "no_published_estimate",
                "why_this_appears": (
                    f"A released annual PM2.5 estimate for {year} is available at this Census Gazetteer internal point."
                    if has_estimate else f"No supported annual PM2.5 estimate is published for this place in {year}."
                ),
                "pollutant": "PM2.5", "units": "µg/m³", "period": f"annual {year}",
                "method": "nearest eligible EPA AQS monitor" if has_estimate else None,
                "location_meaning": "Census Gazetteer internal point; not a place boundary, neighborhood surface, or area average.",
                "supporting_monitor": ({
                    "id": estimate.get("reference_monitor_id"),
                    "distance_km": estimate.get("nearest_monitor_km"),
                    "measured_value_ug_m3": estimate.get("reference_monitor_value_ug_m3"),
                } if has_estimate else None),
                "uncertainty_interpretation": (
                    "Empirical spatial out-of-fold monitor-site error band; it is not a locally guaranteed interval."
                    if has_estimate else None
                ),
                "does_not_establish": ["current conditions", "citywide concentration", "personal exposure", "source contribution or responsibility"],
            },
        })
    next_offset = offset + len(selected) if offset + len(selected) < total else None
    return {"items": selected, "total": total, "year": year, "truncated": total > len(selected),
            "offset": max(0, offset), "limit": limit, "next_offset": next_offset}


@app.get("/api/national/monitors")
def national_monitors(year: int = 2024, site_id: str = "", west: float | None = None, south: float | None = None, east: float | None = None, north: float | None = None, limit: int = NATIONAL_MONITORS_PAGE_MAX, offset: int = 0):
    has_bounds = validate_bounds(west, south, east, north)
    limit = max(1, min(limit, NATIONAL_MONITORS_PAGE_MAX))
    offset = max(0, offset)
    if has_bounds:
        selected, total = query_bounds("monitors.json", west, south, east, north, limit=limit, offset=offset, predicate=lambda r: (year < 0 or r["year"] == year) and (not site_id or r["id"] == site_id))
    else:
        rows = read_release("monitors.json")
        selected = [r for r in rows if (year < 0 or r["year"] == year) and (not site_id or r["id"] == site_id)]
        total = len(selected)
        selected = selected[max(0, offset):max(0, offset) + limit]
    next_offset = offset + len(selected) if offset + len(selected) < total else None
    return {"items": selected, "year": year, "total": total, "truncated": total > len(selected),
            "offset": max(0, offset), "limit": limit, "next_offset": next_offset}


@app.get("/api/national/sources")
def national_sources(west: float | None = None, south: float | None = None, east: float | None = None, north: float | None = None, pollutant: str = "PM25", facility_id: str = "", limit: int = 3000, offset: int = 0):
    pollutant = pollutant.strip().upper()
    if not pollutant or len(pollutant) > 20:
        raise HTTPException(status_code=422, detail="Invalid pollutant filter")
    limit = max(1, min(limit, 3000))
    offset = max(0, offset)
    predicate = lambda row: pollutant == row.get("pollutant", "").upper() and (not facility_id or str(row.get("id")) == facility_id)
    if facility_id and not validate_bounds(west, south, east, north):
        all_rows = [row for row in read_release("sources.json") if predicate(row)]
        all_rows.sort(key=lambda row: row.get("emissions", 0), reverse=True)
        selected, total = all_rows[offset:offset + limit], len(all_rows)
        facility_count = len({str(row.get("id")) for row in all_rows})
    else:
        selected, total, facility_count = query_bounds(
            "sources.json", west, south, east, north, limit=limit, offset=offset,
            predicate=predicate,
            sort_key=lambda row: row.get("emissions", 0), distinct_key="id",
        )
    selected = [dict(row) for row in selected]
    for row in selected:
        # EIS is the only traceable identity in this release. Keep the official
        # archive URL and explicitly avoid inventing a per-facility URL.
        row.setdefault("facility_id", row.get("id"))
        row.setdefault("facility_record_url", None)
        row.update(_facility_identity(row))
    next_offset = offset + len(selected) if offset + len(selected) < total else None
    return {"items": selected, "total": total, "summary_rows": total, "facility_count": facility_count,
            "truncated": total > len(selected), "offset": max(0, offset), "limit": limit, "next_offset": next_offset,
            "inventory_year": 2023, "source_record_type": "EPA NEI facility emissions summary row",
            "ordering": "reported PM2.5-PRI emissions descending; tons/year"}


@app.get("/api/national/context")
def national_context(latitude: float, longitude: float, radius_km: float = 50.0,
                    pollutant: str = "PM25", monitor_year: int = 2024, limit: int = 20,
                    geoid: str = ""):
    """Return documented nearby evidence around a point, retaining its evidence class."""
    if not (math.isfinite(latitude) and -90 <= latitude <= 90
            and math.isfinite(longitude) and -180 <= longitude <= 180):
        raise HTTPException(status_code=422, detail="Latitude and longitude must be finite WGS84 coordinates")
    if not math.isfinite(radius_km) or not 0 < radius_km <= 250:
        raise HTTPException(status_code=422, detail="radius_km must be greater than 0 and at most 250")
    pollutant = pollutant.strip().upper()
    if not pollutant or len(pollutant) > 20:
        raise HTTPException(status_code=422, detail="Invalid pollutant filter")
    limit = max(1, min(limit, 100))

    # Search only a conservative bounding box around the requested radius; the
    # exact great-circle test below determines membership and distance.
    lat_delta = radius_km / 110.574
    lon_scale = max(0.01, math.cos(math.radians(latitude)))
    lon_delta = min(180.0, radius_km / (111.320 * lon_scale))
    west, east = max(-180.0, longitude - lon_delta), min(180.0, longitude + lon_delta)
    south, north = max(-90.0, latitude - lat_delta), min(90.0, latitude + lat_delta)
    def all_candidates(name: str, predicate):
        # query_bounds is deliberately paged: context counts and rankings must
        # cover the whole radius even when its bounding box exceeds one page.
        page_size = 10000
        page, total = query_bounds(name, west, south, east, north, limit=page_size, offset=0, predicate=predicate)
        rows = list(page)
        for offset in range(page_size, total, page_size):
            next_page, _ = query_bounds(name, west, south, east, north, limit=page_size, offset=offset, predicate=predicate)
            rows.extend(next_page)
        return rows

    candidates = all_candidates("monitors.json", lambda row: row.get("year") == monitor_year)
    monitor_items = []
    for row in candidates:
        distance = haversine_km(latitude, longitude, float(row["latitude"]), float(row["longitude"]))
        if distance <= radius_km:
            monitor_items.append({
                "evidence_class": "measured_monitor_summary", "id": row.get("id"),
                "distance_km": round(distance, 3), "relation": "near_point",
                "year": row.get("year"), "value_ug_m3": row.get("pm25_ug_m3"),
                "units": row.get("units"), "sample_completeness": row.get("sample_completeness"),
                "event_treatment": row.get("event_treatment"), "source": row.get("source"),
                "source_url": row.get("url"),
                "interpretation": "Measured at an instrument site; proximity does not mean the monitor is inside a Census place boundary.",
            })

    sources = all_candidates("sources.json", lambda row: pollutant == row.get("pollutant", "").upper())
    source_items = []
    for row in sources:
        distance = haversine_km(latitude, longitude, float(row["latitude"]), float(row["longitude"]))
        if distance <= radius_km:
            source_items.append({
                "evidence_class": "facility_inventory_estimate", "id": row.get("id"),
                "distance_km": round(distance, 3), "relation": "near_point",
                "inventory_year": row.get("inventory_year"), "pollutant_code": row.get("pollutant_code"),
                "emissions": row.get("emissions"), "units": row.get("units"),
                "category": row.get("category"), "source": row.get("source"),
                "source_url": row.get("url"), "facility_record_url": None,
                "interpretation": "Annual facility inventory estimate, not ambient concentration; proximity does not establish contribution or responsibility.",
            })
    # Keep evidence classes separate. Largest rows are ranked only within a
    # compatible pollutant-code/unit group; magnitude is inventory mass, not
    # ambient contribution.
    key = lambda item: (item["distance_km"], str(item["id"]))
    monitor_items.sort(key=key)
    source_items.sort(key=key)
    all_items = sorted(monitor_items + source_items, key=lambda item: (item["distance_km"], item["evidence_class"], str(item["id"])))
    inventory_groups = {}
    for item in source_items:
        group_key = (str(item.get("pollutant_code") or pollutant), str(item.get("units") or "unknown"))
        inventory_groups.setdefault(group_key, []).append(item)
    largest_compatible = []
    for (pollutant_code, units), records in sorted(inventory_groups.items()):
        ranked = sorted(records, key=lambda item: (-(item.get("emissions") or 0), item["distance_km"], str(item["id"])))
        largest_compatible.append({
            "pollutant_code": pollutant_code, "units": units,
            "records": ranked[:min(limit, 10)], "compatible_record_count": len(records),
            "ranking_meaning": f"Reported annual emissions descending within {pollutant_code} records measured in {units}.",
        })
    road_geoid = min(
        OSM_ROAD_PLACES,
        key=lambda key: haversine_km(latitude, longitude, OSM_ROAD_PLACES[key][1], OSM_ROAD_PLACES[key][2]),
    )
    road_distance = haversine_km(latitude, longitude, OSM_ROAD_PLACES[road_geoid][1], OSM_ROAD_PLACES[road_geoid][2])
    road_context = major_road_context(road_geoid if road_distance <= 0.01 else "", latitude, longitude)
    place_evidence = None
    if geoid:
        if not re.fullmatch(r"[0-9]{7}", geoid):
            raise HTTPException(status_code=422, detail="geoid must be a seven-digit Census place identifier")
        matching_place = next((place for place in read_release("places.json") if str(place.get("id")) == geoid), None)
        if matching_place:
            estimate = (matching_place.get("model_estimates") or {}).get(str(monitor_year))
            place_evidence = {
                "evidence_class": "modeled_place_point_estimate" if estimate else "no_published_estimate",
                "place": {"id": geoid, "name": matching_place.get("name"), "state": matching_place.get("state")},
                "year": monitor_year, "estimate": estimate,
                "coordinate_meaning": "Census Gazetteer internal point; not a place boundary or area average.",
                "uncertainty": estimate.get("interval_interpretation") if estimate else matching_place.get("withheld_reason"),
            }
    return {
        "query": {"latitude": latitude, "longitude": longitude, "radius_km": radius_km,
                  "pollutant": pollutant, "monitor_year": monitor_year},
        "items": all_items[:limit], "total": len(monitor_items) + len(source_items),
        "returned": min(limit, len(all_items)), "truncated": len(all_items) > limit,
        "nearest_monitors": monitor_items[:min(limit, 10)],
        "closest_facilities": source_items[:min(limit, 10)],
        "largest_compatible_inventory_groups": largest_compatible,
        "counts": {"measured_monitor_summaries": len(monitor_items),
                   "facility_inventory_summary_rows": len(source_items),
                   "distinct_facilities": len({str(x["id"]) for x in source_items})},
        "provenance": {"monitor_source": "EPA AQS annual PM2.5 monitor summaries",
                       "inventory_source": "EPA National Emissions Inventory facility summary rows",
                       "monitor_year": monitor_year, "inventory_year": 2023,
                       "ranking": "great-circle distance ascending, then evidence class and stable record ID; inventory emissions are not a ranking weight"},
        "monitoring_gap": {
            "status": "no_monitor_summary_within_radius" if not monitor_items else "monitor_summaries_within_radius",
            "monitor_summary_count": len(monitor_items), "radius_km": radius_km,
            "meaning": "A zero count means this release has no eligible AQS annual site summary within the selected radius and year; it does not prove an area has no monitoring of any kind.",
        },
        "place_evidence": place_evidence,
        "road_context": road_context,
        "limitations": [
            "A Census Gazetteer point is not a legal place boundary; this endpoint measures distance from the supplied point only.",
            "Near means within the requested radius and does not mean inside a place boundary.",
            "Monitor summaries are measured at instrument sites; facility records are annual inventory estimates, not ambient measurements.",
            "Proximity and inventory emissions do not establish facility contribution, source responsibility, or local air quality.",
            "OpenStreetMap road proximity and mapped road length are geographic context only; they do not represent traffic, emissions, concentration, or causal contribution. Road metrics cover only the bounded Durham and Charlotte extracts.",
        ],
    }


SNAPSHOT_LIMIT = 5
_GEOID = re.compile(r"^[0-9]{7}$")
_SNAPSHOT_LIMITATIONS = (
    "Values are annual PM2.5 point estimates at Census Gazetteer internal points, not place averages, current conditions, "
    "personal exposure, forecasts, health risk, or causal/source attribution. The empirical spatial out-of-fold error band "
    "does not guarantee local coverage. EPA facility inventory records are emissions estimates, not ambient measurements "
    "or evidence of contribution."
)


def _release_identity(manifest: dict, identities: dict | None = None) -> str:
    # Include all inputs that materially change snapshot content, even if an
    # operator replaces a generated file without updating manifest.json.
    files = ("manifest.json", "places.json", "model.json", "monitors.json", "sources.json")
    file_hashes = {}
    for name in files:
        identity = (identities or {}).get(name) or release_identity(name)
        if identity != release_identity(name):
            raise HTTPException(status_code=503, detail="National release changed while preparing the snapshot; retry the request")
        file_hashes[name] = release_file_sha256(name, identity)
        if identity != release_identity(name):
            raise HTTPException(status_code=503, detail="National release changed while preparing the snapshot; retry the request")
    payload = json.dumps(
        {"manifest": manifest, "files": file_hashes},
        sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")
    release = manifest.get("release", "unknown-release")
    return f"{release}:{hashlib.sha256(payload).hexdigest()[:16]}"


def _source_vintages(manifest: dict) -> dict:
    sources = manifest.get("dataset_sources") or {}
    return {
        "aqs": sources.get("EPA AQS annual PM2.5 monitor summaries"),
        "census_gazetteer": sources.get("Census place Gazetteer"),
        "census_population": sources.get("Census population"),
        "epa_nei": sources.get("EPA National Emissions Inventory"),
    }


def _unsupported_reason(place: dict, year: int, manifest: dict, model: dict) -> str:
    selected_year = int(manifest.get("selected_modeling_year", 2024))
    if year != selected_year:
        return f"No place estimate is published for {year}; the deployed model was fit for {selected_year}. Monitor observations for other years remain separate measured records."
    lat, lon = float(place["latitude"]), float(place["longitude"])
    if not (24 <= lat <= 50 and -125 <= lon <= -66):
        return "The Gazetteer point is outside the model's declared contiguous-U.S. domain."
    coords = model.get("training_monitor_coordinates") or []
    if coords:
        nearest = min(haversine_km(lat, lon, float(coord[0]), float(coord[1])) for coord in coords)
        threshold = model.get("max_supported_nearest_monitor_km")
        if threshold is not None and nearest > float(threshold):
            return (f"No estimate is published because the nearest eligible training monitor is {nearest:.1f} km away, "
                    f"beyond the {float(threshold):.1f} km spatial out-of-fold support threshold.")
    return "The release contains no supported place estimate for this year; it does not record a more specific withholding reason."


def _nearby_inventory(place: dict, sources: list[dict], *, radius_km: float = 50.0, limit: int = 4) -> list[dict]:
    nearby = []
    for row in sources:
        distance = haversine_km(float(place["latitude"]), float(place["longitude"]), float(row["latitude"]), float(row["longitude"]))
        if distance <= radius_km:
            nearby.append((distance, row))
    nearby.sort(key=lambda item: (item[1].get("emissions", 0), -item[0]), reverse=True)
    return [
        {"facility_id": row.get("id"), "summary_row_id": row.get("id"), "name": row.get("name"),
         "pollutant_code": row.get("pollutant_code"), "inventory_year": row.get("inventory_year"),
         "emissions": row.get("emissions"), "units": row.get("units"), "category": row.get("category"),
         "distance_km": round(distance, 3), "source_url": row.get("url"), "facility_record_url": None,
         "interpretation": "Nearby inventory record only; proximity does not establish an ambient contribution or responsibility.",
         "evidence_explanation": {"evidence_class": "facility_inventory_estimate",
             "why_this_appears": f"This EPA NEI facility summary row is within {radius_km:g} km of the Census Gazetteer internal point.",
             "distance_meaning": "Great-circle distance to the internal point, not distance to the place boundary.",
             "emissions_meaning": "Annual inventory estimate in the reported source units; not ambient concentration.",
             "does_not_establish": ["contribution to a nearby monitor", "source responsibility", "local air quality"]}}
        for distance, row in nearby[:limit]
    ]


def _snapshot(geoids: str, year: int) -> dict:
    requested = [value.strip() for value in geoids.split(",")]
    if any(not value for value in requested):
        raise HTTPException(status_code=422, detail="GEOID list cannot contain empty entries")
    if not 1 <= len(requested) <= SNAPSHOT_LIMIT:
        raise HTTPException(status_code=422, detail=f"Provide between 1 and {SNAPSHOT_LIMIT} GEOIDs")
    if len(set(requested)) != len(requested):
        raise HTTPException(status_code=422, detail="GEOIDs must be unique")
    if any(not _GEOID.fullmatch(value) for value in requested):
        raise HTTPException(status_code=422, detail="Each GEOID must contain exactly seven digits")
    release = read_release_set(("manifest.json", "places.json", "model.json", "sources.json"))
    manifest = release["manifest.json"]
    places = release["places.json"]
    model = release["model.json"]
    by_id = {place["id"]: place for place in places}
    unknown = [geoid for geoid in requested if geoid not in by_id]
    sources = release["sources.json"]
    # Tie every representation to immutable release time so JSON, CSV, and
    # GeoJSON remain byte-stable for the same release and query.
    now = manifest.get("built_utc")
    source_vintages = _source_vintages(manifest)
    rows = []
    for geoid in requested:
        place = by_id.get(geoid)
        if not place:
            continue
        estimate = (place.get("model_estimates") or {}).get(str(year))
        # Preserve the legacy v1 model-estimate field if present in a release.
        if estimate is None and isinstance(place.get("model_estimates"), dict):
            estimate = None
        estimate_record = None
        if estimate:
            estimate_record = {
                "value_ug_m3": estimate.get("value_ug_m3"),
                "interval90_low_ug_m3": estimate.get("interval90_low_ug_m3"),
                "interval90_high_ug_m3": estimate.get("interval90_high_ug_m3"),
                "interval_interpretation": "Symmetric empirical 90th-percentile absolute spatial out-of-fold monitor-site residual band; not a locally guaranteed interval.",
                "evidence_status": estimate.get("evidence_status"),
                "model_id": estimate.get("model_id"),
                "method": manifest.get("model", {}).get("method"),
                "nearest_monitor_km": estimate.get("nearest_monitor_km"),
                "reference_monitor_id": estimate.get("reference_monitor_id"),
                "reference_monitor_value_ug_m3": estimate.get("reference_monitor_value_ug_m3"),
                "support": estimate.get("support"),
            }
        rows.append({
            "id": place["id"], "name": place["name"], "state": place["state"],
            "state_fips": place["state_fips"], "place_type": place.get("place_type"),
            "coordinates": [place["longitude"], place["latitude"]], "coordinate_reference_system": "WGS84",
            "coordinate_meaning": "Census Gazetteer internal point; not a place boundary or area-average location.",
            "evidence_explanation": {
                "evidence_class": "modeled_place_point_estimate" if estimate_record else "no_published_estimate",
                "why_this_appears": ("A released annual PM2.5 model estimate is available at this Census Gazetteer internal point for the selected year."
                                      if estimate_record else _unsupported_reason(place, year, manifest, model)),
                "coordinate_meaning": "Census Gazetteer internal point; not a place boundary or area-average location.",
                "does_not_establish": ["current conditions", "citywide concentration", "personal exposure", "source contribution or responsibility"]},
            "pollutant": "PM2.5", "units": "µg/m³", "year": year,
            "estimate": estimate_record,
            "unsupported_reason": None if estimate_record else _unsupported_reason(place, year, manifest, model),
            "population_2024": (place.get("estimates") or {}).get("2024"),
            "population_vintage": place.get("population_vintage"),
            "dataset_sources": source_vintages, "generated_utc": now,
            "nearby_inventory_records": _nearby_inventory(place, sources),
            "limitations": _SNAPSHOT_LIMITATIONS,
        })
    return {
        "release": manifest.get("release"), "release_id": _release_identity(manifest, release.identities),
        "built_utc": manifest.get("built_utc"), "year": year, "generated_utc": now,
        "requested_geoids": requested, "unknown_geoids": unknown, "items": rows,
        "dataset_sources": source_vintages, "limitations": _SNAPSHOT_LIMITATIONS,
    }


@app.get("/api/national/snapshot")
def national_snapshot(geoids: str = "", year: int = 2024):
    return _snapshot(geoids, year)


def _snapshot_csv(snapshot: dict) -> str:
    columns = [
        "GEOID", "Place", "State", "State FIPS", "Place type", "Longitude WGS84", "Latitude WGS84",
        "Coordinate meaning", "Evidence class", "Why this appears", "Evidence limits JSON", "Pollutant", "Units", "Year", "Estimate µg/m³", "90% OOF band low µg/m³",
        "90% OOF band high µg/m³", "Evidence status", "Model ID", "Method", "Nearest monitor km",
        "90% interval interpretation", "Spatial support", "Reference monitor ID", "Reference monitor value µg/m³", "Unsupported reason", "Population 2024",
        "Population vintage", "Nearby EPA NEI records JSON", "Dataset sources JSON", "Release", "Release ID",
        "Built UTC", "Generated UTC", "Limitations",
    ]
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\r\n")
    writer.writerow(columns)
    for place in snapshot["items"]:
        estimate = place.get("estimate") or {}
        values = [
            place["id"], place["name"], place["state"], place["state_fips"], place["place_type"],
            place["coordinates"][0], place["coordinates"][1], place["evidence_explanation"]["coordinate_meaning"],
            place["evidence_explanation"]["evidence_class"],
            place["evidence_explanation"]["why_this_appears"], json.dumps(place["evidence_explanation"]["does_not_establish"], ensure_ascii=False),
            place["pollutant"], place["units"], place["year"], estimate.get("value_ug_m3"), estimate.get("interval90_low_ug_m3"),
            estimate.get("interval90_high_ug_m3"), estimate.get("evidence_status"), estimate.get("model_id"),
            estimate.get("method"), estimate.get("nearest_monitor_km"), estimate.get("interval_interpretation"),
            estimate.get("support"), estimate.get("reference_monitor_id"),
            estimate.get("reference_monitor_value_ug_m3"), place.get("unsupported_reason"), place.get("population_2024"),
            place.get("population_vintage"), json.dumps(place["nearby_inventory_records"], ensure_ascii=False),
            json.dumps(place["dataset_sources"], ensure_ascii=False), snapshot["release"], snapshot["release_id"],
            snapshot["built_utc"], snapshot["generated_utc"], place["limitations"],
        ]
        safe = []
        for value in values:
            if isinstance(value, str) and re.match(r"^[\s\x00-\x1f\ufeff\u200b]*[=+@-]", value):
                value = "'" + value
            safe.append(value)
        writer.writerow(safe)
    return output.getvalue()


@app.get("/api/national/snapshot.csv")
def national_snapshot_csv(geoids: str = "", year: int = 2024):
    snapshot = _snapshot(geoids, year)
    return Response(_snapshot_csv(snapshot), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="upwind-national-{year}-snapshot.csv"'})


@app.get("/api/national/snapshot.geojson")
def national_snapshot_geojson(geoids: str = "", year: int = 2024):
    snapshot = _snapshot(geoids, year)
    features = []
    for place in snapshot["items"]:
        estimate = place.get("estimate") or {}
        features.append({
            "type": "Feature", "geometry": {"type": "Point", "coordinates": place["coordinates"]},
            "properties": {key: value for key, value in place.items() if key != "coordinates"},
        })
    geojson = {"type": "FeatureCollection", "name": "UPWIND National Explorer community snapshot",
               "metadata": {key: snapshot[key] for key in ("release", "release_id", "built_utc", "year", "generated_utc", "dataset_sources", "limitations")},
               "features": features}
    return Response(json.dumps(geojson, ensure_ascii=False), media_type="application/geo+json",
                    headers={"Content-Disposition": f'attachment; filename="upwind-national-{year}-snapshot.geojson"'})


def _finite_json_float(text):
    value = float(text)
    if not math.isfinite(value):
        raise ValueError("JSON numbers must be finite")
    return value


def _reject_json_constant(text):
    raise ValueError("Nonstandard JSON number: " + text)


def _validate_json_body(raw):
    value = json.loads(
        raw, parse_float=_finite_json_float, parse_constant=_reject_json_constant
    )
    pending = [(value, 0)]
    while pending:
        node, depth = pending.pop()
        if depth > 64:
            raise ValueError("JSON nesting exceeds64levels")
        if isinstance(node, dict):
            pending.extend((item, depth + 1) for item in node.values())
        elif isinstance(node, list):
            pending.extend((item, depth + 1) for item in node)


@app.middleware("http")
async def size_limit(request: Request, call_next):
    # Stream limit also covers clients without Content-Length.
    # This middleware is registered after the other wrappers and therefore
    # runs first. Reject public writes before reading or validating a body.
    if _public_mode() and not _public_preflight_allowed(request) and (request.method not in {"GET", "HEAD"} or not _public_path_allowed(request)):
        return Response("Not found", status_code=404)
    if request.method in {"POST", "PUT"}:
        chunks, size = [], 0
        async for chunk in request.stream():
            size += len(chunk)
            if size > 8_000_000:
                return Response("Request exceeds 8 MB limit", status_code=413)
            chunks.append(chunk)
        request._body = b"".join(chunks)
        try:
            _validate_json_body(request._body)
        except (ValueError, RecursionError) as exc:
            return Response(
                json.dumps({"detail": "Invalid JSON request: " + str(exc)}),
                status_code=422,
                media_type="application/json",
            )
    try:
        return await call_next(request)
    except ValueError as e:
        return Response(
            json.dumps({"detail": str(e)}),
            status_code=422,
            media_type="application/json",
        )


@app.get("/api/health")
def health():
    if _public_mode():
        model_version, protocol_version = NATIONAL_MODEL_VERSION, NATIONAL_PROTOCOL_VERSION
    else:
        from .engine import MODEL_VERSION, PROTOCOL_VERSION
        model_version, protocol_version = MODEL_VERSION, PROTOCOL_VERSION
    return {
        "status": "ok",
        "version": "0.1.0",
        "model_version": model_version,
        "protocol_version": protocol_version,
        "product": "national-explorer" if _public_mode() else "local-research-engine",
        "evidence": "historical release evidence" if _public_mode() else "synthetic evaluations only",
    }


@app.get("/api/ready")
def ready():
    """Deployment readiness: every runtime release artifact and road extract exists."""
    required = [
        (national_data.release_dir(), name)
        for name in ("manifest.json", "places.json", "model.json", "monitors.json", "sources.json")
    ]
    required.extend((national_roads.road_dir(), f"{city}.{suffix}")
                    for city in ("durham", "charlotte") for suffix in ("osm", "metadata.json"))
    missing = [str(directory / name) for directory, name in required
               if not (directory / name).is_file() or (directory / name).stat().st_size == 0]
    malformed = []
    for directory, name in required[:5]:
        path = directory / name
        if str(path) in missing:
            continue
        try:
            json.loads(path.read_text())
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            malformed.append(str(path))
    if malformed:
        return Response(
            json.dumps({"status": "not_ready", "malformed_files": malformed}),
            status_code=503,
            media_type="application/json",
        )
    if missing:
        return Response(
            json.dumps({"status": "not_ready", "missing_files": missing}),
            status_code=503,
            media_type="application/json",
        )
    return {"status": "ready", "release": "national explorer data and bounded road context available"}


@app.middleware("http")
async def bounded_post_admission(request: Request, call_next):
    # Reject overload before buffering large JSON bodies. One application worker
    # owns this event-loop semaphore; health/reads stay available under load.
    if os.environ.get("UPWIND_PUBLIC_READONLY", "0").strip().lower() in {"1", "true", "yes"}:
        path = request.url.path
        allowed = path in {"/api/health", "/api/ready"} or path.startswith("/api/national/")
        if not _public_preflight_allowed(request) and (request.method not in {"GET", "HEAD"} or not allowed):
            return Response("Not found", status_code=404)
    if request.method not in {"POST", "PUT"}:
        return await call_next(request)
    if _post_capacity.locked():
        return Response(
            '{"detail":"Four requests are already processing; retry shortly"}',
            status_code=429,
            media_type="application/json",
            headers={"Retry-After": "1"},
        )
    await _post_capacity.acquire()
    try:
        return await call_next(request)
    finally:
        _post_capacity.release()


@app.get("/api/demo")
def demo():
    from .fixtures import synthetic_case
    inv, _ = synthetic_case()
    return inv


@app.get("/api/demo/campaign")
def campaign_demo():
    from .campaign_fixture import synthetic_campaign

    return synthetic_campaign()


@app.post("/api/analyze")
def analysis(inv: Investigation):
    from .engine import analyze
    return analyze(inv)


@app.post("/api/import/csv")
def import_csv(req: ImportRequest):
    from .importers import parse_csv
    try:
        rows, record = parse_csv(req)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    return {"rows": [r.model_dump() for r in rows], "record": record}


@app.get("/api/investigations")
def investigations():
    from . import store
    return store.list_all()


@app.post("/api/investigations")
def save(inv: Investigation):
    from . import store
    from .engine import analyze
    from .models import migrate_analysis
    migrate_analysis(inv)
    if inv.result is not None:
        inv.result = analyze(inv)
    return store.save(inv)


@app.post("/api/investigations/import")
def import_investigation(inv: Investigation):
    from . import store
    from .engine import analyze
    from .models import migrate_analysis
    migrate_analysis(inv)
    inv.id = ""
    if inv.result is not None:
        inv.result = analyze(inv)
    return store.save(inv)


def lookup(id):
    from . import store
    try:
        return store.load(id)
    except KeyError:
        raise HTTPException(404, "Investigation not found")


@app.get("/api/investigations/{id}")
def get_investigation(id: str):
    return lookup(id)


@app.get("/api/investigations/{id}/export")
def export(id: str):
    return Response(
        lookup(id).model_dump_json(indent=2),
        media_type="application/json",
        headers={
            "Content-Disposition": 'attachment; filename="upwind-investigation.json"'
        },
    )


@app.get("/api/investigations/{id}/measurements.csv")
def export_csv(id: str):
    from .report import measurements_csv
    return Response(
        measurements_csv(lookup(id)),
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="upwind-measurements.csv"'
        },
    )


@app.get("/api/investigations/{id}/report", response_class=HTMLResponse)
def report(id: str):
    from .report import evidence_report
    return HTMLResponse(
        evidence_report(lookup(id)),
        headers={
            "Content-Disposition": 'attachment; filename="upwind-evidence.html"',
            "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'",
        },
    )


# Run `npm run build` first for a single-process local production application.
dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if dist.exists():
    @app.get("/explore", include_in_schema=False)
    def national_explorer_page():
        return FileResponse(dist / "index.html")

    app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")
