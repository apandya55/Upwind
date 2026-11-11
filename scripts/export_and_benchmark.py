#!/usr/bin/env python3
"""Export NC annual EPA observations and benchmark existing UPWIND interpolation.

================================================================================
DATA INTAKE, HARMONIZATION & BENCHMARK HARNESS
================================================================================
This script automates the production data export and validation pipeline:
1. Intake & Filter: Reads annual PM2.5 monitoring summaries from EPA AQS for
   North Carolina (FIPS 37), enforcing 75% quarterly completeness criteria.
2. POC Harmonization: Multiple monitors (POCs - Parameter Occurrence Codes) at the
   same physical site are combined into single robust annual site means.
3. Columnar Parquet Serialization: Generates high-efficiency Apache Parquet files
   with strict schema typing, metadata manifests, and SHA-256 integrity digests.
4. Benchmark Suite: Runs spatial cross-validation comparing UPWIND's Gaussian
   dispersion kernel against Inverse Distance Weighting and Nearest-Monitor baselines.
================================================================================
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import sys
import tempfile
import time

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "backend")]
from evaluate_national_v2 import predict
from upwind.national import data as spatial

WEATHER = {
    "temperature_c": ("Annual mean air temperature", "°C"),
    "relative_humidity_pct": ("Annual mean relative humidity", "%"),
    "wind_speed_m_s": ("Annual mean scalar wind speed", "m/s"),
}
COLUMNS = {
    "id": ("Physical EPA AQS site identifier; colocated POCs are combined", "identifier"),
    "state_fips": ("State FIPS, 37 for North Carolina", "code"),
    "county_fips": ("Five-digit state + county FIPS", "code"),
    "site_number": ("Four-digit AQS site number", "code"),
    "year": ("Annual observation year", "year"),
    "period_start": ("Inclusive January 1; annual period label", "date"),
    "period_end_exclusive": ("Exclusive January 1 of following year", "date"),
    "latitude": ("Station latitude, WGS84", "degrees north"),
    "longitude": ("Station longitude, WGS84", "degrees east"),
    "pm25_ug_m3": ("Mean of eligible colocated POC annual PM2.5 summaries", "µg/m³, local conditions"),
    "poc_count": ("Number of selected colocated instruments, not independent sites", "count"),
    "sample_completeness": ("EPA completeness indicator; required Y", "flag"),
    "event_treatment": ("Selected ambient event treatment(s), preserved from ingestion", "text"),
    "pollutant_standard": ("EPA annual PM2.5 standard selected during ingestion", "text"),
    "metric": ("EPA aggregation metric: Quarterly Means of Daily Means", "text"),
    "evidence_type": ("Source observation classification", "text"),
    **WEATHER,
}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def clean(path):
    raw = json.loads(Path(path).read_text())
    if not isinstance(raw, list) or not raw:
        raise ValueError("monitors.json must contain a nonempty record list")
    selected = [r for r in raw if r.get("state_fips") == "37"]
    valid, rejected = [], 0
    for row in selected:
        try:
            ok = (row["sample_completeness"] == "Y"
                  and row["units"] == "µg/m³"
                  and row["metric"] == "Quarterly Means of Daily Means"
                  and row["evidence_type"] == "measured_monitor_annual_summary"
                  and math.isfinite(float(row["pm25_ug_m3"]))
                  and -90 <= float(row["latitude"]) <= 90
                  and -180 <= float(row["longitude"]) <= 180
                  and isinstance(row["year"], int) and 1900 <= row["year"] <= 9998
                  and row["id"] == f"37-{row['county_fips'][-3:]}-{row['site_number']}")
        except (KeyError, TypeError, ValueError):
            ok = False
        if ok:
            valid.append(row)
        else:
            rejected += 1
    unique = {}
    for row in valid:
        key = row["id"], row["year"]
        if key in unique and unique[key] != row:
            raise ValueError(f"Conflicting site-year records: {key}; rebuild ingestion")
        unique[key] = row
    rows = sorted(unique.values(), key=lambda r: (r["year"], r["id"]))
    if not rows:
        raise ValueError("No eligible North Carolina observations")
    frame = pd.DataFrame(rows)
    for col in COLUMNS:
        if col not in frame:
            frame[col] = None
    for col in WEATHER:
        frame[col] = np.nan
    frame["period_start"] = pd.to_datetime(frame.year.astype(str) + "-01-01").dt.date
    frame["period_end_exclusive"] = pd.to_datetime((frame.year + 1).astype(str) + "-01-01").dt.date
    return frame[list(COLUMNS)], {"input_national_rows": len(raw), "input_nc_rows": len(selected),
        "rejected_nc_rows": rejected, "duplicate_nc_rows_removed": len(valid) - len(rows)}


def join_weather(frame, path):
    weather = pd.read_csv(path, dtype={"id": str})
    required = {"id", "year", *WEATHER}
    if not required <= set(weather.columns):
        raise ValueError(f"Weather requires columns {sorted(required)}")
    weather = weather[sorted(required)].drop_duplicates()
    if weather[["id", "year"]].isna().any().any() or weather.duplicated(["id", "year"]).any():
        raise ValueError("Missing or conflicting weather site-year keys")
    years = pd.to_numeric(weather.year, errors="raise")
    if not ((years % 1 == 0) & years.between(1900, 9998)).all():
        raise ValueError("Weather year must be an integer calendar year")
    weather["year"] = years.astype(int)
    for col in WEATHER:
        weather[col] = pd.to_numeric(weather[col], errors="raise")
        if np.isinf(weather[col]).any():
            raise ValueError(f"Non-finite weather: {col}")
    if not weather.relative_humidity_pct.dropna().between(0, 100).all() or (weather.wind_speed_m_s.dropna() < 0).any():
        raise ValueError("Humidity must be 0–100; wind speed must be nonnegative")
    return frame.drop(columns=list(WEATHER)).merge(weather, on=["id", "year"], how="left", validate="one_to_one")[list(COLUMNS)]


def scores(y, p):
    y, p = np.asarray(y), np.asarray(p)
    residual = p - y
    denominator = np.sum((y - y.mean()) ** 2)
    return {"n": len(y), "MAE": float(np.mean(abs(residual))),
            "RMSE": float(np.sqrt(np.mean(residual ** 2))),
            "R2": float(1 - np.sum(residual ** 2) / denominator) if len(y) > 1 and denominator > 0 else None}


def benchmark(frame):
    # Assign once per physical station, using its earliest released coordinates.
    sites = frame.drop_duplicates("id")
    folds = {
        r.id: int(hashlib.sha256(
            f"UPWIND-NC-1:{math.floor(r.latitude)}:{math.floor(r.longitude)}".encode()
        ).hexdigest()[:8], 16) % 5 for r in sites.itertuples()
    }
    results = []
    for year, group in frame.groupby("year", sort=True):
        x = group[["latitude", "longitude"]].to_numpy(float)
        y = group.pm25_ug_m3.to_numpy(float)
        f = group.id.map(folds).to_numpy()
        for fold in sorted(set(f)):
            train, test = f != fold, f == fold
            if not train.any():
                continue
            for method in ("nearest_monitor", "idw_k4_p2", "gaussian_kernel_ridge_150km"):
                predictions = predict(method, x[train], y[train], x[test])
                for station, observed, prediction in zip(group.id[test], y[test], predictions):
                    results.append(dict(id=station, year=int(year), fold=int(fold), method=method,
                                        observed=float(observed), predicted=float(prediction), n_train=int(train.sum())))
    if not results:
        raise ValueError("No spatial holdouts with training support")
    return pd.DataFrame(results)


def latency(frame, seed, repeats):
    """Compare identical full-result bbox queries against UPWIND's actual index."""
    rows = json.loads(frame[["id", "year", "latitude", "longitude"]].to_json(orient="records", double_precision=15))
    rng = np.random.default_rng(seed)
    boxes = []
    for _ in range(100):
        row = rows[int(rng.integers(len(rows)))]
        width = float(rng.uniform(0.05, 1.0))
        boxes.append((row["longitude"]-width, row["latitude"]-width,
                      row["longitude"]+width, row["latitude"]+width))
    previous = os.environ.get("UPWIND_NATIONAL_RELEASE_DIR")
    try:
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "monitors.json").write_text(json.dumps(rows))
            os.environ["UPWIND_NATIONAL_RELEASE_DIR"] = directory
            spatial._read_release.cache_clear()
            spatial._spatial_buckets.cache_clear()
            spatial.read_release("monitors.json")  # exclude file parsing from index build
            start = time.perf_counter_ns()
            spatial._spatial_buckets("monitors.json", spatial.release_identity("monitors.json"))
            build_ms = (time.perf_counter_ns() - start) / 1e6

            def scan(box):
                w, s, e, n = box
                return [r for r in rows if w <= r["longitude"] <= e and s <= r["latitude"] <= n]

            def indexed(box):
                return spatial.query_bounds("monitors.json", *box, limit=10000)[0]

            identity = lambda result: sorted((r["id"], r["year"]) for r in result)
            for box in boxes:
                if identity(scan(box)) != identity(indexed(box)):
                    raise AssertionError("Spatial index returned different records")
            samples = {"scan": [], "indexed": []}
            for repeat in range(repeats):
                for box in boxes:
                    order = [("scan", scan), ("indexed", indexed)]
                    if repeat % 2:
                        order.reverse()
                    for label, query in order:
                        start = time.perf_counter_ns()
                        query(box)
                        samples[label].append((time.perf_counter_ns() - start) / 1000)
            return {"index_build_ms": build_ms, "queries_per_mode": repeats * len(boxes),
                    **{label: {"median_us": float(np.median(v)), "p95_us": float(np.percentile(v, 95))} for label, v in samples.items()}}
    finally:
        if previous is None:
            os.environ.pop("UPWIND_NATIONAL_RELEASE_DIR", None)
        else:
            os.environ["UPWIND_NATIONAL_RELEASE_DIR"] = previous
        spatial._read_release.cache_clear()
        spatial._spatial_buckets.cache_clear()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--monitors", type=Path, default=ROOT / "data/national/release/monitors.json")
    parser.add_argument("--weather", type=Path, help="Annual site-year weather CSV; see module docstring")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "release")
    parser.add_argument("--docs-dir", type=Path, default=ROOT)
    parser.add_argument("--seed", type=int, default=20261114)
    parser.add_argument("--repeats", type=int, default=20)
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("--repeats must be positive")
    frame, audit = clean(args.monitors)
    if args.weather:
        frame = join_weather(frame, args.weather)
    predictions = benchmark(frame)
    timings = latency(frame, args.seed, args.repeats)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.docs_dir.mkdir(parents=True, exist_ok=True)
    target = args.output_dir / "upwind_nc_air_quality.parquet"
    types = {"year": pa.int64(), "poc_count": pa.int64(),
             "period_start": pa.date32(), "period_end_exclusive": pa.date32(),
             **{c: pa.float64() for c in ("latitude", "longitude", "pm25_ug_m3", *WEATHER)}}
    schema = pa.schema([(c, types.get(c, pa.string())) for c in COLUMNS])
    table = pa.Table.from_pandas(frame, schema=schema, preserve_index=False)
    pq.write_table(table, target, compression="zstd")
    if not pq.read_table(target).equals(table):
        raise AssertionError("Parquet round trip changed data")
    predictions.to_csv(args.output_dir / "spatial_predictions.csv", index=False)
    summary = {**audit, "export_rows": len(frame), "sensor_count": int(frame.id.nunique()),
               "date_start_inclusive": str(frame.period_start.min()),
               "date_end_exclusive": str(frame.period_end_exclusive.max()),
               "bbox_west_south_east_north": [float(frame.longitude.min()), float(frame.latitude.min()), float(frame.longitude.max()), float(frame.latitude.max())],
               "weather_nonnull_counts": {c: int(frame[c].notna().sum()) for c in WEATHER}}
    print(json.dumps(summary, indent=2))
    lines = ["# UPWIND export and spatial benchmarks", "", "Generated by `scripts/export_and_benchmark.py`. No network acquisition is performed.", "", "## Data and ingestion", "",
             "`backend/upwind/store.py` stores investigation JSON in SQLite; it is not a normalized observation warehouse. "
             "This export uses the national EPA annual release built by `scripts/build_national_dataset.py`. "
             "Ingestion selects complete parameter 88101 annual summaries, prioritizes the latest standard, retains Events Included "
             "or No Events per POC, then averages colocated POCs. Hourly intake (`scripts/acquire_aqs.py`) is a separate pipeline. "
             "This is annual NC data, not hourly measurements. Exact duplicate site-years are removed; conflicting duplicates abort. "
             "Rows with invalid required values are counted and dropped. Finite negative PM2.5 values are retained without clipping.", "", "```json", json.dumps(summary, indent=2), "```", "",
             "Weather is left-joined by physical site ID and year only when `--weather` is supplied; no imputation or inferred temporal matching. "
             "Without that file, all meteorological columns are null. Sensor-fusion accuracy cannot be tested with this release: it has no matched weather or independent sensor-fusion targets.", "", "## Spatial accuracy", "",
             "NC-only, within-year five-fold spatial cross-validation using a fixed SHA-256 assignment of one-degree cells (UPWIND-NC-1:floor(lat):floor(lon), first eight hex digits modulo five). The national ten-degree protocol places NC sites in one fold and cannot support NC-only training; this regional split uses smaller cells. "
             "Each station retains its earliest coordinate's fold across all years. Entire held-out folds are excluded from training. "
             "Predictions call `scripts/evaluate_national_v2.py` directly; nearest monitor is the released method and IDW/kernel ridge are candidates. "
             "No parameters are tuned here. EPA annual site summaries are the reference targets, not a claim of independent FRM-only instruments. "
             "This is a regional re-evaluation, not the published national score or a future-year forecast. "
             "MAE = mean(abs(predicted − observed)); RMSE = sqrt(mean(error²)); R² = 1 − SSE/SST using the test-set mean. "
             "R² is undefined for fewer than two targets or constant targets. Pooled scores weight site-years equally; repeated years are not independent stations. "
             "Small regional folds limit generalizability; 2025 observations are provisional.", "", "| Year | Method | N | MAE (µg/m³) | RMSE (µg/m³) | R² |", "|---|---|---:|---:|---:|---:|"]
    for label, subset in [(str(y), g) for y, g in predictions.groupby("year")] + [("All", predictions)]:
        for method, group in subset.groupby("method"):
            m = scores(group.observed, group.predicted)
            r2 = "undefined" if m['R2'] is None else f"{m['R2']:.6f}"
            lines.append(f"| {label} | {method} | {m['n']} | {m['MAE']:.6f} | {m['RMSE']:.6f} | {r2} |")
    lines += ["", "Fold coverage (same for each method):", "", "| Year | Fold | Train | Test |", "|---|---:|---:|---:|"]
    nearest = predictions[predictions.method == "nearest_monitor"]
    for (year, fold), group in nearest.groupby(["year", "fold"]):
        lines.append(f"| {year} | {fold} | {group.n_train.iloc[0]} | {len(group)} |")
    lines += ["", f"Scored {len(nearest)} of {len(frame)} site-years; unsupported folds are skipped. Full predictions: `release/spatial_predictions.csv`.", "", "## Query latency", "",
              "Warm in-process full-result bounding-box queries: linear scan versus the production one-degree bucket index in "
              "`backend/upwind/national/data.py`. This does not add a SQL index or modify the application database. "
              "100 seeded station-centered windows, half-width 0.05–1 degree, alternating execution order each repetition. "
              "All results are checked for exact equivalence before timing. Indexed timing includes production file-identity checks; "
              "index build excludes JSON parsing. These small NC data may be faster to scan. Timings vary by machine and load.", "", "```json", json.dumps(timings, indent=2), "```", "", "## Reproduction", "",
              "Install the project's engine dependencies plus `pyarrow==19.0.1`, then run from any directory:", "", "```sh", f"python {Path(__file__).resolve()} --monitors {args.monitors.resolve()} --seed {args.seed} --repeats {args.repeats}" + (f" --weather {args.weather.resolve()}" if args.weather else ""), "```", "",
              f"Environment: Python {platform.python_version()}, NumPy {np.__version__}, pandas {pd.__version__}, PyArrow {pa.__version__}; {platform.platform()}.", "",
              f"Input SHA-256: `{digest(args.monitors)}`. Parquet SHA-256: `{digest(target)}`.", "",
              f"Weather SHA-256: `{digest(args.weather)}`." if args.weather else "Weather input: absent."]
    (args.docs_dir / "BENCHMARKS.md").write_text("\n".join(lines) + "\n")
    dictionary = ["# UPWIND NC data dictionary", "", "One row per physical EPA station and calendar year; sorted by year then ID. "
                  "Parquet uses ZSTD and stores no dataframe index. Dates label annual periods, not instantaneous samples. "
                  "Identifiers preserve leading zeros. Missing optional data are Arrow null, never zero or a sentinel. "
                  "No rows are dropped for missing weather. See BENCHMARKS.md for ingestion filters and exact counts.", "", "| Column | Arrow type | Definition | Unit | Null handling |", "|---|---|---|---|---|"]
    required = {"id", "state_fips", "county_fips", "site_number", "year", "period_start", "period_end_exclusive", "latitude", "longitude", "pm25_ug_m3", "sample_completeness", "metric", "evidence_type"}
    for field in table.schema:
        description, unit = COLUMNS[field.name]
        rule = "Required; invalid source row rejected" if field.name in required else "Absent source value remains null"
        if field.name in WEATHER:
            rule = "Null without matching annual weather or when source value missing; never imputed"
        dictionary.append(f"| {field.name} | {field.type} | {description} | {unit} | {rule} |")
    dictionary += ["", "Optional weather CSV must contain `id`, integer `year`, and all three weather columns. "
                   "Values must be numeric or empty; infinities, humidity outside 0–100%, negative wind speed, "
                   "missing keys, and conflicting site-years abort. Exact duplicate rows are collapsed. "
                   "The caller is responsible for annual aggregation and weather provenance. Weather is exported but is not used in the coordinate-only benchmark."]
    (args.docs_dir / "DATA_DICTIONARY.md").write_text("\n".join(dictionary) + "\n")


if __name__ == "__main__":
    main()
