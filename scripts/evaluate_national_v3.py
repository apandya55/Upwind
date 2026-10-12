#!/usr/bin/env python3
"""National Explorer data audit and PRISM covariate evaluation."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

import numpy as np
import pandas as pd

try:  # Supports both `python scripts/...` and package-style test imports.
    from scripts.build_national_dataset import select_ambient_poc_summaries
except ModuleNotFoundError:  # pragma: no cover - exercised by direct CLI entrypoint
    from build_national_dataset import select_ambient_poc_summaries

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "data/national/release"
RAW = ROOT / "data/national/raw"
DEFAULT_OUT = ROOT / "evaluations/national-v3"
PROTOCOL_ID = "UW-NATIONAL-SPATIAL-2026-04"
PRISM_BASE = "https://ftp.prism.oregonstate.edu/time_series/us/an/4km/tmean/monthly/{year}/prism_tmean_us_25m_{year}.zip"


def fold_for(lat: float, lon: float) -> int:
    """The fixed v2 fold identity, retained for a directly paired audit."""
    cell = f"{int((lat + 90) // 10)}:{int((lon + 180) // 10)}"
    return int(hashlib.sha256(("UW-NATIONAL-2026-02:" + cell).encode()).hexdigest()[:8], 16) % 5


def haversine(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    lat1, lat2 = np.deg2rad(a[:, 0])[:, None], np.deg2rad(b[:, 0])[None, :]
    dlat = lat2 - lat1
    dlon = np.deg2rad(b[:, 1])[None, :] - np.deg2rad(a[:, 1])[:, None]
    q = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 6371.0088 * 2 * np.arcsin(np.minimum(1, np.sqrt(q)))


def metrics(y: np.ndarray, pred: np.ndarray, reference: np.ndarray) -> dict:
    err = np.asarray(pred) - np.asarray(y)
    den = float(np.sum((np.asarray(y) - np.asarray(reference)) ** 2))
    return {
        "n": int(len(y)),
        "mae_ug_m3": float(np.mean(np.abs(err))),
        "rmse_ug_m3": float(np.sqrt(np.mean(err**2))),
        "bias_ug_m3": float(np.mean(err)),
        "r2_vs_training_mean": float(1 - np.sum(err**2) / den) if den else None,
    }


def _predict_gaussian(train_x, train_y, test_x):
    d_train = haversine(train_x, train_x)
    d_test = haversine(test_x, train_x)
    kernel = np.exp(-0.5 * (d_train / 150.0) ** 2)
    centered = train_y - np.mean(train_y)
    beta = np.linalg.solve(kernel + np.eye(len(train_y)), centered)
    return float(np.mean(train_y)) + np.exp(-0.5 * (d_test / 150.0) ** 2) @ beta


def _predict_prism(train_x, train_y, train_z, test_x, test_z):
    """One fixed enhanced candidate, all standardization and fitting train-only."""
    mean = float(np.mean(train_z))
    scale = float(np.std(train_z))
    if not math.isfinite(scale) or scale < 1e-9:
        scale = 1.0
    z_train = (train_z - mean) / scale
    z_test = (test_z - mean) / scale
    design = np.column_stack([np.ones(len(train_y)), z_train])
    coefficients, *_ = np.linalg.lstsq(design, train_y, rcond=None)
    residual = train_y - design @ coefficients
    d_train = haversine(train_x, train_x)
    d_test = haversine(test_x, train_x)
    kernel = np.exp(-0.5 * (d_train / 150.0) ** 2)
    spatial = np.linalg.solve(kernel + np.eye(len(train_y)), residual)
    return np.column_stack([np.ones(len(test_x)), z_test]) @ coefficients + np.exp(-0.5 * (d_test / 150.0) ** 2) @ spatial


def _aqs_eligible(df: pd.DataFrame, year: int) -> pd.DataFrame:
    return df[
        (df["Parameter Code"].astype(str).str.zfill(5) == "88101")
        & df["Pollutant Standard"].astype(str).str.startswith("PM25 Annual")
        & df["Metric Used"].eq("Quarterly Means of Daily Means")
        & df["Units of Measure"].eq("Micrograms/cubic meter (LC)")
        & df["Completeness Indicator"].eq("Y")
        & (df["Year"] == year)
    ].copy()


def audit_aqs_year(path: Path, year: int) -> dict:
    with zipfile.ZipFile(path) as archive:
        names = [n for n in archive.namelist() if n.lower().endswith(".csv")]
        if len(names) != 1:
            raise ValueError(f"Expected one AQS CSV in {path}, found {names}")
        df = pd.read_csv(archive.open(names[0]), low_memory=False)
    eligible = _aqs_eligible(df, year)
    key = ["State Code", "County Code", "Site Num", "POC", "Event Type"]
    physical = ["State Code", "County Code", "Site Num"]
    eligible["site_id"] = (
        eligible["State Code"].astype(str).str.zfill(2)
        + "-" + eligible["County Code"].astype(str).str.zfill(3)
        + "-" + eligible["Site Num"].astype(str).str.zfill(4)
    )
    dup_groups = eligible.groupby(key, dropna=False).size()
    site_group = eligible.groupby("site_id", sort=False)
    pocs = site_group["POC"].nunique()
    events = site_group["Event Type"].nunique()
    # Compare the former site-level event aggregation with the corrected
    # ambient-target rule. AQS documents event-treatment rows as alternatives
    # for one monitor, not independent POCs.
    eligible["_standard_rank"] = eligible["Pollutant Standard"].str.extract(r"(\d{4})$")[0].fillna("0").astype(int)
    eligible = eligible.sort_values(["_standard_rank", "POC", "Certification Indicator"], ascending=[False, True, False])
    deduplicated = eligible.drop_duplicates(key, keep="first")
    legacy_fallback_groups = []
    selected_rows = []
    legacy_site_values = {}
    ambient_site_values = {}
    ambient_treatment_counts: Counter[str] = Counter()
    unsupported_pocs = 0
    sites_without_ambient_poc = 0
    for _, group in deduplicated.groupby("site_id", sort=False):
        no_event = group[group["Event Type"].eq("No Events")]
        legacy_chosen = no_event if len(no_event) else group
        legacy_site_values[str(group["site_id"].iloc[0])] = float(pd.to_numeric(legacy_chosen["Arithmetic Mean"], errors="coerce").mean())
        if not len(no_event):
            legacy_fallback_groups.append(group)
        ambient_chosen, omitted = select_ambient_poc_summaries(group)
        unsupported_pocs += omitted
        if ambient_chosen.empty:
            sites_without_ambient_poc += 1
            continue
        site_id = str(group["site_id"].iloc[0])
        ambient_site_values[site_id] = float(pd.to_numeric(ambient_chosen["Arithmetic Mean"], errors="coerce").mean())
        selected_rows.append(ambient_chosen)
        ambient_treatment_counts.update(ambient_chosen["Event Type"].astype(str).tolist())
    legacy_fallback_multi = [g for g in legacy_fallback_groups if g["Event Type"].nunique() > 1]
    legacy_fallback_value_ranges = [
        float(pd.to_numeric(g["Arithmetic Mean"], errors="coerce").max() - pd.to_numeric(g["Arithmetic Mean"], errors="coerce").min())
        for g in legacy_fallback_multi
    ]
    common_sites = set(legacy_site_values) & set(ambient_site_values)
    site_mean_changes = [ambient_site_values[sid] - legacy_site_values[sid] for sid in common_sites]
    return {
        "archive_rows": int(len(df)),
        "eligible_parameter_rows": int(len(eligible)),
        "unique_physical_site_years": int(eligible[physical].drop_duplicates().shape[0]),
        "duplicate_poc_event_groups": int((dup_groups > 1).sum()),
        "duplicate_poc_event_rows": int(dup_groups[dup_groups > 1].sum() - (dup_groups > 1).sum()),
        "rows_after_newest_standard_poc_event_deduplication": int(len(deduplicated)),
        "event_selection_audit": {
            "legacy_policy": "At site level, use No Events rows if any; otherwise average every event-treatment row.",
            "legacy_sites_with_no_events_summary_preferred": int(len(legacy_site_values) - len(legacy_fallback_groups)),
            "legacy_sites_falling_back_to_event_rows": int(len(legacy_fallback_groups)),
            "legacy_fallback_sites_with_multiple_event_treatments_averaged": int(len(legacy_fallback_multi)),
            "legacy_fallback_multi_event_mean_absolute_within_site_range_ug_m3": float(np.mean(legacy_fallback_value_ranges)) if legacy_fallback_value_ranges else 0.0,
            "legacy_fallback_multi_event_median_absolute_within_site_range_ug_m3": float(np.median(legacy_fallback_value_ranges)) if legacy_fallback_value_ranges else 0.0,
            "ambient_policy": "One summary per physical site POC: Events Included when exceptional-event data are present, otherwise No Events; event-excluded rows are never substituted for an ambient concentration.",
            "ambient_policy_selected_poc_rows": int(sum(len(g) for g in selected_rows)),
            "ambient_policy_event_treatment_counts": dict(sorted(ambient_treatment_counts.items())),
            "pocs_with_only_event_excluded_summaries": unsupported_pocs,
            "site_years_without_ambient_poc": sites_without_ambient_poc,
            "site_years_with_changed_mean_vs_legacy": int(sum(abs(value) > 1e-12 for value in site_mean_changes)),
            "mean_absolute_site_value_change_ug_m3": float(np.mean(np.abs(site_mean_changes))) if site_mean_changes else 0.0,
            "maximum_absolute_site_value_change_ug_m3": float(np.max(np.abs(site_mean_changes))) if site_mean_changes else 0.0,
            "event_type_definition_url": "https://aqs.epa.gov/aqsweb/airdata/FileFormats.html",
        },
        "max_pocs_per_site": int(pocs.max()) if len(pocs) else 0,
        "sites_with_multiple_pocs": int((pocs > 1).sum()),
        "sites_with_multiple_event_types": int((events > 1).sum()),
        "event_type_counts": {str(k): int(v) for k, v in eligible["Event Type"].value_counts().items()},
        "pollutant_standard_counts": {str(k): int(v) for k, v in eligible["Pollutant Standard"].value_counts().items()},
        "units": sorted(str(x) for x in eligible["Units of Measure"].dropna().unique()),
        "metric": sorted(str(x) for x in eligible["Metric Used"].dropna().unique()),
        "completeness_indicator": sorted(str(x) for x in eligible["Completeness Indicator"].dropna().unique()),
        "observation_percent_min": float(pd.to_numeric(eligible["Observation Percent"], errors="coerce").min()),
        "observation_percent_median": float(pd.to_numeric(eligible["Observation Percent"], errors="coerce").median()),
        "observation_percent_max": float(pd.to_numeric(eligible["Observation Percent"], errors="coerce").max()),
    }


def sample_prism(year: int, points: np.ndarray, raw_dir: Path) -> tuple[np.ndarray, dict]:
    """Read the official annual CONUS grid and sample its containing pixels."""
    try:
        import rasterio
    except ImportError as exc:
        raise RuntimeError("rasterio is required to sample the verified PRISM predictor") from exc
    archive_path = raw_dir / "prism" / f"prism_tmean_us_25m_{year}.zip"
    if not archive_path.exists():
        raise FileNotFoundError(archive_path)
    with zipfile.ZipFile(archive_path) as archive:
        tif_name = next((n for n in archive.namelist() if n.lower().endswith(".tif")), None)
        info_name = next((n for n in archive.namelist() if n.lower().endswith(".info.txt")), None)
        if not tif_name:
            raise ValueError(f"PRISM archive {archive_path} contains no GeoTIFF")
        with archive.open(tif_name) as stream, rasterio.MemoryFile(stream.read()) as memory:
            with memory.open() as ds:
                from pyproj import Transformer
                transformer = Transformer.from_crs("EPSG:4326", ds.crs, always_xy=True)
                coords = [transformer.transform(float(lon), float(lat)) for lat, lon in points]
                values = np.asarray([v[0] for v in ds.sample(coords)], dtype=float)
                values[~np.isfinite(values) | (values == ds.nodata)] = np.nan
                metadata = {"crs": str(ds.crs), "width": ds.width, "height": ds.height,
                            "bounds": [float(x) for x in ds.bounds], "nodata": ds.nodata,
                            "transform": [float(x) for x in ds.transform[:6]],
                            "tif_member": tif_name,
                            "info": archive.read(info_name).decode("utf-8", "replace") if info_name else ""}
    return values, metadata


def _matched_predictions(rows: list[dict], year: int, method: str):
    data = [r for r in rows if r["year"] == year and math.isfinite(r["prism_tmean_c"])]
    coords = np.asarray([[r["latitude"], r["longitude"]] for r in data], dtype=float)
    y = np.asarray([r["pm25_ug_m3"] for r in data], dtype=float)
    z = np.asarray([r["prism_tmean_c"] for r in data], dtype=float)
    folds = np.asarray([r["fold"] for r in data], dtype=int)
    predictions = np.full(len(data), np.nan)
    distances = np.full(len(data), np.nan)
    references = np.full(len(data), np.nan)
    fold_reports = {}
    for fold in range(5):
        test, train = folds == fold, folds != fold
        if not test.any() or not train.any():
            continue
        d = haversine(coords[test], coords[train])
        distances[test] = d.min(axis=1)
        references[test] = y[train].mean()
        if method == "nearest_monitor":
            predictions[test] = y[train][np.argmin(d, axis=1)]
        elif method == "gaussian_kernel_ridge_150km":
            predictions[test] = _predict_gaussian(coords[train], y[train], coords[test])
        elif method == "gaussian_kernel_ridge_150km_plus_prism_tmean":
            predictions[test] = _predict_prism(coords[train], y[train], z[train], coords[test], z[test])
        else:
            raise ValueError(method)
        fold_reports[str(fold)] = {"n_train": int(train.sum()), "n_test": int(test.sum()),
                                  "metrics": metrics(y[test], predictions[test], np.full(int(test.sum()), y[train].mean()))}
    pooled = metrics(y, predictions, np.asarray([y[folds != f].mean() for f in folds]))
    return pooled, fold_reports, distances, y, predictions, references


def run(raw_dir: Path = RAW, release_dir: Path = RELEASE, out_dir: Path = DEFAULT_OUT) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = json.loads((release_dir / "monitors.json").read_text())
    coordinates: dict[str, tuple[float, float]] = {}
    coordinate_history: defaultdict[str, set] = defaultdict(set)
    for row in rows:
        coordinates.setdefault(row["id"], (row["latitude"], row["longitude"]))
        coordinate_history[row["id"]].add((row["latitude"], row["longitude"]))
    site_folds = {site: fold_for(*xy) for site, xy in coordinates.items()}
    for row in rows:
        row["fold"] = site_folds[row["id"]]
    aqs_audit = {}
    for year in (2024, 2025):
        archive = raw_dir / f"annual_conc_by_monitor_{year}.zip"
        aqs_audit[str(year)] = audit_aqs_year(archive, year)
    predictor = {}
    for year in (2024, 2025):
        year_rows = [r for r in rows if r["year"] == year]
        points = np.asarray([[r["latitude"], r["longitude"]] for r in year_rows], dtype=float)
        values, metadata = sample_prism(year, points, raw_dir)
        for row, value in zip(year_rows, values):
            row["prism_tmean_c"] = float(value) if math.isfinite(value) else float("nan")
        predictor[str(year)] = {"n_rows": len(year_rows), "n_finite": int(np.isfinite(values).sum()),
                                "n_missing": int(np.isnan(values).sum()), **metadata}
    methods = ["nearest_monitor", "gaussian_kernel_ridge_150km", "gaussian_kernel_ridge_150km_plus_prism_tmean"]
    deployed_band = float(json.loads((release_dir / "model.json").read_text())["calibration_abs_residual_90pct_ug_m3"])
    evaluation = {}
    all_uncertainty = {}
    for year in (2024, 2025):
        evaluation[str(year)] = {}
        for method in methods:
            pooled, folds, distances, y, pred, references = _matched_predictions(rows, year, method)
            evaluation[str(year)][method] = {"pooled_out_of_fold": pooled, "folds": folds,
                                              "distance_strata": _distance_metrics(y, pred, distances, references)}
            # The old fixed band is retained as a direct comparison. Also
            # report coverage of the re-estimated band actually used by this
            # corrected-data release.
            band = 4.059
            valid = np.isfinite(pred)
            all_uncertainty.setdefault(str(year), {})[method] = {
                "nominal_level": 0.90,
                "legacy_v2_band": {
                    "source": "pre-correction v2 nearest-monitor geographic OOF residual quantile",
                    "band_ug_m3": band,
                    "coverage": float(np.mean(np.abs(pred[valid] - y[valid]) <= band)),
                    "width_ug_m3": 2 * band,
                },
                "corrected_release_deployed_band": {
                    "source": "corrected-data v3 nearest-monitor geographic OOF residual quantile",
                    "band_ug_m3": deployed_band,
                    "coverage": float(np.mean(np.abs(pred[valid] - y[valid]) <= deployed_band)),
                    "width_ug_m3": 2 * deployed_band,
                },
                "n": int(valid.sum()),
            }
    report = {
        "protocol": PROTOCOL_ID,
        "status": "development_only_previously_inspected_target_vintages",
        "generated_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "input_hashes": {"monitors.json": hashlib.sha256((release_dir / "monitors.json").read_bytes()).hexdigest(),
                         "aqs_2024": hashlib.sha256((raw_dir / "annual_conc_by_monitor_2024.zip").read_bytes()).hexdigest(),
                         "aqs_2025": hashlib.sha256((raw_dir / "annual_conc_by_monitor_2025.zip").read_bytes()).hexdigest(),
                         "prism_2024": hashlib.sha256((raw_dir / "prism/prism_tmean_us_25m_2024.zip").read_bytes()).hexdigest(),
                         "prism_2025": hashlib.sha256((raw_dir / "prism/prism_tmean_us_25m_2025.zip").read_bytes()).hexdigest()},
        "site_identity_audit": {
            "unique_physical_sites_all_years": len(coordinates),
            "site_year_rows": len(rows),
            "site_ids_with_coordinate_changes": sum(len(v) > 1 for v in coordinate_history.values()),
            "folds_assigned_once_per_site_id": True,
            "fold_definition": "v2 fixed SHA-256 10-degree coordinate cell; all rows for a physical AQS site inherit its fold",
        },
        "aqs_annual_audit": aqs_audit,
        "annual_completeness_comparison": {
            "unique_eligible_site_years": {year: aqs_audit[year]["unique_physical_site_years"] for year in ("2024", "2025")},
            "eligible_parameter_rows": {year: aqs_audit[year]["eligible_parameter_rows"] for year in ("2024", "2025")},
            "site_count_change_2025_minus_2024": aqs_audit["2025"]["unique_physical_site_years"] - aqs_audit["2024"]["unique_physical_site_years"],
            "interpretation": "2025 provisional archive currently contains 13 more complete site summaries than 2024, despite 128 fewer eligible standard/POC/event rows; it is a different site-year sample and not an independent prospective validation set.",
        },
        "predictor_audit": predictor,
        "corrected_release_deployed_interval": {
            "method": "symmetric empirical nearest-monitor spatial out-of-fold absolute residual quantile",
            "nominal_level": 0.90,
            "half_width_ug_m3": deployed_band,
            "width_ug_m3": 2 * deployed_band,
            "interpretation": "Descriptive site-level OOF error band; it does not guarantee place-level or local coverage.",
        },
        "evaluation": evaluation,
        "uncertainty": all_uncertainty,
        "selection": {"deployed_model_unchanged": True,
                       "selected_model": "upwind-nearest-monitor-annual-pm25-0.2.0",
                       "rule": "The v2 Gaussian candidate must beat nearest monitor in at least four of five folds in both years; v3 does not alter that rule.",
                       "fold_wins_vs_nearest": {year: {
                           method: sum(
                               evaluation[year][method]["folds"][fold]["metrics"]["mae_ug_m3"]
                               < evaluation[year]["nearest_monitor"]["folds"][fold]["metrics"]["mae_ug_m3"]
                               for fold in evaluation[year][method]["folds"]
                           )
                           for method in methods if method != "nearest_monitor"
                       } for year in evaluation},
                       "environmental_candidate_status": "experimental_comparison"},
        "predictor_provenance": {"family": "PRISM AN M3 annual mean temperature",
                                 "source": "PRISM Group, Oregon State University",
                                 "url": "https://prism.oregonstate.edu/",
                                 "ftp_pattern": PRISM_BASE,
                                 "downloaded_archives": {year: {
                                     "file": f"prism_tmean_us_25m_{year}.zip",
                                     "bytes": int((raw_dir / "prism" / f"prism_tmean_us_25m_{year}.zip").stat().st_size),
                                     "sha256": hashlib.sha256((raw_dir / "prism" / f"prism_tmean_us_25m_{year}.zip").read_bytes()).hexdigest(),
                                 } for year in (2024, 2025)},
                                 "access_date": "2026-10-20",
                                 "terms": "https://prism.oregonstate.edu/terms",
                                 "license_summary": "PRISM Terms of Use state all gridded, polygon, tabular, and graphical data may be freely reproduced and distributed; references must state PRISM Group, URL, and access date.",
                                 "units": "degrees Celsius",
                                 "resolution": "4 km / 2.5 arc-minute CONUS grid",
                                 "temporal_caveat": "Annual grids are retrospective and published after the target year; no real-time forecast or causal feature is claimed."},
        "limitations": [
            "Spatial cross-validation folds evaluate generalization across regional monitor clusters.",
            "PRISM is a retrospective environmental covariate. Its annual target-year grid cannot support an operational beginning-of-year prediction claim.",
            "AQS rows are annual monitor summaries, not independent daily observations; event-treatment alternatives are reduced to one ambient summary per POC and the selected treatment, certification, completeness, and POC are retained in the source release.",
            "The environmental candidate is a fixed one-feature linear mean plus fixed Gaussian residual; no broad parameter search was performed.",
            "The former v0.2 builder selected No Events rows at site level, or averaged every event treatment when none existed. AQS identifies these as alternative event-adjusted summaries, not independent instruments. The corrected v0.3 build selects Events Included once per POC where exceptional-event data exist and No Events otherwise; it never substitutes event-excluded values for the ambient target. See the event_selection_audit for before/after row and value differences.",
            "Monitor-site cross-validation does not establish accuracy at Census place points or local exposure."
        ]
    }
    target = out_dir / "report.json"
    target.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
    (out_dir / "protocol.json").write_text((ROOT / "evaluations/national-v3/protocol.json").read_text())
    return report


def _distance_metrics(y, pred, distances, references):
    strata = [(0, 50, "<=50km"), (50, 100, "50-100km"), (100, 200, "100-200km"), (200, float("inf"), ">200km")]
    output = {}
    for low, high, label in strata:
        mask = np.isfinite(pred) & (distances > low) & (distances <= high)
        if mask.any():
            output[label] = {"distance_min_km": low, "distance_max_km": None if not math.isfinite(high) else high,
                             **metrics(y[mask], pred[mask], references[mask])}
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=RAW)
    parser.add_argument("--release-dir", type=Path, default=RELEASE)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    report = run(args.raw_dir, args.release_dir, args.out_dir)
    print(json.dumps({"protocol": report["protocol"], "evaluation": {y: {m: x["pooled_out_of_fold"] for m, x in v.items()} for y, v in report["evaluation"].items()}, "uncertainty": report["uncertainty"]}, indent=2))


if __name__ == "__main__":
    main()
