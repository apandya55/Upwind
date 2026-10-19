"""UW-STRESS-2026-04: frozen-model challenge; evaluator truth stays private."""

import argparse
from collections import Counter
import copy
import gc
import hashlib
import json
import platform
from pathlib import Path
import resource
import shutil
import time

import numpy as np

from upwind.models import Investigation, Measurement, Point
from upwind.inference import fit, CONFIG, MODEL_VERSION
from upwind.validation import weather_bias as wb
from upwind.validation.research.cases import point, reveal
from upwind.validation.research.run import source_metrics, score_prediction

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = "UW-STRESS-2026-04"
SEEDS = tuple(range(6100000, 6100048))
EXTRA = (
    "sensor_dropout",
    "sensor_bias",
    "shared_reference_bias",
    "source_outside_domain",
    "extreme_readings",
    "shared_lineage",
)
FAMILIES = wb.FAMILIES + EXTRA


def write(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")


def fingerprints():
    result = wb.hashes()
    for path in [Path(__file__), ROOT / "docs/SEVERE_STRESS_PROTOCOL.md"]:
        result[str(path.relative_to(ROOT))] = hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
    return result


def case(family, seed):
    if family not in FAMILIES:
        raise ValueError("Unknown stress condition")
    rng = np.random.default_rng(seed + 17_000_000)
    layout = np.column_stack((rng.uniform(10, 900, 6), rng.uniform(-215, 215, 6)))
    angles = np.array([202, 246, 294, 338]) + rng.uniform(-10, 10, 4)
    original_layout, original_angles = wb.LAYOUTS["final"], wb.ANGLES["final"]
    try:
        wb.LAYOUTS["final"], wb.ANGLES["final"] = layout.tolist(), angles.tolist()
        inv, truth = wb.world(
            "characterized_nominal" if family in EXTRA else family, seed, "final"
        )
    finally:
        wb.LAYOUTS["final"], wb.ANGLES["final"] = original_layout, original_angles
    mutation = None
    if family == "sensor_dropout":
        inv.measurements = [
            m for m in inv.measurements if m.sensor_id not in {"M00", "M02", "M04"}
        ]
        mutation = {"removed_sensor_ids": ["M00", "M02", "M04"]}
    elif family == "sensor_bias":
        bias = float(rng.uniform(15, 35))
        for row in inv.measurements:
            if row.sensor_id == "M00":
                row.pm25_ug_m3 += bias
        mutation = {"sensor": "M00", "additive_bias_ug_m3": bias}
    elif family == "shared_reference_bias":
        bias = float(rng.uniform(32, 55))
        for row in inv.weather:
            row.wind_from_deg = float((row.wind_from_deg + bias) % 360)
        mutation = {
            "hidden_common_bias_deg": bias,
            "independence_claim_is_violated": True,
        }
    elif family == "source_outside_domain":
        inv.source_locations = [
            Point(**point((x, y), "final"))
            for x in (-680.0, -590.0, -500.0)
            for y in (-220.0, 0.0, 220.0)
        ]
        mutation = {"declared_source_rectangle_xy_m": [-680, -220, -500, 220]}
    elif family == "extreme_readings":
        for row in inv.measurements:
            if row.sensor_id == "M00":
                row.pm25_ug_m3 = 650.0
        mutation = {"sensor": "M00", "replaced_value_ug_m3": 650}
    elif family == "shared_lineage":
        bias = float(rng.uniform(25, 40))
        for row in inv.weather:
            if row.role == "reference":
                row.upstream_id = "instrument-A"
            else:
                row.wind_from_deg = float((row.wind_from_deg + bias) % 360)
        mutation = {"primary_shift_deg": bias, "reference_upstream_id": "instrument-A"}
    inv.name = f"SYNTHETIC severe stress {family} {seed}"
    # Revalidate changed values so normal import quality flags remain active.
    inv = Investigation.model_validate(inv.model_dump())
    truth.update(
        family=family,
        stress_protocol=PROTOCOL,
        mutation=mutation,
        layout_before_jitter_xy_m=layout.tolist(),
        angles_before_jitter_deg=angles.tolist(),
    )
    return inv, truth


def evaluate(inv, truth, prediction=False):
    started = time.perf_counter()
    row = {
        "family": truth["family"],
        "seed": truth["seed"],
        "model": MODEL_VERSION,
        "rows_loaded": len(inv.measurements),
        "raw_extreme_rows": sum(m.pm25_ug_m3 > 500 for m in inv.measurements),
        "prediction_scheduled": prediction,
    }
    try:
        fitted = fit(inv, diagnostics=True)
        row.update(
            status="fitted",
            **source_metrics(fitted, truth),
            warning=bool(fitted["diagnostics"]["predictive_warning"]),
            weather_warning=bool(fitted["meteorology"]["weather_warning"]),
            diagnostics=fitted["diagnostics"],
            meteorology=fitted["meteorology"],
            rows_used=fitted["rows_used"],
        )
        row["accepted"] = wb.accepted(row)
        row["numeric_ok"] = bool(
            np.isfinite(fitted["cell_weights"]).all()
            and (fitted["cell_weights"] >= 0).all()
            and abs(sum(fitted["cell_weights"]) - 1) < 1e-9
            and np.isfinite(fitted["source_probability"])
            and 0 <= fitted["source_probability"] <= 1
        )
        row["analysis_wall_ms"] = 1000 * (time.perf_counter() - started)
        if prediction:
            t = time.perf_counter()
            reveal(truth)  # Only after fitting. Never appended to fitted inputs.
            targets = [
                Measurement(
                    sensor_id=f"stress-unseen-{j}",
                    timestamp=truth["last_timestamp"],
                    origin="synthetic",
                    pm25_ug_m3=float(value),
                    uncertainty_ug_m3=float(truth["future_sigma"][12 + j]),
                    **point(xy, "final"),
                )
                for j, (xy, value) in enumerate(
                    zip(truth["target_xy"], truth["target_outcomes"])
                )
            ]
            try:
                row["prediction"] = {
                    "status": "scored",
                    **score_prediction(fitted, targets, truth["target_outcomes"]),
                }
            except Exception as exc:
                row["prediction"] = {
                    "status": "crash",
                    "reason": f"{type(exc).__name__}: {exc}",
                }
            row["prediction_wall_ms"] = 1000 * (time.perf_counter() - t)
    except ValueError as exc:
        row.update(status="refused", reason=str(exc))
    except Exception as exc:
        row.update(status="crash", reason=f"{type(exc).__name__}: {exc}")
    row["wall_ms"] = 1000 * (time.perf_counter() - started)
    row["process_peak_rss_mib"] = (
        resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    )
    return row


def freeze(out):
    out.mkdir(parents=True, exist_ok=False)
    hashes = fingerprints()
    write(
        out / "freeze.json",
        {
            "protocol": PROTOCOL,
            "model": MODEL_VERSION,
            "source_hashes": hashes,
            "model_configuration": copy.deepcopy(CONFIG),
            "seeds": list(SEEDS),
            "families": list(FAMILIES),
            "python": platform.python_version(),
            "numpy": np.__version__,
        },
    )
    for name in hashes:
        destination = out / "source" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, destination)


def run(out, shard, preflight):
    frozen = json.loads((out / "freeze.json").read_text())
    before = fingerprints()
    assert before == frozen["source_hashes"], (
        "Scientific/evaluator source changed after freeze"
    )
    assert CONFIG == frozen["model_configuration"], (
        "Runtime model configuration changed"
    )
    folder = out / ("preflight" if preflight else f"shard-{shard}")
    folder.mkdir(parents=True, exist_ok=False)
    seeds = [6101000, 6101001] if preflight else SEEDS[shard::4]
    families = (
        ["characterized_nominal", "shared_reference_bias", "source_outside_domain"]
        if preflight
        else FAMILIES
    )
    write(
        folder / "metadata.json",
        {
            "protocol": PROTOCOL,
            "source_hashes_before": before,
            "seeds": list(seeds),
            "families": list(families),
            "role": "development preflight, not final"
            if preflight
            else "fresh frozen-model challenge",
            "model_configuration": CONFIG,
        },
    )
    started = time.perf_counter()
    statuses = Counter()
    prediction_statuses = Counter()
    for seed in seeds:
        for family in families:
            inv, truth = case(family, seed)
            write(
                folder / f"input-{family}-{seed}.json",
                {"investigation": inv.model_dump(), "private_evaluator_truth": truth},
            )
            row = evaluate(inv, truth, prediction=preflight or seed < SEEDS[0] + 12)
            with (folder / "results.jsonl").open("a") as file:
                file.write(json.dumps(row, allow_nan=False) + "\n")
            statuses[row["status"]] += 1
            if row["prediction_scheduled"]:
                prediction_statuses[
                    row.get("prediction", {}).get("status", "unavailable")
                ] += 1
            print(seed, family, row["status"], row.get("accepted"), flush=True)
            del inv, truth, row
            gc.collect()
    after = fingerprints()
    write(
        folder / "completion.json",
        {
            "source_hashes_after": after,
            "source_unchanged": before == after,
            "configuration_unchanged": CONFIG == frozen["model_configuration"],
            "counts": dict(statuses),
            "predictions": dict(prediction_statuses),
            "seconds": time.perf_counter() - started,
            "process_peak_rss_mib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            / 1024,
        },
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["freeze", "preflight", "run"])
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--shard", type=int, choices=range(4), default=0)
    args = parser.parse_args()
    if args.mode == "freeze":
        freeze(args.out)
    else:
        run(args.out, args.shard, args.mode == "preflight")


if __name__ == "__main__":
    main()
