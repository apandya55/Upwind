#!/usr/bin/env python3
"""Fit and geographically evaluate annual PM2.5 place estimates offline.

The first release intentionally uses coordinates only. Development chooses a
Gaussian radial-basis ridge smoother against nearest-monitor and regional-mean
baselines. Independent 2-degree geographic blocks form calibration and final
test splits; sites in a held block never enter its training fold.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "data/national/release"


def read_json(path):
    return json.loads(Path(path).read_text())


def distance_matrix_km(a, b):
    # Equirectangular geometry is sufficiently accurate for the 2-degree
    # block-scale model; great-circle distance is separately used for support.
    lat0 = np.deg2rad((np.mean(a[:, 0]) + np.mean(b[:, 0])) / 2)
    aa = np.column_stack((a[:, 1] * np.cos(lat0), a[:, 0]))
    bb = np.column_stack((b[:, 1] * np.cos(lat0), b[:, 0]))
    d = aa[:, None, :] - bb[None, :, :]
    return np.sqrt((d * d).sum(axis=2)) * 111.195


def haversine(a, b):
    lat1, lon1 = np.deg2rad(a[:, 0]), np.deg2rad(a[:, 1])
    lat2, lon2 = np.deg2rad(b[:, 0]), np.deg2rad(b[:, 1])
    dlat, dlon = lat2[None, :] - lat1[:, None], lon2[None, :] - lon1[:, None]
    z = np.sin(dlat / 2) ** 2 + np.cos(lat1[:, None]) * np.cos(lat2[None, :]) * np.sin(dlon / 2) ** 2
    return 6371.0088 * 2 * np.arcsin(np.minimum(1, np.sqrt(z)))


def block_id(coords):
    lat_block = np.floor((coords[:, 0] + 90) / 2).astype(int)
    lon_block = np.floor((coords[:, 1] + 180) / 2).astype(int)
    # Multipliers are fixed protocol constants; adjacent blocks remain held out together.
    return (lat_block * 37 + lon_block * 17) % 5


def centers_farthest(coords, count=80):
    if len(coords) <= count:
        return coords.copy()
    rng = np.random.default_rng(26092026)
    chosen = [int(np.argmin((coords[:, 0] - np.median(coords[:, 0])) ** 2 + (coords[:, 1] - np.median(coords[:, 1])) ** 2))]
    closest = np.full(len(coords), np.inf)
    while len(chosen) < count:
        last = coords[chosen[-1]]
        d = distance_matrix_km(coords, last[None, :])[:, 0]
        closest = np.minimum(closest, d)
        closest[chosen] = -1
        chosen.append(int(np.argmax(closest)))
    return coords[np.asarray(chosen)]


def design(coords, centers, sigma):
    d = distance_matrix_km(coords, centers)
    basis = np.exp(-0.5 * (d / sigma) ** 2)
    return np.column_stack((np.ones(len(coords)), (coords[:, 0] - 39) / 10, (coords[:, 1] + 98) / 15, basis))


def fit_predict(train_x, train_y, test_x, sigma, ridge=0.1):
    centers = centers_farthest(train_x)
    tr, te = design(train_x, centers, sigma), design(test_x, centers, sigma)
    penalty = np.eye(tr.shape[1]) * ridge
    penalty[:3, :3] = 0
    beta = np.linalg.solve(tr.T @ tr + penalty, tr.T @ train_y)
    return te @ beta


def metrics(y, pred):
    e = np.asarray(pred) - np.asarray(y)
    return {"n": int(len(e)), "mae_ug_m3": float(np.mean(np.abs(e))), "rmse_ug_m3": float(np.sqrt(np.mean(e**2))), "signed_bias_ug_m3": float(np.mean(e)), "r2": float(1 - np.sum(e**2) / max(np.sum((y - np.mean(y))**2), 1e-12))}


def region_for(lat, lon):
    if lat >= 48: return "Alaska / northern"
    if lon <= -125: return "Pacific"
    if lon <= -113: return "Mountain West"
    if lon <= -100: return "Central"
    if lon <= -85: return "Midwest / South"
    if lon <= -75: return "Southeast"
    return "Northeast / Atlantic"


def run(release=RELEASE):
    release = Path(release)
    manifest_path = release / "manifest.json"
    monitors_path, places_path = release / "monitors.json", release / "places.json"
    manifest = read_json(manifest_path)
    year = int(manifest["selected_modeling_year"])
    records = [r for r in read_json(monitors_path) if r["year"] == year]
    if len(records) < 100:
        raise ValueError(f"Need >=100 eligible site-years; found {len(records)}")
    coords = np.array([[r["latitude"], r["longitude"]] for r in records], float)
    y = np.array([r["pm25_ug_m3"] for r in records], float)
    blocks = block_id(coords)
    # Development folds exclude final block 0 and calibration block 1.
    development = []
    for fold in (2, 3, 4):
        test = blocks == fold
        train = np.isin(blocks, [2, 3, 4]) & ~test
        if test.sum() and train.sum():
            development.append((train, test))
    sigmas = (50.0, 100.0, 200.0)
    tuning = []
    for sigma in sigmas:
        truth, pred = [], []
        for tr, te in development:
            truth.extend(y[te]); pred.extend(fit_predict(coords[tr], y[tr], coords[te], sigma))
        tuning.append({"sigma_km": sigma, **metrics(np.asarray(truth), np.asarray(pred))})
    selected = min(tuning, key=lambda row: row["rmse_ug_m3"])["sigma_km"]
    # Calibration and final evaluation use entirely held geographic block IDs.
    train = np.isin(blocks, [2, 3, 4])
    calibration = blocks == 1
    final = blocks == 0
    if not final.any() or not calibration.any():
        raise ValueError("Spatial split produced an empty calibration or final fold")
    cal_pred = fit_predict(coords[train], y[train], coords[calibration], selected)
    final_pred = fit_predict(coords[train], y[train], coords[final], selected)
    candidate_test = metrics(y[final], final_pred)
    cal_distances = haversine(coords[calibration], coords[train])
    cal_nearest_idx = np.argmin(cal_distances, axis=1)
    cal_nearest = y[train][cal_nearest_idx]
    cal_nearest_distance = cal_distances[np.arange(calibration.sum()), cal_nearest_idx]
    # Freeze the support distance from calibration geography, before touching
    # final-test predictions.
    max_supported_distance = float(np.quantile(cal_nearest_distance, 0.9, method="higher"))
    final_distance_matrix = haversine(coords[final], coords[train])
    final_nearest_index = np.argmin(final_distance_matrix, axis=1)
    final_nearest = final_distance_matrix[np.arange(final.sum()), final_nearest_index]
    nearest = y[train][final_nearest_index]
    nearest_test = metrics(y[final], nearest)
    # Paired geographic-cluster bootstrap by state. Negative means RBF has
    # lower loss. This is descriptive for the held-out geography and does not
    # turn 166 correlated sites into 166 independent regions.
    state_codes = np.array([r["state_fips"] for r, keep in zip(records, final) if keep])
    unique_states = np.unique(state_codes)
    grouped = [np.flatnonzero(state_codes == state) for state in unique_states]
    rng = np.random.default_rng(26092026)
    mae_delta, rmse_delta = [], []
    rbf_abs = np.abs(final_pred - y[final]); near_abs = np.abs(nearest - y[final])
    rbf_sq = (final_pred - y[final]) ** 2; near_sq = (nearest - y[final]) ** 2
    for _ in range(4000):
        chosen = rng.integers(0, len(grouped), size=len(grouped))
        ix = np.concatenate([grouped[j] for j in chosen])
        mae_delta.append(float(np.mean(rbf_abs[ix] - near_abs[ix])))
        rmse_delta.append(float(np.sqrt(np.mean(rbf_sq[ix])) - np.sqrt(np.mean(near_sq[ix]))))
    paired_comparison = {
        "unit": "state-cluster bootstrap resampling final-test states with replacement",
        "seed": 26092026, "replicates": 4000, "clusters": int(len(unique_states)),
        "mae_candidate_minus_nearest_ug_m3": float(candidate_test["mae_ug_m3"] - nearest_test["mae_ug_m3"]),
        "mae_95pct_interval": [float(np.quantile(mae_delta, .025)), float(np.quantile(mae_delta, .975))],
        "rmse_candidate_minus_nearest_ug_m3": float(candidate_test["rmse_ug_m3"] - nearest_test["rmse_ug_m3"]),
        "rmse_95pct_interval": [float(np.quantile(rmse_delta, .025)), float(np.quantile(rmse_delta, .975))],
        "interpretation": "Intervals crossing zero do not establish improvement; state clustering is still an imperfect approximation to spatial dependence.",
    }
    choose_rbf = paired_comparison["mae_95pct_interval"][1] < 0 and paired_comparison["rmse_95pct_interval"][1] < 0
    deployment_method = "rbf" if choose_rbf else "nearest_monitor"
    selected_prediction = final_pred if choose_rbf else nearest
    cal_selected = cal_pred if choose_rbf else cal_nearest
    cal_abs = np.abs(y[calibration] - cal_selected)
    q90 = float(np.quantile(cal_abs, 0.90, method="higher"))
    baseline = {
        "regional_mean": metrics(y[final], np.full(final.sum(), y[train].mean())),
        "nearest_monitor": nearest_test,
    }
    # A development-only relative skill gate prevents a complex smoother from
    # being selected on an insignificant final-test difference.
    model_spec = {"model_id": "upwind-nearest-monitor-annual-pm25-0.1.0" if not choose_rbf else "upwind-spatial-rbf-annual-pm25-0.1.0", "method": "nearest eligible training monitor" if not choose_rbf else "Gaussian radial-basis ridge spatial smoother", "candidate_model_id": "upwind-spatial-rbf-annual-pm25-0.1.0", "target": f"{year} AQS annual PM2.5 µg/m³", "features": ["latitude", "longitude"], "basis_centers": min(80, len(coords)), "selected_sigma_km": selected, "ridge": 0.1, "selection_rule": "Select RBF only if paired state-cluster 95% intervals show lower held-out MAE and RMSE; otherwise deploy nearest-monitor baseline."}
    # Refit RBF coefficients for deployment; reproduce the fitted model from a
    # direct serialized center/beta record rather than keeping per-place scores.
    centers = centers_farthest(coords)
    tr = design(coords, centers, selected)
    penalty = np.eye(tr.shape[1]) * 0.1; penalty[:3, :3] = 0
    beta = np.linalg.solve(tr.T @ tr + penalty, tr.T @ y)
    places = read_json(places_path)
    place_coords = np.array([[p["latitude"], p["longitude"]] for p in places], float)
    place_distances = haversine(place_coords, coords)
    nearest_km = place_distances.min(axis=1)
    supported = (nearest_km <= max_supported_distance) & (place_coords[:,0] >= 24) & (place_coords[:,0] <= 50) & (place_coords[:,1] >= -125) & (place_coords[:,1] <= -66)
    rbf_estimate = design(place_coords, centers, selected) @ beta
    place_nearest_idx = np.argmin(place_distances, axis=1)
    estimate = rbf_estimate if choose_rbf else y[place_nearest_idx]
    for i,p in enumerate(places):
        p["model_estimates"] = {}
        if supported[i]:
            p["model_estimates"][str(year)] = {"value_ug_m3": float(estimate[i]), "interval90_low_ug_m3": float(estimate[i]-q90), "interval90_high_ug_m3": float(estimate[i]+q90), "nearest_monitor_km": float(nearest_km[i]), "reference_monitor_id": records[int(place_nearest_idx[i])]["id"], "reference_monitor_value_ug_m3": float(y[place_nearest_idx[i]]), "support": "within calibration-block 90th-percentile distance to an eligible monitor", "model_id": model_spec["model_id"], "evidence_type": "model_estimate"}
    # Monitoring evidence is a 5 km centroid-neighborhood rule, not a claim of
    # monitor containment in a place's legal boundary (polygon overlay absent).
    dist_place_monitor = nearest_km
    nearby = dist_place_monitor <= 5.0
    place_status = {"searchable_places": len(places), "with_estimate": int(supported.sum()), "without_supported_estimate": int((~supported).sum()), "with_monitor_within_5km_of_gazetteer_point": int(nearby.sum()), "monitoring_rule": "AQS spatial site within 5 km of Gazetteer internal point; proximity proxy, not point-in-place polygon evidence.", "population_vintage": "Census 2020-2024 PEP; unique GEOID places with latest 2024 estimate", "population_for_estimated_places": int(sum((p["estimates"].get("2024") or 0) for i,p in enumerate(places) if supported[i] and p["id"])), "places_with_population": int(sum("2024" in p["estimates"] for p in places))}
    # unique place GEOIDs avoid adding counties, cities and metros together.
    place_status["population_for_estimated_places"] = int(sum((p["estimates"].get("2024") or 0) for i,p in enumerate(places) if supported[i]))
    errors = selected_prediction - y[final]
    final_regions = np.array([region_for(a,b) for a,b in coords[final]])
    region_metrics = {name: metrics(y[final][final_regions == name], selected_prediction[final_regions == name]) for name in sorted(set(final_regions))}
    concentration_bins = {"<8": y[final] < 8, "8-12": (y[final] >= 8) & (y[final] < 12), "12-15": (y[final] >= 12) & (y[final] < 15), ">=15": y[final] >= 15}
    concentration_metrics = {name: metrics(y[final][mask], selected_prediction[mask]) for name,mask in concentration_bins.items() if np.any(mask)}
    distance_bins = {"<=50km": final_nearest <= 50, "50-100km": (final_nearest > 50) & (final_nearest <= 100), "100-200km": (final_nearest > 100) & (final_nearest <= 200), ">200km": final_nearest > 200}
    distance_metrics = {name: metrics(y[final][mask], selected_prediction[mask]) for name,mask in distance_bins.items() if np.any(mask)}
    selected_metrics = metrics(y[final], selected_prediction)
    report = {"protocol": "UW-NATIONAL-SPATIAL-2026-01", "model": model_spec, "input_year": year, "site_years": len(records), "unique_sites": len({r["id"] for r in records}), "geographic_split": {"unit": "2-degree latitude/longitude blocks", "fold_assignment": "fixed arithmetic hash modulo 5", "development_blocks": "2,3,4 with block-wise cross-validation", "calibration_block": 1, "final_test_block": 0, "development_tuning": tuning, "training_final_n": int(train.sum()), "calibration_n": int(calibration.sum()), "final_test_n": int(final.sum()), "site_leakage": False}, "final_test": {"selected_method": selected_metrics, "rbf_candidate": candidate_test, "baselines": baseline, "paired_rbf_vs_nearest": paired_comparison, "by_region": region_metrics, "by_concentration_ug_m3": concentration_metrics, "by_nearest_training_monitor_distance": distance_metrics, "distance_to_training_monitor_km": {"median": float(np.median(final_nearest)), "calibration_p90_support_threshold_km": max_supported_distance, "max": float(np.max(final_nearest))}, "calibration_abs_residual_90pct_ug_m3": q90, "calibration_empirical_coverage_on_final_test": float(np.mean(np.abs(y[final] - selected_prediction) <= q90)), "calibration_interval_width_ug_m3": 2*q90}, "coverage": place_status, "limitations": ["Coordinate-only interpolation; no elevation, meteorology, land cover, or emissions predictors.", "Annual monitor-site summaries are spatially held out, not a future-year forecast.", "Spatial blocks do not cover territories or guarantee environmental support between monitors.", "Intervals are symmetric empirical calibration bands, not a calibrated Bayesian posterior.", "EPA annual summaries have regulatory completeness and event-treatment conventions; this release retains them and does not reconstruct daily exposure.", "Monitor-within-5-km counts use Gazetteer internal points, not Census place polygon containment."], "deployment_refit": "Selected method fitted on all eligible site-years after evaluation; reported test score is the held-out block-0 result.", "input_sha256": {"monitors.json": hashlib.sha256(monitors_path.read_bytes()).hexdigest(), "places.json": hashlib.sha256(places_path.read_bytes()).hexdigest()}}
    (release / "model_report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    (release / "places.json.partial").write_text(json.dumps(places, separators=(",",":"), allow_nan=False)+"\n")
    (release / "places.json.partial").replace(places_path)
    artifact = {**model_spec, "training_monitor_ids": [r["id"] for r in records], "training_monitor_coordinates": coords.tolist(), "training_monitor_values_ug_m3": y.tolist(), "calibration_abs_residual_90pct_ug_m3": q90, "max_supported_nearest_monitor_km": max_supported_distance}
    if choose_rbf:
        artifact["rbf_coefficients"] = {"centers_latlon": centers.tolist(), "coefficients": beta.tolist()}
    (release / "model.json").write_text(json.dumps(artifact,separators=(",",":"))+"\n")
    manifest.update({"model": model_spec, "model_evaluation": report["final_test"], "coverage": place_status, "counts": {"searchable_census_places":len(places),"monitor_site_years":len(read_json(monitors_path)),"monitor_sites_selected_year":len(records),"modeled_places":place_status["with_estimate"],"supported_model_places":place_status["with_estimate"],"places_with_nearby_monitor_proxy":place_status["with_monitor_within_5km_of_gazetteer_point"],"population_covered":place_status["population_for_estimated_places"]}, "status":"model_trained_spatially_evaluated"})
    (release / "manifest.json.partial").write_text(json.dumps(manifest, indent=2, sort_keys=True)+"\n")
    (release / "manifest.json.partial").replace(manifest_path)
    print(json.dumps({"model":model_spec,"final_test":report["final_test"],"coverage":place_status},indent=2))


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument("--release-dir",type=Path,default=RELEASE); args=parser.parse_args(); run(args.release_dir)
