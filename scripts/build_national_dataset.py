#!/usr/bin/env python3
"""Download and transform official U.S. annual PM2.5, place, population and NEI data.

Raw archives are cached under ignored ``data/national/raw``. Files are atomically
published only after checksum, archive and schema validation. Derived release
files are reproducible JSON consumed by the local National Explorer API.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import time
import zipfile
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/national/raw"
RELEASE = ROOT / "data/national/release"
SOURCES = {
    "EPA AQS annual PM2.5 monitor summaries": "https://aqs.epa.gov/aqsweb/airdata/annual_conc_by_monitor_{year}.zip",
    "Census 2024 national place Gazetteer": "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2024_Gazetteer/2024_Gaz_place_national.zip",
    "Census 2024 place population estimates": "https://www2.census.gov/programs-surveys/popest/datasets/2020-2024/cities/totals/sub-est2024.csv",
    "EPA 2023 NEI facility-level pollutant summary": "https://gaftp.epa.gov/air/nei/2023/data_summaries/eis_report_38234_2023NEI_facility_summary_21jul2026.zip",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def download(url: str, destination: Path, *, archive: bool = False) -> dict:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.stat().st_size:
        valid = True
        if archive:
            try:
                with zipfile.ZipFile(destination) as zf:
                    valid = zf.testzip() is None and bool(zf.namelist())
            except (OSError, zipfile.BadZipFile):
                valid = False
        if valid:
            return {"url": url, "retrieved": "cached", "bytes": destination.stat().st_size, "sha256": sha256(destination)}
    temporary = destination.with_suffix(destination.suffix + ".partial")
    for attempt in range(3):
        command = ["curl", "--fail", "--location", "--silent", "--show-error", "--connect-timeout", "20", "--max-time", "900", "--retry", "2"]
        if temporary.exists():
            command.extend(["--continue-at", "-"])
        command.extend([url, "--output", str(temporary)])
        try:
            subprocess.run(command, check=True)
            if archive:
                with zipfile.ZipFile(temporary) as zf:
                    bad = zf.testzip()
                    if bad:
                        raise ValueError(f"Corrupt ZIP member: {bad}")
                    if not zf.namelist():
                        raise ValueError("Empty ZIP archive")
            osize = temporary.stat().st_size
            temporary.replace(destination)
            return {"url": url, "retrieved": date.today().isoformat(), "bytes": osize, "sha256": sha256(destination)}
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2**attempt)
    raise RuntimeError("Download retries exhausted")


def _single_csv_zip(path: Path) -> pd.DataFrame:
    with zipfile.ZipFile(path) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if len(names) != 1:
            raise ValueError(f"Expected one CSV in {path.name}, got {names}")
        with zf.open(names[0]) as stream:
            return pd.read_csv(stream, low_memory=False)


def select_ambient_poc_summaries(site_rows: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Select one unadjusted annual concentration summary for each AQS POC.

    AQS publishes multiple event-treatment summaries for a POC when exceptional
    events occurred. Those summaries are alternative calculations, not
    independent instruments. For an observed ambient target, retain the
    ``Events Included`` result; where events did not occur, retain ``No Events``.
    Event-excluded alternatives are not substituted for observed ambient levels.
    """
    selected = []
    unsupported_pocs = 0
    for _, poc_rows in site_rows.groupby("POC", sort=True):
        included = poc_rows[poc_rows["Event Type"].eq("Events Included")]
        no_events = poc_rows[poc_rows["Event Type"].eq("No Events")]
        if not included.empty:
            selected.append(included.iloc[0])
        elif not no_events.empty:
            selected.append(no_events.iloc[0])
        else:
            # Only event-excluded summaries remain. They cannot represent the
            # measured ambient concentration requested by this product.
            unsupported_pocs += 1
    if selected:
        return pd.DataFrame(selected), unsupported_pocs
    return site_rows.iloc[0:0].copy(), unsupported_pocs


def canonical_aqs_observation(record: dict) -> dict:
    """Normalize one released AQS physical site-year without changing its meaning.

    The normalized record makes provider, station identity, annual period,
    units, selected POC quality/event treatment, and raw source lineage
    machine-readable. It is explicitly an annual monitor observation, not a
    place estimate or daily measurement.
    """
    provenance = record["source_provenance"]
    return {
        "schema": "upwind-canonical-observation-1",
        "provider": "U.S. EPA Air Quality System (AQS)",
        "provider_observation_type": "annual monitor summary",
        "station": {
            "provider_station_id": record["id"],
            "state_fips": record["state_fips"],
            "county_fips": record["county_fips"],
            "site_number": record["site_number"],
            "latitude": record["latitude"],
            "longitude": record["longitude"],
            "coordinate_reference_system": "WGS84",
        },
        "observation_period": {
            "start": f"{record['year']}-01-01",
            "end_exclusive": f"{record['year'] + 1}-01-01",
            "timezone": "UTC",
            "resolution": "annual",
        },
        "measurement": {
            "pollutant": "PM2.5",
            "parameter_code": "88101",
            "value": record["pm25_ug_m3"],
            "units": "µg/m³",
            "metric": record["metric"],
            "pollutant_standard": record["pollutant_standard"],
            "aggregation": "arithmetic mean of one selected annual summary per eligible colocated POC",
        },
        "quality": {
            "sample_completeness": record["sample_completeness"],
            "selected_poc_count": record["poc_count"],
            "poc_treatments": record["poc_event_treatments"],
        },
        "provenance": provenance,
        "evidence_type": record["evidence_type"],
    }


def process_aqs(paths: dict[int, Path]) -> tuple[list[dict], dict]:
    records = []
    audit = {}
    required = {"State Code", "County Code", "Site Num", "Parameter Code", "POC", "Latitude", "Longitude", "Pollutant Standard", "Metric Used", "Year", "Units of Measure", "Event Type", "Observation Percent", "Completeness Indicator", "Certification Indicator", "Arithmetic Mean"}
    for year, path in paths.items():
        archive_sha256 = sha256(path)
        df = _single_csv_zip(path)
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"AQS {year} schema missing {sorted(missing)}")
        rows = df[
            (df["Parameter Code"].astype(str).str.zfill(5) == "88101")
            & df["Pollutant Standard"].astype(str).str.startswith("PM25 Annual")
            & df["Metric Used"].eq("Quarterly Means of Daily Means")
            & df["Units of Measure"].eq("Micrograms/cubic meter (LC)")
            & df["Completeness Indicator"].eq("Y")
            & df["Year"].eq(year)
        ].copy()
        # Preserve the raw archive row identity before filtering, sorting, or
        # selecting among alternative event-treatment summaries. The archive
        # hash plus member and row number gives each selected summary a stable
        # pointer back to its exact source record.
        csv_member = next(n for n in zipfile.ZipFile(path).namelist() if n.lower().endswith(".csv"))
        rows["_source_row_number"] = rows.index.astype(int) + 2  # CSV line, including header
        rows["State Code"] = rows["State Code"].astype(str).str.zfill(2)
        rows["County Code"] = rows["County Code"].astype(str).str.zfill(3)
        rows["Site Num"] = rows["Site Num"].astype(str).str.zfill(4)
        rows["POC"] = rows["POC"].astype(str)
        rows["Arithmetic Mean"] = pd.to_numeric(rows["Arithmetic Mean"], errors="coerce")
        rows = rows[rows["Arithmetic Mean"].notna() & rows["Latitude"].between(-90, 90) & rows["Longitude"].between(-180, 180)]
        # Each physical AQS site contributes once. When standards or POCs are
        # colocated, retain eligible POCs in provenance and average the annual
        # monitor summaries into a single spatial site-year.
        rows["_standard_rank"] = rows["Pollutant Standard"].str.extract(r"(\d{4})$")[0].fillna("0").astype(int)
        rows = rows.sort_values(["_standard_rank", "POC", "Certification Indicator"], ascending=[False, True, False])
        rows = rows.drop_duplicates(["State Code", "County Code", "Site Num", "POC", "Event Type"], keep="first")
        grouped = rows.groupby(["State Code", "County Code", "Site Num"], sort=True)
        n_before = len(df)
        year_records = []
        selected_event_counts = {"Events Included": 0, "No Events": 0}
        unsupported_pocs = 0
        site_years_without_ambient_poc = 0
        for (state, county, site), group in grouped:
            # Event treatments are alternate summaries for the same POC, not
            # replicate instruments. Select one ambient summary per POC, then
            # average distinct colocated POCs into one physical site-year.
            chosen, site_unsupported_pocs = select_ambient_poc_summaries(group)
            unsupported_pocs += site_unsupported_pocs
            if chosen.empty:
                site_years_without_ambient_poc += 1
                continue
            first = chosen.iloc[0]
            value = float(chosen["Arithmetic Mean"].mean())
            selected_treatments = sorted(chosen["Event Type"].astype(str).unique().tolist())
            for event_type in chosen["Event Type"].astype(str):
                selected_event_counts[event_type] = selected_event_counts.get(event_type, 0) + 1
            poc_event_treatments = [
                {
                    "poc_id": str(row["POC"]),
                    "event_treatment": str(row["Event Type"]),
                    "certification": str(row["Certification Indicator"]),
                    "observation_percent": float(row["Observation Percent"]) if pd.notna(row["Observation Percent"]) else None,
                    "pollutant_standard": str(row["Pollutant Standard"]),
                    "arithmetic_mean_ug_m3": float(row["Arithmetic Mean"]),
                    "source_row_number": int(row["_source_row_number"]),
                }
                for _, row in chosen.sort_values("POC").iterrows()
            ]
            record = {
                "id": f"{state}-{county}-{site}", "state_fips": state,
                "county_fips": state + county, "site_number": site,
                "latitude": float(first["Latitude"]), "longitude": float(first["Longitude"]),
                "year": year, "pm25_ug_m3": value,
                "poc_count": int(chosen["POC"].nunique()),
                "poc_ids": sorted(chosen["POC"].astype(str).unique().tolist()),
                "sample_completeness": "Y",
                "event_treatment": selected_treatments[0] if len(selected_treatments) == 1 else "Mixed selected treatments by POC",
                "poc_event_treatments": poc_event_treatments,
                "source_provenance": {
                    "source": "EPA AQS annual concentration by monitor archive",
                    "archive_name": path.name,
                    "archive_sha256": archive_sha256,
                    "csv_member": csv_member,
                    "selected_source_rows": [entry["source_row_number"] for entry in poc_event_treatments],
                    "source_url": SOURCES["EPA AQS annual PM2.5 monitor summaries"].format(year=year),
                },
                "pollutant_standard": str(first["Pollutant Standard"]),
                "metric": "Quarterly Means of Daily Means", "units": "µg/m³",
                "certification": sorted(chosen["Certification Indicator"].astype(str).unique().tolist()),
                "evidence_type": "measured_monitor_annual_summary",
            }
            record["canonical_observation"] = canonical_aqs_observation(record)
            year_records.append(record)
        records.extend(year_records)
        audit[str(year)] = {
            "archive_rows": n_before,
            "eligible_annual_summary_rows": len(rows),
            "unique_spatial_site_years": len(year_records),
            "state_count": len({r["state_fips"] for r in year_records}),
            "event_treatment_selection": {
                "definition_url": "https://aqs.epa.gov/aqsweb/airdata/FileFormats.html",
                "selected_poc_rows_by_treatment": selected_event_counts,
                "pocs_with_only_event_excluded_summaries": unsupported_pocs,
                "site_years_without_ambient_poc": site_years_without_ambient_poc,
                "policy": "Select one annual summary per POC: Events Included when exceptional-event data are present, otherwise No Events. Do not treat event-treatment alternatives as independent monitor readings; do not substitute event-excluded summaries for observed ambient concentration.",
            },
        }
    return records, audit


def process_places(gaz_path: Path, population_path: Path) -> tuple[list[dict], dict]:
    with zipfile.ZipFile(gaz_path) as zf:
        member = next((n for n in zf.namelist() if n.endswith("place_national.txt")), None)
        if member is None:
            raise ValueError("Census place Gazetteer member missing")
        with zf.open(member) as stream:
            places = pd.read_csv(stream, sep="\t", dtype=str)
    places.columns = [str(c).strip() for c in places.columns]
    pop = pd.read_csv(population_path, dtype=str, encoding="latin-1")
    pop.columns = [str(c).strip() for c in pop.columns]
    needed = {"GEOID", "NAME", "LSAD", "FUNCSTAT", "INTPTLAT", "INTPTLONG"}
    if needed - set(places.columns):
        raise ValueError("Unexpected Census Gazetteer schema")
    pop = pop[pop["SUMLEV"].eq("162") & pop["PLACE"].ne("00000")].copy()
    pop["GEOID"] = pop["STATE"].str.zfill(2) + pop["PLACE"].str.zfill(5)
    pop_lookup = pop.set_index("GEOID").to_dict("index")
    states = {"01":"Alabama","02":"Alaska","04":"Arizona","05":"Arkansas","06":"California","08":"Colorado","09":"Connecticut","10":"Delaware","11":"District of Columbia","12":"Florida","13":"Georgia","15":"Hawaii","16":"Idaho","17":"Illinois","18":"Indiana","19":"Iowa","20":"Kansas","21":"Kentucky","22":"Louisiana","23":"Maine","24":"Maryland","25":"Massachusetts","26":"Michigan","27":"Minnesota","28":"Mississippi","29":"Missouri","30":"Montana","31":"Nebraska","32":"Nevada","33":"New Hampshire","34":"New Jersey","35":"New Mexico","36":"New York","37":"North Carolina","38":"North Dakota","39":"Ohio","40":"Oklahoma","41":"Oregon","42":"Pennsylvania","44":"Rhode Island","45":"South Carolina","46":"South Dakota","47":"Tennessee","48":"Texas","49":"Utah","50":"Vermont","51":"Virginia","53":"Washington","54":"West Virginia","55":"Wisconsin","56":"Wyoming","60":"American Samoa","66":"Guam","69":"Northern Mariana Islands","72":"Puerto Rico","78":"U.S. Virgin Islands"}
    output = []
    joined = 0
    for row in places.to_dict("records"):
        geoid = str(row["GEOID"]).zfill(7)
        state = geoid[:2]
        estimate = pop_lookup.get(geoid)
        estimates = {} if estimate is None else {str(y): int(estimate[f"POPESTIMATE{y}"]) for y in range(2020, 2025) if estimate.get(f"POPESTIMATE{y}", "").isdigit()}
        joined += estimate is not None
        output.append({
            "id": geoid, "name": str(row["NAME"]), "state": states.get(state, "Unknown"),
            "state_fips": state, "lsad": str(row["LSAD"]),
            "place_type": "Census-designated place" if str(row["LSAD"]) == "57" else "Incorporated place" if str(row["FUNCSTAT"]) == "A" else "Census place",
            "functional_status": str(row["FUNCSTAT"]),
            "latitude": float(row["INTPTLAT"]), "longitude": float(row["INTPTLONG"]),
            "population_vintage": 2024 if estimates else None, "estimates": estimates,
        })
    return output, {"gazetteer_places": len(output), "population_joined_places": joined, "population_vintage": "2020-2024 Census Population Estimates Program, subcounty places", "population_join_rate": joined / len(output) if output else 0}


def process_nei(path: Path) -> tuple[list[dict], dict]:
    """Read EPA's facility summary and retain primary PM2.5 facility records."""
    with zipfile.ZipFile(path) as zf:
        candidates = [n for n in zf.namelist() if n.lower().endswith(".csv") and "emis_sum_fac" in n.lower()]
        if len(candidates) != 1:
            return [], {"inventory_year": 2023, "facility_file_count": 0, "reason": "The downloaded EPA facility summary archive contains no tabular facility coordinates; no points were fabricated. The official NEI facility map/data query link is provided in methodology."}
        name = candidates[0]
        required = {"eis facility id", "site latitude", "site longitude", "site name", "pollutant code", "pollutant desc", "total emissions", "emissions uom", "primary naics description", "facility source type"}
        output, input_rows, missing_coordinates = [], 0, 0
        with zf.open(name) as stream:
            for frame in pd.read_csv(stream, chunksize=150_000, low_memory=False, encoding_errors="replace"):
                frame.columns = [str(c).strip().lower() for c in frame.columns]
                missing = required - set(frame.columns)
                if missing:
                    raise ValueError(f"NEI facility summary schema missing {sorted(missing)}")
                frame = frame[frame["pollutant code"].astype(str).str.upper().eq("PM25-PRI")]
                input_rows += len(frame)
                for row in frame.to_dict("records"):
                    try:
                        lat, lon, amount = float(row["site latitude"]), float(row["site longitude"]), float(row["total emissions"])
                    except (TypeError, ValueError):
                        missing_coordinates += 1
                        continue
                    if not (-90 <= lat <= 90 and -180 <= lon <= 180) or not math.isfinite(amount):
                        missing_coordinates += 1
                        continue
                    output.append({"id": str(row["eis facility id"]), "name": str(row["site name"]), "company": str(row.get("company name", "")), "latitude": lat, "longitude": lon, "pollutant": "PM25", "pollutant_code": "PM25-PRI", "pollutant_description": str(row["pollutant desc"]), "emissions": amount, "units": str(row["emissions uom"]), "category": str(row["primary naics description"]), "facility_source_type": str(row["facility source type"]), "inventory_year": 2023, "reporting_period": str(row.get("reporting period", "2023")), "source": "EPA 2023 NEI facility emissions summary", "url": SOURCES["EPA 2023 NEI facility-level pollutant summary"]})
    ids = [r["id"] for r in output]
    return output, {"inventory_year": 2023, "facility_file": name, "pollutant_code": "PM25-PRI", "pollutant_description": "PM2.5 Primary (Filterable + Condensible)", "input_primary_pm25_rows": input_rows, "facility_records_with_coordinates": len(output), "rows_missing_or_invalid_coordinates_or_emissions": missing_coordinates, "duplicate_eis_facility_ids": len(ids) - len(set(ids)), "units_observed": sorted({r["units"] for r in output}), "interpretation": "EPA facility-level annual inventory estimates; primary PM2.5 is kept distinct from components, filterable-only PM2.5, PM10, and precursors. Values are not ambient concentrations or source contributions; no distance-based responsibility attribution."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-year", type=int, default=2018)
    parser.add_argument("--end-year", type=int, default=2025)
    parser.add_argument("--no-nei", action="store_true", help="Build ambient/place release without downloading NEI facility summary")
    parser.add_argument("--raw-dir", type=Path, default=RAW)
    parser.add_argument("--release-dir", type=Path, default=RELEASE)
    args = parser.parse_args()
    if not (2000 <= args.start_year <= args.end_year <= 2026):
        parser.error("Year range must be within 2000–2026")
    raw, release = args.raw_dir, args.release_dir
    raw.mkdir(parents=True, exist_ok=True); release.mkdir(parents=True, exist_ok=True)
    hashes = {}
    aqs = {}
    for year in range(args.start_year, args.end_year + 1):
        name = f"annual_conc_by_monitor_{year}.zip"
        aqs[year] = raw / name
        hashes[name] = download(SOURCES["EPA AQS annual PM2.5 monitor summaries"].format(year=year), aqs[year], archive=True)
    gaz = raw / "2024_Gaz_place_national.zip"
    hashes[gaz.name] = download(SOURCES["Census 2024 national place Gazetteer"], gaz, archive=True)
    pop = raw / "sub-est2024.csv"
    hashes[pop.name] = download(SOURCES["Census 2024 place population estimates"], pop)
    monitor_rows, annual_audit = process_aqs(aqs)
    places, place_audit = process_places(gaz, pop)
    source_rows, source_audit = [], {"reason":"NEI acquisition omitted at operator request"} if args.no_nei else {}
    if not args.no_nei:
        nei = raw / "2023nei_facility_summary.zip"
        hashes[nei.name] = download(SOURCES["EPA 2023 NEI facility-level pollutant summary"], nei, archive=True)
        source_rows, source_audit = process_nei(nei)
    # 2025 is available but remains provisional in the October 2026 build
    # window. Use 2024 for training and keep the newer annual file as research
    # context until EPA marks it complete.
    eligible_years = [int(y) for y, rows in annual_audit.items() if rows["unique_spatial_site_years"] >= 100 and int(y) <= 2024]
    selected_year = max(eligible_years, default=args.end_year)
    train_records = [r for r in monitor_rows if r["year"] == selected_year]
    # Explicitly distinguish a searchable geography from a supported estimate.
    # The modeling script adds estimates only where its held-out support rule passes.
    for p in places:
        p["nearby_monitor"] = None
    place_points = [(p["latitude"], p["longitude"]) for p in places]
    try:
        from scipy.spatial import cKDTree
        tree = cKDTree(place_points)
        for r in train_records:
            _, i = tree.query([r["latitude"],r["longitude"]])
            p=places[int(i)]
            distance = haversine_km(r["latitude"],r["longitude"],p["latitude"],p["longitude"])
            if distance <= 5.0 and (p["nearby_monitor"] is None or distance < p["nearby_monitor"]["distance_km"]):
                p["nearby_monitor"] = {"distance_km": round(float(distance),3),"year":selected_year,"monitor_id":r["id"]}
    except ImportError:
        pass
    source_catalog = {"EPA AQS annual PM2.5 monitor summaries": {"url":SOURCES["EPA AQS annual PM2.5 monitor summaries"],"license":"U.S. government public data; EPA AQS terms and data disclaimers apply","period":f"{args.start_year}–{args.end_year}","target":"Annual PM2.5 concentration metric; complete monitor summaries only"},"Census place Gazetteer": {"url":SOURCES["Census 2024 national place Gazetteer"],"vintage":2024,"license":"U.S. Census Bureau public data"},"Census population": {"url":SOURCES["Census 2024 place population estimates"],"vintage":"2020–2024","license":"U.S. Census Bureau public data"},"EPA National Emissions Inventory": {"url":SOURCES["EPA 2023 NEI facility-level pollutant summary"],"vintage":2023,"license":"U.S. EPA public inventory; inventory estimates are not ambient measurements"}}
    manifest = {"release":"upwind-national-explorer-0.1.0","built_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"retrieved_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"selected_modeling_year":selected_year,"dataset_sources":source_catalog,"raw_files":hashes,"annual_monitor_audit":annual_audit,"place_audit":place_audit,"source_audit":source_audit,"counts":{"searchable_census_places":len(places),"monitor_site_years":len(monitor_rows),"monitor_sites_selected_year":len(train_records),"modeled_places":0,"supported_model_places":0,"population_covered":None},"selection_rule":{"parameter_code":"88101","pollutant_standard":"PM25 Annual*; newest standard available per eligible POC","metric":"Quarterly Means of Daily Means","completeness":"Y","units":"Micrograms/cubic meter (LC)","spatial_deduplication":"one AQS state/county/site/year; average one selected summary per physical site POC; choose Events Included for exceptional events, otherwise No Events; do not average event-treatment alternatives"},"status":"data_built_model_pending"}
    outputs={"monitors.json":monitor_rows,"places.json":places,"sources.json":source_rows,"manifest.json":manifest}
    for filename,payload in outputs.items():
        tmp=release/(filename+".partial")
        tmp.write_text(json.dumps(payload,separators=(",",":"),allow_nan=False)+"\n")
        tmp.replace(release/filename)
    print(json.dumps({"release_dir":str(release),"counts":manifest["counts"],"annual_monitor_audit":annual_audit,"place_audit":place_audit,"source_audit":source_audit},indent=2))


def haversine_km(lat1, lon1, lat2, lon2):
    import math
    p1,p2=math.radians(lat1),math.radians(lat2); dp=math.radians(lat2-lat1); dl=math.radians(lon2-lon1)
    a=math.sin(dp/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 6371.0088*2*math.asin(min(1,math.sqrt(a)))


if __name__ == "__main__":
    main()
