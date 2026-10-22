"""Append-only externality stress runner for UW-ENGINE-2026-07A.

This runner creates synthetic worlds with fresh seed families and records only
observable analysis output in the result rows. It is intentionally small: the
protocol requires a separately reviewed/frozen generator before the final split
is run, so this development harness must not be treated as final evidence.
"""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from upwind.engine import analyze
from upwind.fixtures import synthetic_case
from upwind.inference import CONFIG, MODEL_VERSION, PROTOCOL_VERSION
from upwind.numerics import projector, plume


SPLITS = {
    "development": range(8_110_000, 8_110_016),
    "calibration": range(8_210_000, 8_210_016),
    "final": range(8_310_000, 8_310_032),
}
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


def _world(family, seed):
    case = "multiple_sources" if family == "two_sources" else "identifiable"
    inv, truth = synthetic_case(case, seed)
    rng = np.random.default_rng(seed + 73_000_000)
    ordered = sorted(inv.measurements, key=lambda row: row.timestamp)
    if family == "humidity_response":
        for row in inv.measurements:
            row.humidity_percent = 88.0 if row.sensor_id == "M1" else 45.0
            if row.sensor_id == "M1":
                # A synthetic sensor response covaries with humidity. This is
                # evaluator-only perturbation, not an inferred correction.
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
                wind = next(
                    w.wind_from_deg
                    for w in inv.weather
                    if w.timestamp == row.timestamp
                )
                # The release doubles at a known step; the added concentration
                # follows the same source geometry, not a uniform background.
                row.pm25_ug_m3 += float(
                    plume([receptor], [-650.0, 250.0], 5000.0, 2.3, wind)[0]
                )
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
    return inv, truth


def _source_hash():
    root = Path(__file__).resolve().parents[1]
    paths = sorted((root / "backend/upwind").rglob("*.py"))
    digest = hashlib.sha256()
    for path in paths:
        digest.update(str(path.relative_to(root)).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def run(out, split, limit=None, families=None):
    out = Path(out)
    if out.exists():
        raise FileExistsError("Refusing to overwrite an existing v0.7 evidence directory")
    out.mkdir(parents=True)
    seeds = list(SPLITS[split])[:limit] if limit else list(SPLITS[split])
    families = tuple(families or FAMILIES)
    metadata = {
        "model_version": MODEL_VERSION,
        "protocol": PROTOCOL_VERSION,
        "split": split,
        "seeds": seeds,
        "families": families,
        "config": CONFIG,
        "source_sha256": _source_hash(),
        "evidence": "synthetic development/calibration/final harness; no field validation",
    }
    (out / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    rows = []
    private_truth = []
    for seed in seeds:
        for family in families:
            inv, truth = _world(family, seed)
            private_truth.append(truth)
            try:
                result = analyze(inv)
                row = {
                    "split": split,
                    "seed": seed,
                    "family": family,
                    "status": result["status"],
                    "evidence_status": result.get("evidence_status"),
                    "source_probability": result.get("source_probability"),
                    "warnings": result.get("warnings", []),
                    "externality_flags": (result.get("observability") or {})
                    .get("externalities", {})
                    .get("flags", []),
                    "material_competing_pair": (result.get("observability") or {})
                    .get("source_count", {})
                    .get("material_competing_pair", False),
                    "diagnostic_unavailable": (result.get("observability") or {})
                    .get("source_count", {})
                    .get("diagnostic_unavailable", False),
                }
            except Exception as exc:  # retain a visible denominator row
                row = {
                    "split": split,
                    "seed": seed,
                    "family": family,
                    "status": "crash",
                    "reason": f"{type(exc).__name__}: {exc}",
                }
            rows.append(row)
    (out / "results.json").write_text(json.dumps(rows, indent=2, allow_nan=False) + "\n")
    # Truth stays in a separate evaluator-only file and is never consumed by
    # analyze. It is not written to a final directory unless a reviewer chooses
    # to preserve it under the protocol's private-evaluator rules.
    (out / "private_truth.json").write_text(
        json.dumps(private_truth, indent=2, sort_keys=True) + "\n"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=SPLITS, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--families", nargs="+", choices=FAMILIES)
    args = parser.parse_args()
    run(args.out, args.split, args.limit, args.families)
