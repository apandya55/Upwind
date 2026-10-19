"""Development-only model, selection, planner-budget and bounded-resource probes.

No final or calibration worlds are accepted. These checks assess sensitivity,
not independent empirical reliability; outputs remain append-only.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
from itertools import combinations
import json
import os
from pathlib import Path
import platform
import resource
import subprocess
import sys
import time

import numpy as np
from scipy.stats import spearmanr

from upwind.design import design_score
from upwind.inference import CONFIG, MODEL_VERSION, fit
from upwind.models import Measurement
from upwind.quality import measurement_quality, select_rows
from upwind.validation.overhaul import (
    SPLITS,
    lonlat,
    make_world,
    new_predictive,
    predictive_scores,
    reveal_future,
    source_metrics,
    true_mean,
)

ROOT = Path(__file__).resolve().parents[1]


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def hashes():
    paths = list((ROOT / "backend/upwind").rglob("*.py")) + [
        Path(__file__).resolve(),
        ROOT / "docs/ENGINE_EVALUATION_PROTOCOL.md",
    ]
    return {
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(paths)
    }


def targets(state):
    return [
        Measurement(
            sensor_id=f"T{i}",
            timestamp=state["stamps"][-1],
            pm25_ug_m3=float(value),
            uncertainty_ug_m3=float(sigma),
            origin="synthetic",
            **lonlat(xy, "development"),
        )
        for i, (xy, value, sigma) in enumerate(
            zip(state["target_xy"], state["target_outcomes"], state["target_sigma"])
        )
    ]


def evaluate_fit(fitted, state):
    means, covariances = new_predictive(fitted, targets(state))
    return {
        "source": source_metrics(fitted, state),
        "target_prediction": predictive_scores(
            fitted["weights"], means, covariances, state["target_outcomes"]
        ),
        "loaded": fitted["rows_loaded"],
        "usable": fitted["rows_input"],
        "excluded": fitted["rows_excluded"],
        "fitted": fitted["rows_used"],
    }


def model_ablations(seeds):
    records = []
    for family in (
        "background_only",
        "weak_signal",
        "strong_signal",
        "direction_bias",
        "two_sources",
        "correlated_errors",
        "episodic",
    ):
        for seed in seeds:
            inv, state = make_world(family, seed, "development")
            state = reveal_future(state)
            for kind in (
                "full_model",
                "background_only",
                "without_background_family",
                "without_wind_uncertainty",
            ):
                start = time.perf_counter()
                fitted = fit(
                    inv,
                    diagnostics=False,
                    background_only=kind == "background_only",
                    wind_uncertainty=kind != "without_wind_uncertainty",
                )
                if kind == "without_background_family":
                    # Family removal changes the mixture calculations, not labels.
                    weights = fitted["weights"].copy()
                    weights[0] = 0
                    weights /= weights.sum()
                    fitted = dict(fitted, weights=weights, source_probability=1.0)
                records.append(
                    {
                        "family": family,
                        "seed": seed,
                        "ablation": kind,
                        "status": "retained",
                        "wall_ms": (time.perf_counter() - start) * 1000,
                        **evaluate_fit(fitted, state),
                    }
                )
        print(f"model ablation {family}: complete", flush=True)
    return records


def dense_world(count, rare_episode):
    """Independent dense development transport with explicit temporal field.

    A rare +20 ug/m3 shared regional pulse at one epoch deliberately violates
    steady release/background assumptions. Its retention is not truth recovery.
    """
    inv, state = make_world("strong_signal", 410010, "development")
    state = reveal_future(state)
    rng = np.random.default_rng(410010 + count)
    coords = np.asarray(state["monitor_xy"])
    number_sensors = len(coords)
    sensor = np.arange(count) % number_sensors
    epoch = np.arange(count) // number_sensors
    relative_time = epoch / max(1, epoch.max())
    xy = coords[sensor]
    dt = np.abs(relative_time[:, None] - relative_time[None]) * 1080
    distance = np.linalg.norm(xy[:, None] - xy[None], axis=-1)
    covariance = 0.7**2 * np.exp(-distance / 180 - dt / 600) + np.eye(count) * 1e-10
    field = np.linalg.cholesky(covariance) @ rng.normal(size=count)
    bias = rng.normal(0, 0.7, number_sensors)[sensor]
    mean = true_mean(xy, relative_time * 3, state)
    rare = (
        epoch == max(1, int(epoch.max() * 0.43))
        if rare_episode
        else np.zeros(count, dtype=bool)
    )
    observed = np.maximum(0, mean + rare * 20 + field + bias + rng.normal(0, 1, count))
    start = datetime.fromisoformat(state["stamps"][0])
    rows, rare_keys = [], []
    for i in range(count):
        stamp = (start + timedelta(seconds=float(relative_time[i] * 1080))).isoformat()
        row = Measurement(
            sensor_id=f"M{sensor[i]:02}",
            timestamp=stamp,
            pm25_ug_m3=float(observed[i]),
            uncertainty_ug_m3=1.0,
            origin="synthetic",
            **lonlat(xy[i], "development"),
        )
        rows.append(row)
        if rare[i]:
            rare_keys.append((row.sensor_id, row.timestamp))
    inv.measurements = rows
    return inv, state, rare_keys


def selection_ablations():
    records = []
    for count in (24, 48, 96, 192, 512):
        for rare in (False, True):
            inv, state, rare_keys = dense_world(count, rare)
            usable, _ = measurement_quality(inv)
            fits = {}
            for limit in (40, 128, 256, 512):
                for seed in (0, 1, 2):
                    changed = inv.model_copy(deep=True)
                    changed.settings.inference_limit = limit
                    changed.settings.selection_seed = seed
                    selected = select_rows(usable, limit, seed)
                    row_keys = [(r.sensor_id, r.timestamp) for r in selected]
                    fingerprint = hashlib.sha256(
                        json.dumps(row_keys).encode()
                    ).hexdigest()
                    if fingerprint not in fits:
                        started = time.perf_counter()
                        fitted = fit(changed, diagnostics=False)
                        fits[fingerprint] = {
                            **evaluate_fit(fitted, state),
                            "wall_ms": (time.perf_counter() - started) * 1000,
                        }
                    records.append(
                        {
                            "loaded_rows": count,
                            "rare_episode": rare,
                            "inference_limit": limit,
                            "selection_seed": seed,
                            "selected_keys_sha256": fingerprint,
                            "rare_rows_total": len(rare_keys),
                            "rare_rows_retained": sum(
                                tuple(k) in set(row_keys) for k in rare_keys
                            ),
                            "full_data": len(selected) == count,
                            **fits[fingerprint],
                        }
                    )
            print(f"selection {count} rows rare={rare}: complete", flush=True)
    # Add paired deviations from each fixture's full-data calculation.
    for row in records:
        reference = next(
            r
            for r in records
            if r["loaded_rows"] == row["loaded_rows"]
            and r["rare_episode"] == row["rare_episode"]
            and r["inference_limit"] == 512
            and r["selection_seed"] == 0
        )
        row["vs_full_source_probability"] = (
            row["source"]["source_probability"]
            - reference["source"]["source_probability"]
        )
        row["vs_full_map_error_m"] = (
            row["source"]["localization_error_m"]
            - reference["source"]["localization_error_m"]
        )
        row["vs_full_target_rmse"] = (
            row["target_prediction"]["rmse_ug_m3"]
            - reference["target_prediction"]["rmse_ug_m3"]
        )
    return records


def eligible(inv, fitted):
    return sorted(
        [
            i
            for i, s in enumerate(inv.sites)
            if s.kind == "candidate"
            and s.allowed
            and s.power
            and s.access
            and inv.settings.window in s.windows
            and s.cost <= inv.settings.budget
            and fitted["candidate_supported"][i]
        ],
        key=lambda i: inv.sites[i].id,
    )


def planner_ablations(seeds):
    records = []
    for family in ("strong_signal", "weak_signal", "direction_bias"):
        for seed in seeds:
            inv, state = make_world(family, seed, "development")
            fitted = fit(inv, diagnostics=False)
            available = eligible(inv, fitted)
            subsets = [
                tuple(s)
                for k in range(inv.settings.equipment_limit + 1)
                for s in combinations(available, k)
                if sum(inv.sites[i].cost for i in s) <= inv.settings.budget + 1e-9
            ]
            stamp = max(r.timestamp for r in inv.measurements)

            def predictive(indices):
                return fitted["predictive"](
                    [inv.sites[i] for i in indices],
                    timestamps=[stamp] * len(indices),
                    sensor_ids=["followup-" + inv.sites[i].id for i in indices],
                    uncertainties=[inv.settings.noise_ug_m3] * len(indices),
                )

            locked = []
            for component_budget in (128, 256, 512):
                for sample_budget in (128, 512):
                    scorer, metadata = design_score(
                        fitted["weights"],
                        fitted["groups"],
                        predictive,
                        seed=inv.settings.seed,
                        max_components=component_budget,
                        samples=sample_budget,
                        component_keys=fitted["component_keys"],
                    )
                    started = time.perf_counter()
                    scores = [scorer(list(subset)) for subset in subsets]
                    order = sorted(
                        range(len(subsets)),
                        key=lambda j: (
                            -scores[j],
                            sum(inv.sites[i].cost for i in subsets[j]),
                            subsets[j],
                        ),
                    )
                    best = order[0]
                    locked.append(
                        {
                            "component_budget": component_budget,
                            "sample_budget": sample_budget,
                            "selected": list(subsets[best]),
                            "site_ids": [inv.sites[i].id for i in subsets[best]],
                            "score_nats": scores[best],
                            "all_subset_scores": scores,
                            "top5_site_ids": [
                                [inv.sites[i].id for i in subsets[j]] for j in order[:5]
                            ],
                            "planner_numerics": metadata,
                            "search_wall_ms": (time.perf_counter() - started) * 1000,
                        }
                    )
            lock_hash = hashlib.sha256(
                json.dumps(
                    [
                        (r["component_budget"], r["sample_budget"], r["site_ids"])
                        for r in locked
                    ]
                ).encode()
            ).hexdigest()
            # All acquisition choices are frozen before accessing hidden outcomes.
            state = reveal_future(state)
            outcomes = {
                f"C{i:02}": v for i, v in enumerate(state["candidate_outcomes"])
            }
            sigma = {f"C{i:02}": v for i, v in enumerate(state["candidate_sigma"])}
            base_scores = locked[0]["all_subset_scores"]
            base_plan = set(locked[0]["site_ids"])
            cache = {}
            for row in locked:
                selected = tuple(row.pop("selected"))
                if selected not in cache:
                    updated = inv.model_copy(deep=True)
                    for i in selected:
                        site = inv.sites[i]
                        updated.measurements.append(
                            Measurement(
                                sensor_id="followup-" + site.id,
                                timestamp=stamp,
                                pm25_ug_m3=float(outcomes[site.id]),
                                uncertainty_ug_m3=float(sigma[site.id]),
                                origin="synthetic",
                                latitude=site.latitude,
                                longitude=site.longitude,
                            )
                        )
                    cache[selected] = evaluate_fit(
                        fit(updated, diagnostics=False), state
                    )
                correlation = spearmanr(base_scores, row["all_subset_scores"]).statistic
                row.update(
                    family=family,
                    seed=seed,
                    split="development",
                    locked_plan_sha256=lock_hash,
                    feasible_subsets=len(subsets),
                    rank_correlation_vs_default=float(correlation)
                    if np.isfinite(correlation)
                    else None,
                    plan_overlap_vs_default=len(base_plan.intersection(row["site_ids"]))
                    / max(1, len(base_plan.union(row["site_ids"]))),
                    realized=cache[selected],
                )
                records.append(row)
            print(f"planner resolution {family} {seed}: complete", flush=True)
    return records


def resource_child(size, limit):
    # This is an explicit process ceiling, not a claim about actual memory use.
    ceiling = 2 * 1024**3
    resource.setrlimit(resource.RLIMIT_AS, (ceiling, ceiling))
    from upwind.validation.resources import scale_case
    from upwind.engine import analyze

    started = time.perf_counter()
    inv = scale_case(size)
    inv.settings.inference_limit = limit
    result = analyze(inv)
    hwm = next(
        (
            float(line.split()[1]) / 1024
            for line in Path("/proc/self/status").read_text().splitlines()
            if line.startswith("VmHWM:")
        ),
        None,
    )
    return {
        "status": result["status"],
        "size": size,
        "inference_limit": limit,
        "loaded_measurements": len(inv.measurements),
        "weather_rows": len(inv.weather),
        "sites": len(inv.sites),
        "source_anchors": len(inv.source_locations),
        "fitted_rows": result.get("rows_used"),
        "scenario_count": result.get("scenario_count"),
        "wall_ms": (time.perf_counter() - started) * 1000,
        "peak_rss_mib": hwm,
        "address_space_ceiling_mib": 2048,
        "planner_numerics": result.get("planning_diagnostics"),
        "finite_scores": all(np.isfinite(p["score"]) for p in result.get("plans", [])),
    }


def resources():
    records = []
    for size in (100, 1000, 10000):
        for limit in (128, 512):
            command = [
                sys.executable,
                str(Path(__file__).resolve()),
                "--resource-child",
                str(size),
                "--inference-limit",
                str(limit),
            ]
            started = time.perf_counter()
            try:
                proc = subprocess.run(
                    command,
                    cwd=ROOT,
                    env={
                        **os.environ,
                        "OPENBLAS_NUM_THREADS": "1",
                        "OMP_NUM_THREADS": "1",
                    },
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                row = (
                    json.loads(proc.stdout)
                    if proc.returncode == 0
                    else {
                        "status": "child_failure",
                        "returncode": proc.returncode,
                        "stderr": proc.stderr[-4000:],
                        "stdout": proc.stdout[-1000:],
                    }
                )
            except subprocess.TimeoutExpired:
                row = {"status": "timeout", "timeout_seconds": 30}
            except Exception as exc:
                row = {
                    "status": "runner_failure",
                    "reason": f"{type(exc).__name__}: {exc}",
                }
            row.update(
                size=size,
                inference_limit=limit,
                command=command,
                subprocess_wall_seconds=time.perf_counter() - started,
            )
            records.append(row)
            print(f"resource {size} limit={limit}: {row['status']}", flush=True)
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    parser.add_argument(
        "--phase",
        choices=("all", "model", "selection", "planner", "resources"),
        default="all",
    )
    parser.add_argument("--limit-seeds", type=int, default=2)
    parser.add_argument("--resource-child", type=int)
    parser.add_argument("--inference-limit", type=int, default=128)
    args = parser.parse_args()
    if args.resource_child is not None:
        print(
            json.dumps(
                resource_child(args.resource_child, args.inference_limit),
                allow_nan=False,
            )
        )
        return
    if args.out is None or not 1 <= args.limit_seeds <= 12:
        parser.error("--out and between1and12 development seeds required")
    if args.out.exists() and any(args.out.iterdir()):
        parser.error("Output must be empty; preserve previous numerical results")
    args.out.mkdir(parents=True, exist_ok=True)
    before = hashes()
    seeds = list(SPLITS["development"])[: args.limit_seeds]
    metadata = {
        "evidence": "development-used sensitivity analysis; no final worlds or field validation",
        "model_version": MODEL_VERSION,
        "protocol": "UW-OVERHAUL-2026-01",
        "seeds": seeds,
        "phase": args.phase,
        "configuration": CONFIG,
        "source_hashes_before": before,
        "command": sys.argv,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "utc": datetime.now(timezone.utc).isoformat(),
        "blas_threads": os.environ.get("OPENBLAS_NUM_THREADS"),
    }
    write(args.out / "metadata.json", metadata)
    for phase, runner in [
        ("model", lambda: model_ablations(seeds)),
        ("selection", selection_ablations),
        ("planner", lambda: planner_ablations(seeds)),
        ("resources", resources),
    ]:
        if args.phase in ("all", phase):
            write(args.out / f"{phase}.json", runner())
    metadata["source_hashes_after"] = hashes()
    metadata["sources_unchanged"] = before == metadata["source_hashes_after"]
    write(args.out / "metadata.json", metadata)


if __name__ == "__main__":
    main()
