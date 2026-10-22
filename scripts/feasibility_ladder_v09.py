"""Run the small, labeled v0.9 feasibility ladder.

This is a diagnostic harness, not an operational evaluator.  Truth and the
known-weather oracle are kept in the output's private diagnostic section and
are never passed to the production fit.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

from upwind.engine import analyze, plume
from upwind.fixtures import synthetic_case
from upwind.inference import CONFIG, MODEL_VERSION, PROTOCOL_VERSION, fit
from upwind.models import Measurement, Site
from upwind.numerics import projector

ROOT = Path(__file__).resolve().parents[1]


def _source_hash():
    files = sorted((ROOT / "backend/upwind").rglob("*.py"))
    payload = [
        (str(path.relative_to(ROOT)), hashlib.sha256(path.read_bytes()).hexdigest())
        for path in files
    ]
    return hashlib.sha256(json.dumps(payload, separators=(",", ":")).encode()).hexdigest()


def independent_scalar_plume(receptor, source, strength, speed, wind_from):
    """Independent scalar check of the documented neutral Gaussian formula."""
    dx, dy = np.asarray(receptor, float) - np.asarray(source, float)
    angle = np.deg2rad(wind_from % 360.0)
    fx, fy = -np.sin(angle), -np.cos(angle)
    down = dx * fx + dy * fy
    cross = dx * (-fy) + dy * fx
    x = max(down, 20.0)
    sy = 0.08 * x / np.sqrt(1 + 0.0001 * x)
    sz = 0.06 * x / np.sqrt(1 + 0.0015 * x)
    vertical = np.exp(-0.5 * ((2.0 - 5.0) / sz) ** 2) + np.exp(
        -0.5 * ((2.0 + 5.0) / sz) ** 2
    )
    transverse = np.exp(-0.5 * min(abs(cross) / sy, 40.0) ** 2)
    value = strength / (2 * np.pi * speed * sy * sz) * transverse * vertical
    return float(value if down >= 20 and np.hypot(dx, dy) <= 3000 else 0.0)


def _strong_case(seed, *, extra_sensor=False):
    inv, truth = synthetic_case("identifiable", seed)
    tr = projector(0.0, 0.0)
    source = np.array([-650.0, 250.0])
    if extra_sensor:
        candidate = next(site for site in inv.sites if site.id == "C8")
        sensor = Site(
            id="M4",
            name="Additional diagnostic monitor",
            kind="sensor",
            allowed=True,
            power=True,
            access=True,
            cost=0,
            latitude=candidate.latitude,
            longitude=candidate.longitude,
        )
        inv.sites.append(sensor)
    for row in inv.measurements:
        receptor = np.asarray(tr.transform(row.longitude, row.latitude))
        weather = next(w for w in inv.weather if w.timestamp == row.timestamp)
        value = independent_scalar_plume(receptor, source, 250_000.0, 2.3, weather.wind_from_deg)
        if row.sensor_id == "M4":
            value = independent_scalar_plume(receptor, source, 250_000.0, 2.3, weather.wind_from_deg)
        row.pm25_ug_m3 = 10.0 + value
    if extra_sensor:
        sensor = next(site for site in inv.sites if site.id == "M4")
        for weather in inv.weather:
            receptor = np.asarray(tr.transform(sensor.longitude, sensor.latitude))
            value = independent_scalar_plume(receptor, source, 250_000.0, 2.3, weather.wind_from_deg)
            inv.measurements.append(
                Measurement(
                    sensor_id="M4",
                    timestamp=weather.timestamp,
                    latitude=sensor.latitude,
                    longitude=sensor.longitude,
                    origin="synthetic",
                    pm25_ug_m3=10.0 + value,
                )
            )
    truth["strength_ug_s"] = 250_000
    return inv, truth


def _cases(seed):
    weak, weak_truth = synthetic_case("identifiable", seed)
    strong, strong_truth = _strong_case(seed + 1)
    unknown = strong.model_copy(deep=True)
    sensor = strong.model_copy(deep=True)
    for row in sensor.measurements:
        if row.sensor_id == "M1":
            row.pm25_ug_m3 += 6.0
    background = strong.model_copy(deep=True)
    for row in background.measurements:
        row.pm25_ug_m3 += 8.0
    weather = strong.model_copy(deep=True)
    for row in weather.weather:
        row.wind_from_deg = (row.wind_from_deg + 18.0) % 360.0
    extra, extra_truth = _strong_case(seed + 2, extra_sensor=True)
    source_free, source_free_truth = synthetic_case("identifiable", seed + 3)
    for row in source_free.measurements:
        row.pm25_ug_m3 = 10.0
    source_free_truth["source_present"] = False
    source_free_truth["source"] = None
    two, two_truth = synthetic_case("multiple_sources", seed + 4)
    out, out_truth = synthetic_case("identifiable", seed + 5)
    out_source = np.array([-2000.0, 250.0])
    out_tr = projector(0.0, 0.0)
    for row in out.measurements:
        receptor = np.asarray(out_tr.transform(row.longitude, row.latitude))
        weather_row = next(w for w in out.weather if w.timestamp == row.timestamp)
        row.pm25_ug_m3 = 10.0 + independent_scalar_plume(
            receptor, out_source, 250_000.0, 2.3, weather_row.wind_from_deg
        )
    out_truth["source"] = {"x_m": float(out_source[0]), "y_m": float(out_source[1])}
    out_truth["source_present"] = True
    return {
        "weak_current_fixture": (weak, weak_truth, dict(wind_uncertainty=True)),
        "strong_known_weather": (strong, strong_truth, dict(wind_uncertainty=False)),
        "unknown_strength": (unknown, strong_truth, dict(wind_uncertainty=True)),
        "sensor_offset": (sensor, strong_truth, dict(wind_uncertainty=True)),
        "background_shift": (background, strong_truth, dict(wind_uncertainty=True)),
        "weather_bias": (weather, strong_truth, dict(wind_uncertainty=True)),
        "additional_sensor": (extra, extra_truth, dict(wind_uncertainty=False)),
        "source_free": (source_free, source_free_truth, dict(wind_uncertainty=True)),
        "two_sources": (two, two_truth, dict(wind_uncertainty=True)),
        "out_of_domain_diagnostic": (out, out_truth, dict(wind_uncertainty=False)),
    }


def _truth_xy(tr, truth):
    source = truth.get("source", {})
    if source is None:
        return None
    if "x_m" in source:
        return np.array([source["x_m"], source["y_m"]], float)
    return np.asarray(tr.transform(source["longitude"], source["latitude"]), float)


def _row(name, inv, truth, options):
    payload = inv.model_dump_json()
    input_hash = hashlib.sha256(payload.encode()).hexdigest()
    result = None
    fit_result = None
    error = None
    try:
        fit_result = fit(inv, diagnostics=False, **options)
        # The public call is retained for the support decision and warning
        # contract; its evaluator does not receive truth or oracle values.
        result = analyze(inv)
    except Exception as exc:  # preserve a failed ladder rung as evidence
        error = f"{type(exc).__name__}: {exc}"
    tr = projector(0.0, 0.0)
    truth_xy = _truth_xy(tr, truth)
    estimate = (result or {}).get("location_estimate") or (fit_result or {}).get("location_estimate") or {}
    mean = estimate.get("posterior_mean")
    mean_error = None
    if mean and "longitude" in mean and truth_xy is not None:
        mean_xy = np.asarray(tr.transform(mean["longitude"], mean["latitude"]), float)
        mean_error = float(np.linalg.norm(mean_xy - truth_xy))
    anchor_xy = np.asarray(
        [tr.transform(point.longitude, point.latitude) for point in inv.source_locations],
        float,
    )
    domain_center_error = None
    if truth_xy is not None and len(anchor_xy):
        domain_center_error = float(np.linalg.norm(truth_xy - anchor_xy.mean(axis=0)))
    sensitivity = (result or {}).get("strength_prior_sensitivity") or (fit_result or {}).get("strength_prior_sensitivity")
    return {
        "case": name,
        "input_sha256": input_hash,
        "fit_error": error,
        "status": (result or {}).get("status"),
        "evidence_status": (result or {}).get("evidence_status"),
        "source_probability": (result or {}).get("source_probability") if result else (fit_result or {}).get("source_probability"),
        "mean_error_m_diagnostic": mean_error,
        "prior_domain_center_error_m": domain_center_error,
        "region_area_fraction": ((result or {}).get("source_region90") or {}).get("area_m2") / max(((result or {}).get("source_region90") or {}).get("domain_area_m2") or 1.0, 1.0) if result else None,
        "spatial_rms_m": ((fit_result or {}).get("location_estimate") or {}).get("spatial_rms_m") if fit_result else None,
        "spatial_quadrature_order": (fit_result or {}).get("spatial_quadrature_order") if fit_result else None,
        "integration_points": (fit_result or {}).get("integration_points") if fit_result else None,
        "numerical_converged": (result or {}).get("numerical_converged") if result else (fit_result or {}).get("numerical_converged"),
        "sensitivity_blocking": (sensitivity or {}).get("blocking") if sensitivity else None,
        "sensitivity_material_factors": (sensitivity or {}).get("material_factors", []) if sensitivity else [],
        "warnings": (result or {}).get("warnings", []),
        "runtime_ms": (result or {}).get("runtime_ms"),
    }


def run(out, seed):
    out = Path(out)
    if out.exists():
        raise FileExistsError("Refusing to overwrite an existing v0.9 ladder directory")
    out.mkdir(parents=True)
    cases = _cases(seed)
    rows = [_row(name, *values) for name, values in cases.items()]
    private_truth = {row["case"]: cases[row["case"]][1] for row in rows}
    scalar = independent_scalar_plume(np.array([0.0, 200.0]), np.array([-650.0, 250.0]), 5_000.0, 2.3, 270.0)
    production = float(plume(np.array([[0.0, 200.0]]), np.array([-650.0, 250.0]), 5_000.0, 2.3, 270.0)[0])
    metadata = {
        "model_version": MODEL_VERSION,
        "protocol_version": PROTOCOL_VERSION,
        "seed": seed,
        "cases": list(cases),
        "source_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "candidate_source_sha256": _source_hash(),
        "configuration_sha256": hashlib.sha256(
            json.dumps(CONFIG, sort_keys=True, default=str).encode()
        ).hexdigest(),
        "scope": "Labeled synthetic feasibility ladder; no measured validation, attribution, calibration or field accuracy claim.",
        "known_weather_oracle": "Only the strong_known_weather and additional_sensor fit calls disable weather uncertainty; this is a diagnostic control, not an operational input.",
    }
    summary = {
        "attempts": len(rows),
        "fit_failures": sum(row["fit_error"] is not None for row in rows),
        "public_source_supported": sum(row["evidence_status"] == "source_supported" for row in rows),
        "sensitivity_blocked": sum(row["sensitivity_blocking"] is True for row in rows),
        "independent_scalar_vs_production_abs_delta": abs(scalar - production),
        "independent_scalar_value_ug_m3": scalar,
        "production_scalar_value_ug_m3": production,
        "simple_baseline": "The prior/domain baseline is the declared source rectangle; the ladder stores diagnostic point error against its truth but does not treat truth as production input.",
    }
    (out / "metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    (out / "results.json").write_text(json.dumps(rows, indent=2, allow_nan=False) + "\n")
    (out / "private_truth.json").write_text(json.dumps(private_truth, indent=2, sort_keys=True) + "\n")
    (out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=9_100_001)
    args = parser.parse_args()
    run(args.out, args.seed)
