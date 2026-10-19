"""Held-out synthetic science and leakage-controlled follow-up experiments."""

import math
import time
import numpy as np
from ..engine import analyze, ensemble
from ..numerics import plume
from ..models import Measurement
from .cases import CASES, make_case, point, predict_truth


def entropy(weights):
    p = np.asarray(weights)
    return float(-np.sum(p[p > 0] * np.log(p[p > 0])))


def predictions(fit, points, speed=2.3, direction=270.0):
    xy = np.array(
        [fit["projection"].transform(p["longitude"], p["latitude"]) for p in points]
    )
    c = np.asarray(fit["configs"])
    groups = c[:, 0].astype(int)
    p = c[:, 2, None] + plume(
        xy[None, :, :],
        fit["source_xy"][groups, None, :],
        c[:, 1, None],
        speed * c[:, 4, None],
        direction + c[:, 3, None],
    )
    return fit["weights"] @ p


def location_metrics(weights, source_points, truth, tr):
    truth_lonlat = point(truth["source_xy"])
    truth_xy = np.array(
        tr.transform(truth_lonlat["longitude"], truth_lonlat["latitude"])
    )
    coords = np.array([tr.transform(p.longitude, p.latitude) for p in source_points])
    order = np.argsort(-weights, kind="stable")
    chosen = order[
        : min(len(order), int(np.searchsorted(np.cumsum(weights[order]), 0.9)) + 1)
    ]
    error = float(np.linalg.norm(coords[int(np.argmax(weights))] - truth_xy))
    ties = np.flatnonzero(np.max(weights) - np.asarray(weights) <= 1e-12)
    tied_errors = np.linalg.norm(coords[ties] - truth_xy, axis=1)
    return {
        "map_tie_count": len(ties),
        "map_min_error_m": float(tied_errors.min()),
        "map_max_error_m": float(tied_errors.max()),
        "map_unique": bool(len(ties) == 1),
        "localization_error_m": error,
        "entropy_nats": entropy(weights),
        "max_weight": float(np.max(weights)),
        "grid_points_90": len(chosen),
        "truth_in_90": None
        if truth["source_index"] is None
        else bool(truth["source_index"] in chosen),
        "wrong_and_sharp": bool(error > 100 and max(weights) > 0.9),
        "wrong_map_grid": bool(
            truth["source_index"] is not None
            and len(ties) == 1
            and int(np.argmax(weights)) != truth["source_index"]
        ),
    }


def scientific_runs(seeds=range(220000, 220040), progress=print):
    records = []
    for case in CASES:
        for seed in seeds:
            inv, truth = make_case(case, seed)
            started = time.perf_counter()
            row = {
                "case": case,
                "seed": seed,
                "evidence": "synthetic",
                "on_grid_truth": truth["source_index"] is not None,
            }
            try:
                result = analyze(inv)
                row.update(
                    status=result["status"],
                    reason=result.get("reason"),
                    warnings=result["warnings"],
                )
                if result.get("sources"):
                    fit = ensemble(inv)
                    row.update(
                        location_metrics(
                            fit["location_weights"],
                            inv.source_locations,
                            truth,
                            fit["projection"],
                        )
                    )
                    row["mismatch_warning"] = any(
                        "MODEL MISMATCH" in w for w in result["warnings"]
                    )
                    held_id = inv.measurements[-1].sensor_id
                    training = inv.model_copy(deep=True)
                    held = [m for m in training.measurements if m.sensor_id == held_id]
                    training.measurements = [
                        m for m in training.measurements if m.sensor_id != held_id
                    ]
                    try:
                        trained = ensemble(training)
                        estimate = predictions(trained, [m.model_dump() for m in held])
                        row["held_out_rmse_ug_m3"] = float(
                            np.sqrt(
                                np.mean(
                                    (estimate - np.array([m.pm25_ug_m3 for m in held]))
                                    ** 2
                                )
                            )
                        )
                    except ValueError as e:
                        row["held_out_unavailable"] = str(e)
            except Exception as e:
                row.update(status="crash", exception=type(e).__name__, reason=str(e))
            row["wall_ms"] = round((time.perf_counter() - started) * 1000, 3)
            records.append(row)
        progress(f"science: {case}: {len(seeds)} completed", flush=True)
    return records


def followup_runs(seeds=range(220000, 220040), progress=print):
    records = []
    for case in ["strong_signal", "weak_signal"]:
        for mismatch in [False, True]:
            for seed in seeds:
                inv, truth = make_case(case, seed, planning=True)
                result = analyze(inv)
                if not result.get("sources"):
                    records.append(
                        {
                            "case": case,
                            "seed": seed,
                            "status": "refused",
                            "reason": result.get("reason"),
                        }
                    )
                    continue
                initial = ensemble(inv)
                base = location_metrics(
                    initial["location_weights"],
                    inv.source_locations,
                    truth,
                    initial["projection"],
                )
                # Lock choices for every method BEFORE outcomes are generated.
                plans = [
                    (p["method"], list(p["site_ids"]))
                    for p in result["plans"]
                    if not p["method"].startswith("Random")
                ]
                from ..engine import eligible_indices, select_plan

                ids = eligible_indices(inv)
                for j in range(20):
                    choices = select_plan(
                        inv,
                        "random",
                        lambda _: 0,
                        ids,
                        np.random.default_rng(inv.settings.seed + j),
                    )
                    plans.append(
                        (f"Random seed {seed + j}", [inv.sites[i].id for i in choices])
                    )
                locked = tuple((name, tuple(selected)) for name, selected in plans)
                # Joint errors at candidates and independent held-out targets,
                # conditioned only inside the evaluator on hidden initial field.
                candidates = truth["candidate_xy"]
                held_xy = (
                    [(-50, 0), (50, 30), (250, 0)]
                    if case == "strong_signal"
                    else [(700, 500), (800, 400), (900, 600)]
                )
                all_xy = np.array(candidates + held_xy)
                rng = np.random.default_rng(seed + 990000)

                def kernel(a, b, length=150, amplitude=1):
                    return amplitude * np.exp(
                        -np.linalg.norm(a[:, None, :] - b[None, :, :], axis=-1) / length
                    )

                initial_xy = np.array(truth["initial_xy"])
                if mismatch:
                    mean = np.zeros(len(all_xy))
                    cov = kernel(all_xy, all_xy, 450, 9) + np.eye(len(all_xy)) * 16
                else:
                    k_ii = kernel(initial_xy, initial_xy)
                    k_ci = kernel(all_xy, initial_xy)
                    mean = k_ci @ np.linalg.solve(
                        k_ii, np.asarray(truth["initial_spatial_error"])
                    )
                    cov = (
                        kernel(all_xy, all_xy)
                        - k_ci @ np.linalg.solve(k_ii, k_ci.T)
                        + np.eye(len(all_xy)) * 2
                    )
                errors = rng.multivariate_normal(mean, (cov + cov.T) * 0.5)
                observed = np.maximum(0, predict_truth(all_xy, truth) + errors)
                outcomes = {f"C{i:02}": observed[i] for i in range(len(candidates))}
                held_values = observed[len(candidates) :]
                prior_pred = predictions(initial, [point(p) for p in held_xy])
                prior_rmse = float(np.sqrt(np.mean((prior_pred - held_values) ** 2)))
                assert (
                    tuple((name, tuple(selected)) for name, selected in plans) == locked
                )
                for method, selected in plans:
                    updated = inv.model_copy(deep=True)
                    for id in selected:
                        site = next(s for s in inv.sites if s.id == id)
                        updated.measurements.append(
                            Measurement(
                                sensor_id="followup-" + id,
                                timestamp=inv.measurements[0].timestamp,
                                latitude=site.latitude,
                                longitude=site.longitude,
                                pm25_ug_m3=float(outcomes[id]),
                                uncertainty_ug_m3=1,
                                origin="synthetic",
                            )
                        )
                    try:
                        fitted = ensemble(updated)
                        metrics = location_metrics(
                            fitted["location_weights"],
                            updated.source_locations,
                            truth,
                            fitted["projection"],
                        )
                        posterior_pred = predictions(
                            fitted, [point(p) for p in held_xy]
                        )
                        rmse = float(
                            np.sqrt(np.mean((posterior_pred - held_values) ** 2))
                        )
                        records.append(
                            {
                                "case": case,
                                "error_model": "mismatched" if mismatch else "matched",
                                "seed": seed,
                                "method": method,
                                "site_ids": selected,
                                "status": "ok",
                                **metrics,
                                "prior_entropy": base["entropy_nats"],
                                "entropy_reduction": base["entropy_nats"]
                                - metrics["entropy_nats"],
                                "prior_localization_error_m": base[
                                    "localization_error_m"
                                ],
                                "localization_improvement_m": base[
                                    "localization_error_m"
                                ]
                                - metrics["localization_error_m"],
                                "prior_predictive_rmse": prior_rmse,
                                "posterior_predictive_rmse": rmse,
                                "predictive_improvement": prior_rmse - rmse,
                            }
                        )
                    except Exception as e:
                        records.append(
                            {
                                "case": case,
                                "error_model": "mismatched" if mismatch else "matched",
                                "seed": seed,
                                "method": method,
                                "status": "crash",
                                "reason": str(e),
                            }
                        )
            progress(
                f"follow-up: {case}, {'mismatched' if mismatch else 'matched'} errors: {len(seeds)} seeds × 23 methods",
                flush=True,
            )
    return records


def wilson(success, total):
    if not total:
        return None
    p = success / total
    z = 1.96
    d = 1 + z * z / total
    center = (p + z * z / (2 * total)) / d
    radius = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total**2)) / d
    return [max(0, center - radius), min(1, center + radius)]
