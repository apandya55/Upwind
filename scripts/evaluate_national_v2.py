#!/usr/bin/env python3
"""Spatial cross-validation comparison for National Explorer candidate models."""
from __future__ import annotations

import hashlib
import json
import shutil
import argparse
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "data/national/release"


def haversine(a, b):
    lat1, lat2 = np.deg2rad(a[:, 0])[:, None], np.deg2rad(b[:, 0])[None, :]
    dlat = lat2 - lat1
    dlon = np.deg2rad(b[:, 1])[None, :] - np.deg2rad(a[:, 1])[:, None]
    q = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 6371.0088 * 2 * np.arcsin(np.minimum(1, np.sqrt(q)))


def fold_for(lat, lon):
    cell = f"{int((lat + 90) // 10)}:{int((lon + 180) // 10)}"
    return int(hashlib.sha256(("UW-NATIONAL-2026-02:" + cell).encode()).hexdigest()[:8], 16) % 5


def metrics(y, pred, reference):
    y, pred, reference = np.asarray(y, dtype=float), np.asarray(pred, dtype=float), np.asarray(reference, dtype=float)
    err = pred - y
    denom = float(np.sum((y - reference) ** 2))
    return {"n": int(len(y)), "mae_ug_m3": float(np.mean(np.abs(err))),
            "rmse_ug_m3": float(np.sqrt(np.mean(err ** 2))),
            "bias_ug_m3": float(np.mean(err)),
            "r2_vs_training_mean": float(1 - np.sum(err ** 2) / denom) if denom else None}


def predict(method, train_x, train_y, test_x):
    d = haversine(test_x, train_x)
    if method == "nearest_monitor":
        return train_y[np.argmin(d, axis=1)]
    if method == "idw_k4_p2":
        ix = np.argpartition(d, min(3, len(train_y)-1), axis=1)[:, :4]
        ds = np.take_along_axis(d, ix, axis=1)
        weights = 1 / np.maximum(ds, 0.1) ** 2
        return np.sum(train_y[ix] * weights, axis=1) / weights.sum(axis=1)
    if method == "gaussian_kernel_ridge_150km":
        train_d = haversine(train_x, train_x)
        test_d = d
        kernel = np.exp(-0.5 * (train_d / 150.0) ** 2)
        cross = np.exp(-0.5 * (test_d / 150.0) ** 2)
        # Intercept is unpenalized; the spatial residual is ridge-regularized.
        centered = train_y - np.mean(train_y)
        beta = np.linalg.solve(kernel + np.eye(len(train_y)), centered)
        return float(np.mean(train_y)) + cross @ beta
    raise ValueError(method)


def run(release=RELEASE):
    release = Path(release)
    rows = json.loads((release / "monitors.json").read_text())
    site_coordinates = {}
    coordinate_counts = {}
    for row in rows:
        site_coordinates.setdefault(row["id"], (row["latitude"], row["longitude"]))
        coordinate_counts.setdefault(row["id"], set()).add((row["latitude"], row["longitude"]))
    site_folds = {site: fold_for(*xy) for site, xy in site_coordinates.items()}
    report = {"protocol": "UW-NATIONAL-SPATIAL-2026-04", "status": "spatial_cross_validation_complete",
              "split": {"group": "10-degree latitude/longitude cells assigned by fixed SHA-256 fold", "folds": 5,
                        "site_year_grouping": "A physical AQS site retains its coordinate cell in every year; each fold is fit and scored within year.",
                        "preprocessing": "none; coordinates only; all distances and kernel calculations use training rows only",
                        "r2_reference": "training-fold arithmetic mean", "candidates": ["nearest_monitor", "idw_k4_p2", "gaussian_kernel_ridge_150km"]},
              "site_group_audit": {"unique_sites_all_years": len(site_folds), "site_year_rows": len(rows),
                                   "site_ids_with_multiple_reported_coordinates": sum(len(v)>1 for v in coordinate_counts.values()),
                                   "folds_assigned_once_per_site_id": True},
              "years": {}, "limitations": ["Cross-validation folds evaluate spatial generalization across monitor sites.",
                  "2025 EPA annual summaries are provisional and results are supplementary, not the deployed 2024 model's final evaluation.",
                  "Monitor-site prediction does not establish accuracy at unsampled place points.",
                  "AQS event-treatment alternatives are reduced to one ambient summary per POC: Events Included when exceptional-event data are present, otherwise No Events; event-excluded values are not substituted.",
                  "The data contain no verified compatible elevation, land-cover, meteorology, or satellite predictors; no nonlinear environmental model was fitted."]}
    cached = {}
    for year in (2024, 2025):
        data = [r for r in rows if r["year"] == year]
        coords = np.array([[r["latitude"], r["longitude"]] for r in data], dtype=float)
        values = np.array([r["pm25_ug_m3"] for r in data], dtype=float)
        folds = np.array([site_folds[r["id"]] for r in data])
        year_report = {"n_sites": len(data), "folds": {}}
        for fold in range(5):
            te = folds == fold
            tr = ~te
            if te.sum() == 0 or tr.sum() == 0:
                continue
            fold_report = {"test_cells_fold": fold, "n_train": int(tr.sum()), "n_test": int(te.sum()), "methods": {}}
            for method in report["split"]["candidates"]:
                pred = predict(method, coords[tr], values[tr], coords[te])
                fold_report["methods"][method] = metrics(values[te], pred, np.full(te.sum(), values[tr].mean()))
            year_report["folds"][str(fold)] = fold_report
        year_report["pooled_out_of_fold"] = {}
        # Pooled fold scores use fold-specific training means for R2 reference.
        for method in report["split"]["candidates"]:
            ys, ps, refs = [], [], []
            for fold in range(5):
                te = folds == fold
                tr = ~te
                if te.sum() == 0 or tr.sum() == 0:
                    continue
                ys.extend(values[te]); ps.extend(predict(method, coords[tr], values[tr], coords[te])); refs.extend([values[tr].mean()] * int(te.sum()))
            year_report["pooled_out_of_fold"][method] = metrics(np.asarray(ys), np.asarray(ps), np.asarray(refs))
        if year == 2024:
            cached["coords"], cached["values"], cached["folds"], cached["records"] = coords, values, folds, data
        year_report["selection"] = "Nearest monitor retained unless a candidate is consistently better across folds."
        report["years"][str(year)] = year_report
    # A candidate advances only when the fixed spatial kernel wins MAE in at
    # least four of five folds in both modeled and provisional years.
    wins = {}
    for year, result in report["years"].items():
        wins[year] = sum(result["folds"][fold]["methods"]["gaussian_kernel_ridge_150km"]["mae_ug_m3"] < result["folds"][fold]["methods"]["nearest_monitor"]["mae_ug_m3"] for fold in result["folds"])
    selected = "gaussian_kernel_ridge_150km" if all(n >= 4 for n in wins.values()) else "nearest_monitor"
    report["selection"] = {"selected_model": selected, "fold_wins_vs_nearest_by_year": wins,
                           "rule": "Fixed Gaussian kernel advances if it has lower fold MAE in at least four of five geographic folds in both 2024 and provisional 2025.",
                           "status": "spatial_cross_validation_complete"}
    # Deployment refit on the 2024 target. Its empirical band and distance
    # support are based on spatially out-of-fold residuals/distances only.
    coords, values, folds, deployment_rows = cached["coords"], cached["values"], cached["folds"], cached["records"]
    oof_pred = np.empty(len(values)); oof_distance = np.empty(len(values))
    for fold in range(5):
        te, tr = folds == fold, folds != fold
        d = haversine(coords[te], coords[tr])
        oof_distance[te] = d.min(axis=1)
        if selected == "gaussian_kernel_ridge_150km":
            oof_pred[te] = predict(selected, coords[tr], values[tr], coords[te])
        else:
            oof_pred[te] = predict(selected, coords[tr], values[tr], coords[te])
    q90 = float(np.quantile(np.abs(oof_pred - values), .90, method="higher"))
    q75_distance = float(np.quantile(oof_distance, .75, method="higher"))
    support_distance = float(np.quantile(oof_distance, .90, method="higher"))
    train_d = haversine(coords, coords)
    if selected == "gaussian_kernel_ridge_150km":
        kernel = np.exp(-.5 * (train_d / 150.0) ** 2)
        intercept = float(values.mean())
        coefficients = np.linalg.solve(kernel + np.eye(len(values)), values - intercept)
    else:
        intercept, coefficients = None, None
    places_path = release / "places.json"
    places = json.loads(places_path.read_text())
    for start in range(0, len(places), 500):
        batch = places[start:start + 500]
        px = np.array([[p["latitude"], p["longitude"]] for p in batch])
        dist = haversine(px, coords)
        nearest_i = np.argmin(dist, axis=1)
        if selected == "gaussian_kernel_ridge_150km":
            pred = intercept + np.exp(-.5 * (dist / 150.0) ** 2) @ coefficients
        else:
            pred = values[nearest_i]
        for j, p in enumerate(batch):
            p["model_estimates"] = {}
            km = float(dist[j, nearest_i[j]])
            in_domain = 24 <= p["latitude"] <= 50 and -125 <= p["longitude"] <= -66
            if km <= support_distance and in_domain:
                p["model_estimates"]["2024"] = {
                    "value_ug_m3": float(pred[j]), "interval90_low_ug_m3": float(pred[j] - q90),
                    "interval90_high_ug_m3": float(pred[j] + q90), "nearest_monitor_km": km,
                    "reference_monitor_id": deployment_rows[nearest_i[j]]["id"],
                    "reference_monitor_value_ug_m3": float(values[nearest_i[j]]),
                    "estimate_latitude": p["latitude"], "estimate_longitude": p["longitude"],
                    "support": "distance within the 90th percentile of spatial out-of-fold monitor distances; contiguous-U.S. domain",
                    "evidence_status": "low_evidence_estimate" if km > q75_distance else "estimated",
                    "model_id": "upwind-spatial-rbf-annual-pm25-0.3.0" if selected.startswith("gaussian") else "upwind-nearest-monitor-annual-pm25-0.3.0",
                    "evidence_type": "model_estimate"}
    places_path.write_text(json.dumps(places, separators=(",", ":"), allow_nan=False) + "\n")
    supported = sum(bool(p["model_estimates"].get("2024")) for p in places)
    population = sum((p.get("estimates") or {}).get("2024", 0) or 0 for p in places if p["model_estimates"].get("2024"))
    model_id = "upwind-spatial-rbf-annual-pm25-0.3.0" if selected.startswith("gaussian") else "upwind-nearest-monitor-annual-pm25-0.3.0"
    model = {"model_id": model_id, "method": "150 km Gaussian kernel ridge on latitude/longitude" if selected.startswith("gaussian") else "nearest eligible monitor",
             "target": "2024 AQS annual PM2.5 µg/m³", "features": ["latitude", "longitude"],
             "kernel_bandwidth_km": 150 if selected.startswith("gaussian") else None,
             "ridge": 1.0 if selected.startswith("gaussian") else None,
             "training_monitor_ids": [r["id"] for r in deployment_rows],
             "training_monitor_coordinates": coords.tolist(), "training_monitor_values_ug_m3": values.tolist(),
             "intercept": intercept, "coefficients": coefficients.tolist() if coefficients is not None else None,
             "calibration_abs_residual_90pct_ug_m3": q90, "oof_distance_75pct_km": q75_distance,
             "max_supported_nearest_monitor_km": support_distance}
    report["deployment"] = {"model": model, "calibration_abs_residual_90pct_ug_m3": q90,
                            "oof_nearest_monitor_distance_p75_km": q75_distance,
                            "oof_nearest_monitor_distance_p90_support_km": support_distance,
                            "supported_places": supported, "withheld_places": len(places)-supported,
                            "population_for_supported_places": population,
                            "uncertainty_note": "Symmetric 90th-percentile absolute error from spatial out-of-fold monitor predictions; empirical site-level evidence, not a local guarantee."}
    # Preserve the v1 result as historical evidence before replacing active
    # release report/model metadata.
    old_report = release / "model_report.json"
    historical = release / "model_report_v1_historical.json"
    if old_report.exists() and not historical.exists():
        shutil.copy2(old_report, historical)
    report["input_sha256"] = hashlib.sha256((release / "monitors.json").read_bytes()).hexdigest()
    path = release / "model_report_v2_development.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    (release / "model_report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    (release / "model.json").write_text(json.dumps(model, separators=(",", ":"), allow_nan=False) + "\n")
    manifest_path = release / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["release"] = "upwind-national-explorer-0.3.0"
    manifest["model"] = {k: model[k] for k in ("model_id", "method", "target", "features", "kernel_bandwidth_km", "ridge")}
    manifest["counts"].update({"modeled_places": supported, "supported_model_places": supported, "population_covered": population})
    manifest.setdefault("coverage", {}).update({"with_estimate": supported, "without_supported_estimate": len(places)-supported,
                                 "population_for_estimated_places": population})
    evaluation_summary = {"protocol": report["protocol"], "status": report["selection"]["status"],
                          "years": {y: d["pooled_out_of_fold"] for y,d in report["years"].items()},
                          "selection": report["selection"], "deployment": {k:v for k,v in report["deployment"].items() if k != "model"}}
    # Keep the original key for v2 clients while introducing the corrected-data
    # release key. Both point to the same currently deployed estimate contract.
    manifest["model_evaluation_v2"] = evaluation_summary
    manifest["model_evaluation_v3"] = evaluation_summary
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps({year: result["pooled_out_of_fold"] for year, result in report["years"].items()}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-dir", type=Path, default=RELEASE)
    run(parser.parse_args().release_dir)
