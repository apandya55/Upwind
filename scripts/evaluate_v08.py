"""Fresh paired source/weather quadrature evaluation for engine 0.8."""

import argparse
import hashlib
import importlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

from upwind.engine import analyze
from upwind.fixtures import synthetic_case
from upwind.inference import CONFIG, MODEL_VERSION, PROTOCOL_VERSION
from upwind.numerics import projector, plume

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "evaluations/engine-v08/v07-baseline/upwind"
SPLITS = {
    "development": list(range(8_410_000, 8_410_016)),
    "calibration": list(range(8_420_000, 8_420_016)),
    "final": list(range(8_430_000, 8_430_032)),
}
PILOT_SEEDS = [8_440_000]
FAMILIES = (
    "nominal",
    "humidity_response",
    "sensor_drift",
    "changing_release",
    "two_sources",
    "spatial_background",
    "heavy_tail",
    "weather_error",
)


def _load_baseline():
    name = "_upwind_v07_paired_baseline"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            name, BASELINE / "__init__.py", submodule_search_locations=[str(BASELINE)]
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return importlib.import_module(name + ".engine"), importlib.import_module(name + ".models")


def _world(family, seed):
    case = "multiple_sources" if family == "two_sources" else "identifiable"
    inv, truth = synthetic_case(case, seed)
    rng = np.random.default_rng(seed + 73_000_000)
    ordered = sorted(inv.measurements, key=lambda row: row.timestamp)
    if family == "humidity_response":
        for row in inv.measurements:
            row.humidity_percent = 88.0 if row.sensor_id == "M1" else 45.0
            if row.sensor_id == "M1":
                row.pm25_ug_m3 += 5.0 * (88.0 - 70.0) / 20.0
    elif family == "sensor_drift":
        for index, row in enumerate(ordered):
            if row.sensor_id == "M1":
                row.pm25_ug_m3 += 0.9 * index
    elif family == "changing_release":
        tr = projector(0.0, 0.0)
        for row in ordered:
            if row.timestamp >= "2025-06-12T10:15:00+00:00":
                receptor = tr.transform(row.longitude, row.latitude)
                wind = next(w.wind_from_deg for w in inv.weather if w.timestamp == row.timestamp)
                row.pm25_ug_m3 += float(plume([receptor], [-650.0, 250.0], 5000.0, 2.3, wind)[0])
    elif family == "spatial_background":
        offsets = {"M1": 7.0, "M2": -5.0, "M3": 4.0}
        for row in inv.measurements:
            row.pm25_ug_m3 += offsets[row.sensor_id]
    elif family == "heavy_tail":
        for row in rng.choice(inv.measurements, size=2, replace=False):
            row.pm25_ug_m3 += 18.0
    elif family == "weather_error":
        for row in inv.weather:
            row.wind_from_deg = (row.wind_from_deg + 18.0) % 360.0
    truth["family"] = family
    truth["seed"] = seed
    truth["source_count"] = 2 if family == "two_sources" else 1
    truth["sources"] = [truth["source"]]
    if family == "two_sources":
        lon, lat = projector(0.0, 0.0).transform(-250.0, -150.0, direction="INVERSE")
        truth["sources"].append({"longitude": float(lon), "latitude": float(lat)})
    return inv, truth


def _source_hash():
    paths = sorted((ROOT / "backend/upwind").rglob("*.py"))
    payload = [(str(p.relative_to(ROOT)), hashlib.sha256(p.read_bytes()).hexdigest()) for p in paths]
    return hashlib.sha256(json.dumps(payload, separators=(",", ":")).encode()).hexdigest()


def _inside(point, polygon):
    x, y = point["longitude"], point["latitude"]
    vertices = [(p["longitude"], p["latitude"]) for p in polygon]
    inside = False
    j = len(vertices) - 1
    for i, (xi, yi) in enumerate(vertices):
        xj, yj = vertices[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def _metrics(result, truth):
    truths = truth["sources"]
    projection = projector(truth["source"]["latitude"], truth["source"]["longitude"])
    truth_xy = np.asarray([projection.transform(s["longitude"], s["latitude"]) for s in truths])
    estimate = result.get("location_estimate") or {}
    def error(point):
        if not point:
            return None
        xy = np.asarray(projection.transform(point["longitude"], point["latitude"]))
        return float(np.linalg.norm(truth_xy - xy, axis=1).min())
    region = result.get("source_region90") or {}
    cells = region.get("cells") or []
    covered = [any(_inside(source, cell["polygon"]) for cell in cells) for source in truths]
    domain = float(region.get("domain_area_m2") or 0.0)
    checks = []
    diagnostics = result.get("diagnostics") or {}
    for kind in ("held_out_sensor", "held_out_window"):
        checks.extend({"kind": kind, **row} for row in diagnostics.get(kind, []))
    scores = [{k: row.get(k) for k in ("rows", "rmse_ug_m3", "coverage90", "mean_nlpd", "tail_probability")} for row in checks if not row.get("unavailable")]
    return {
        "mean_error_m": error(estimate.get("posterior_mean")),
        "mode_error_m": error(estimate.get("density_mode")),
        "truth_region_coverage": covered,
        "truth_region_coverage_any": any(covered),
        "truth_region_coverage_all": all(covered),
        "truth_region_correct_for_source_count": all(covered) if len(truths) > 1 else any(covered),
        "truth_sources_covered": sum(covered),
        "truth_source_count": len(truths),
        "region_area_fraction": float(region.get("area_m2", 0.0) / domain) if domain else None,
        "region_area_m2": region.get("area_m2"),
        "region_component_count": (region.get("connected_region_structure") or {}).get("component_count"),
        "region_component_separation_m": (region.get("connected_region_structure") or {}).get("minimum_component_centroid_separation_m"),
        "posterior_region_mode_count": (region.get("connected_region_structure") or {}).get("component_count"),
        "held_out_checks": scores,
        "held_out_checks_unavailable": sum(bool(row.get("unavailable")) for row in checks),
    }


def _row(result, truth, input_hash, engine_name):
    metric = _metrics(result, truth)
    met = result.get("meteorology_evidence") or {}
    observability = result.get("observability") or {}
    external = observability.get("externalities") or {}
    source_count = observability.get("source_count") or {}
    return {
        "engine": engine_name,
        "seed": truth["seed"],
        "family": truth["family"],
        "input_sha256": input_hash,
        "status": result.get("status"),
        "evidence_status": result.get("evidence_status"),
        "source_probability": result.get("source_probability"),
        "numerical_converged": result.get("numerical_converged"),
        "warnings": result.get("warnings", []),
        "quadrature_diagnostics": result.get("quadrature_diagnostics"),
        "externality_flags": external.get("flags", []),
        "source_count_diagnostic": {
            "material_competing_pair": source_count.get("material_competing_pair"),
            "diagnostic_unavailable": source_count.get("diagnostic_unavailable"),
        },
        "weather_posterior_location_span_m": met.get("source_weather_location_span_m"),
        "weather_common_mode_posterior_probability": met.get("common_mode_posterior_probability"),
        "runtime_ms": result.get("runtime_ms"),
        "refusal_reason": result.get("reason") if result.get("status") not in {"ok", "uninformative"} else None,
        **metric,
    }


def _summary(rows):
    def distribution(selected, key):
        values = sorted(float(r[key]) for r in selected if r.get(key) is not None and np.isfinite(r[key]))
        if not values:
            return {"n": 0, "median": None, "p90": None, "p95": None, "maximum": None}
        return {
            "n": len(values),
            "median": float(np.quantile(values, 0.5)),
            "p90": float(np.quantile(values, 0.9)),
            "p95": float(np.quantile(values, 0.95)),
            "maximum": float(max(values)),
        }

    by_family = {}
    for family in FAMILIES:
        selected = [r for r in rows if r["family"] == family]
        def median(key):
            values = [r[key] for r in selected if r.get(key) is not None and np.isfinite(r[key])]
            return float(np.median(values)) if values else None
        by_family[family] = {
            "attempts": len(selected),
            "status_counts": {k: sum(r.get("status") == k for r in selected) for k in ("ok", "insufficient_data", "infeasible", "uninformative", "crash")},
            "evidence_status_counts": {k: sum(r.get("evidence_status") == k for r in selected) for k in ("source_supported", "ambiguous", "model_mismatch")},
            "numerically_converged": sum(r.get("numerical_converged") is True for r in selected),
            "numerically_unresolved": sum(r.get("numerical_converged") is False for r in selected),
            "mean_error_median_all": median("mean_error_m"),
            "mean_error_distribution_all": distribution(selected, "mean_error_m"),
            "mode_error_median_all": median("mode_error_m"),
            "mode_error_distribution_all": distribution(selected, "mode_error_m"),
            "region_coverage_correct_source_count": sum(r.get("truth_region_correct_for_source_count") is True for r in selected),
            "region_coverage_denominator": sum(r.get("truth_region_correct_for_source_count") is not None for r in selected),
            "median_region_area_fraction": median("region_area_fraction"),
            "accepted_wrong_regions": sum(r.get("evidence_status") == "source_supported" and not r.get("truth_region_correct_for_source_count") for r in selected),
            "median_source_probability": median("source_probability"),
            "externality_flag_count": sum(bool(r.get("externality_flags")) for r in selected),
            "median_held_out_rmse_ug_m3": float(np.median([x["rmse_ug_m3"] for r in selected for x in r.get("held_out_checks", []) if x.get("rmse_ug_m3") is not None])) if any(x.get("rmse_ug_m3") is not None for r in selected for x in r.get("held_out_checks", [])) else None,
        }
        supported = [r for r in selected if r.get("evidence_status") == "source_supported"]
        by_family[family]["accepted_mean_error_median"] = float(np.median([r["mean_error_m"] for r in supported if r.get("mean_error_m") is not None])) if any(r.get("mean_error_m") is not None for r in supported) else None
        by_family[family]["accepted_mean_error_denominator"] = sum(r.get("mean_error_m") is not None for r in supported)
        by_family[family]["accepted_mode_error_distribution"] = distribution(supported, "mode_error_m")
        by_family[family]["accepted_within_50m"] = sum(r.get("mean_error_m") is not None and r["mean_error_m"] <= 50 for r in supported)
        by_family[family]["accepted_within_50m_denominator"] = sum(r.get("mean_error_m") is not None for r in supported)
    return {
        "attempts": len(rows),
        "status_counts": {k: sum(r.get("status") == k for r in rows) for k in ("ok", "insufficient_data", "infeasible", "uninformative", "crash")},
        "evidence_status_counts": {k: sum(r.get("evidence_status") == k for r in rows) for k in ("source_supported", "ambiguous", "model_mismatch")},
        "numerically_converged": sum(r.get("numerical_converged") is True for r in rows),
        "mean_error_distribution_all": distribution(rows, "mean_error_m"),
        "mode_error_distribution_all": distribution(rows, "mode_error_m"),
        "region_coverage_correct_source_count": sum(r.get("truth_region_correct_for_source_count") is True for r in rows),
        "region_coverage_denominator": sum(r.get("truth_region_correct_for_source_count") is not None for r in rows),
        "runtime_ms_median": distribution(rows, "runtime_ms")["median"],
        "family_summary": by_family,
    }


def run(out, seeds, split):
    out = Path(out)
    if out.exists():
        raise FileExistsError("Refusing to overwrite an existing v0.8 evidence directory")
    out.mkdir(parents=True)
    baseline_engine, baseline_models = _load_baseline()
    metadata = {
        "model_version": MODEL_VERSION,
        "protocol": PROTOCOL_VERSION,
        "split": split,
        "seeds": seeds,
        "families": FAMILIES,
        "attempted_worlds": len(seeds) * len(FAMILIES),
        "candidate_config": CONFIG,
        "candidate_source_sha256": _source_hash(),
        "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "protocol_sha256": hashlib.sha256((ROOT / "docs/ENGINE_V08_PROTOCOL.md").read_bytes()).hexdigest(),
        "python_version": sys.version,
        "numpy_version": np.__version__,
        "paired_baseline_model": "plume-robust-0.7.1",
        "paired_baseline_protocol": "UW-ENGINE-2026-07A",
        "paired_baseline_source_manifest": "evaluations/engine-v08/v07-baseline/source-manifest.json",
        "evidence_scope": "Synthetic only; no measured validation, field calibration, source responsibility, or regulatory attribution.",
    }
    (out / "metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    rows, private_truth = [], []
    for seed in seeds:
        for family in FAMILIES:
            inv, truth = _world(family, seed)
            private_truth.append(truth)
            payload = inv.model_dump_json()
            input_hash = hashlib.sha256(payload.encode()).hexdigest()
            try:
                candidate = analyze(inv)
                candidate_row = _row(candidate, truth, input_hash, "plume-robust-0.8.0")
            except Exception as exc:
                candidate_row = {"engine": "plume-robust-0.8.0", "seed": seed, "family": family, "input_sha256": input_hash, "status": "crash", "reason": f"{type(exc).__name__}: {exc}"}
            try:
                baseline_inv = baseline_models.Investigation.model_validate_json(payload)
                baseline = baseline_engine.analyze(baseline_inv)
                baseline_row = _row(baseline, truth, input_hash, "plume-robust-0.7.1")
            except Exception as exc:
                baseline_row = {"engine": "plume-robust-0.7.1", "seed": seed, "family": family, "input_sha256": input_hash, "status": "crash", "reason": f"{type(exc).__name__}: {exc}"}
            rows.extend((candidate_row, baseline_row))
    candidate_rows = [r for r in rows if r["engine"] == "plume-robust-0.8.0"]
    baseline_rows = [r for r in rows if r["engine"] == "plume-robust-0.7.1"]
    paired = []
    for candidate, baseline in zip(candidate_rows, baseline_rows):
        paired.append({
            "seed": candidate["seed"],
            "family": candidate["family"],
            "same_input_sha256": candidate["input_sha256"] == baseline["input_sha256"],
            "candidate_status": candidate.get("evidence_status"),
            "baseline_status": baseline.get("evidence_status"),
            "mean_error_difference_m": None if candidate.get("mean_error_m") is None or baseline.get("mean_error_m") is None else candidate["mean_error_m"] - baseline["mean_error_m"],
            "mode_error_difference_m": None if candidate.get("mode_error_m") is None or baseline.get("mode_error_m") is None else candidate["mode_error_m"] - baseline["mode_error_m"],
            "region_area_fraction_difference": None if candidate.get("region_area_fraction") is None or baseline.get("region_area_fraction") is None else candidate["region_area_fraction"] - baseline["region_area_fraction"],
            "candidate_region_covered": candidate.get("truth_region_coverage_any"),
            "baseline_region_covered": baseline.get("truth_region_coverage_any"),
        })
    (out / "results.json").write_text(json.dumps(rows, indent=2, allow_nan=False) + "\n")
    (out / "paired.json").write_text(json.dumps(paired, indent=2, allow_nan=False) + "\n")
    (out / "summary.json").write_text(json.dumps({
        "candidate": _summary(candidate_rows),
        "baseline": _summary(baseline_rows),
        "paired_attempts": len(paired),
        "paired_same_inputs": sum(row["same_input_sha256"] for row in paired),
        "paired_mean_error_difference_median": float(np.median([r["mean_error_difference_m"] for r in paired if r["mean_error_difference_m"] is not None])) if any(r["mean_error_difference_m"] is not None for r in paired) else None,
        "paired_mode_error_difference_median": float(np.median([r["mode_error_difference_m"] for r in paired if r["mode_error_difference_m"] is not None])) if any(r["mode_error_difference_m"] is not None for r in paired) else None,
    }, indent=2, sort_keys=True) + "\n")
    (out / "private_truth.json").write_text(json.dumps(private_truth, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=[*SPLITS, "pilot", "pilot_retry", "pilot_final", "pilot_final2"], required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    seeds = {"pilot": [8_440_000], "pilot_retry": [8_440_001], "pilot_final": [8_440_002], "pilot_final2": [8_440_003]}[args.split] if args.split.startswith("pilot") else SPLITS[args.split]
    run(args.out, seeds, args.split)
