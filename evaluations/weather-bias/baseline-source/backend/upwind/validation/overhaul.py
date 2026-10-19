"""Independent continuous-source challenge, UW-OVERHAUL-2026-01.

Truth is evaluator-only. This module is never imported by inference or planning.
Run --split development before freezing production and running --split final.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
import hashlib
import importlib
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import resource
import sys
import time

import numpy as np
from scipy.special import gammaln, logsumexp, ndtr
from scipy.stats import norm
from pyproj import CRS, Transformer

from ..models import (
    Assumptions,
    Investigation,
    Measurement,
    Point,
    Settings,
    Site,
    Weather,
)

PROTOCOL = "UW-OVERHAUL-2026-01"
SPLITS = {
    "development": range(410000, 410012),
    "calibration": range(510000, 510024),
    "final": range(610000, 610040),
}
FAMILIES = (
    "background_only",
    "weak_signal",
    "strong_signal",
    "direction_bias",
    "two_sources",
    "boundary",
    "correlated_errors",
    "episodic",
    "missingness",
    "unsupported_weather",
)
PLANNER_FAMILIES = {"strong_signal", "weak_signal", "direction_bias"}
BOUNDS = (-450.0, -220.0, -80.0, 220.0)
ROOT = Path(__file__).resolve().parents[3]


def write(path, obj):
    path.write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")


def lonlat(xy, split):
    """Independent evaluator projection; no production coordinate helper."""
    latitude = {"development": 52.0, "calibration": 36.0, "final": 41.0}[split]
    longitude = {"development": 0.0, "calibration": 15.0, "final": -75.0}[split]
    crs = CRS.from_proj4(
        f"+proj=aeqd +lat_0={latitude} +lon_0={longitude} +datum=WGS84 +units=m"
    )
    inverse = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
    lon, lat = inverse.transform(float(xy[0]), float(xy[1]))
    return {"latitude": float(lat), "longitude": float(lon)}


def transport(points, source, strength, speed, wind_from, split):
    """Flux-normalized stretched plume with intercepted widths and wind averaging.

    This intentionally shares neither kernel nor growth parameterization with
    production. It remains a simplified, stationary open-terrain transport model.
    """
    points = np.asarray(points, dtype=float).reshape(-1, 2)
    delta = points - np.asarray(source, dtype=float)
    exponent = {"development": 2.0, "calibration": 2.2, "final": 1.65}[split]
    lateral_growth, vertical_growth = {
        "development": (0.095, 0.065),
        "calibration": (0.11, 0.075),
        "final": (0.13, 0.055),
    }[split]
    result = np.zeros(len(points))
    for offset in (-4.0, -2.0, 0.0, 2.0, 4.0):
        angle = math.radians((wind_from + offset) % 360)
        down = -delta[:, 0] * math.sin(angle) - delta[:, 1] * math.cos(angle)
        cross = delta[:, 0] * math.cos(angle) - delta[:, 1] * math.sin(angle)
        active = down > 0
        x = np.maximum(down, 0)
        sy = (8 + lateral_growth * x) / (1 + x / 700) ** 0.22
        sz = (4 + vertical_growth * x) / (1 + x / 600) ** 0.12
        lateral = np.exp(-(np.abs(cross / sy) ** exponent))
        lateral *= exponent / (2 * sy * math.exp(gammaln(1 / exponent)))
        vertical = np.exp(-0.5 * ((2 - 7) / sz) ** 2) + np.exp(
            -0.5 * ((2 + 7) / sz) ** 2
        )
        vertical /= math.sqrt(2 * math.pi) * sz
        result += active * strength / speed * lateral * vertical / 5
    return result


def layout(split):
    return np.asarray(
        {
            "development": [
                (40, -90),
                (40, 0),
                (40, 90),
                (240, -120),
                (240, 60),
                (500, -60),
                (700, 150),
            ],
            "calibration": [
                (60, -120),
                (100, 30),
                (220, 180),
                (350, -70),
                (540, 90),
                (810, -180),
            ],
            "final": [
                (70, 45),
                (160, -160),
                (310, 125),
                (470, -35),
                (680, 250),
                (920, -210),
            ],
        }[split],
        dtype=float,
    )


def make_world(family, seed, split):
    """Return ordinary inputs and a separate hidden evaluator state."""
    if family not in FAMILIES or split not in SPLITS:
        raise ValueError("Unknown challenge family or split")
    rng = np.random.default_rng(seed)
    source = np.array([rng.uniform(-350, -155), rng.uniform(-105, 105)])
    if family == "boundary":
        edge = int(rng.integers(4))
        source = np.array([rng.uniform(-445, -85), rng.uniform(-215, 215)])
        source[edge % 2] = [
            (-450 + rng.uniform(0.5, 5)),
            (-220 + rng.uniform(0.5, 5)),
            (-80 - rng.uniform(0.5, 5)),
            (220 - rng.uniform(0.5, 5)),
        ][edge]
    q = float(rng.uniform(18000, 36000))
    if family == "weak_signal":
        q = float(rng.uniform(150, 450))
    if family == "background_only":
        q = 0.0
    background = float(rng.uniform(9, 16))
    drift = float(rng.normal(0, 0.8))
    if split == "development":
        measured_direction = float(rng.uniform(260, 280))
    elif split == "calibration":
        measured_direction = float(
            rng.uniform(255, 260) if seed % 2 else rng.uniform(280, 285)
        )
    else:
        measured_direction = float(
            rng.uniform(245, 255) if seed % 2 else rng.uniform(285, 295)
        )
    true_direction = measured_direction + (35.0 if family == "direction_bias" else 0.0)
    speed = float(rng.uniform(1.8, 3.4))
    monitors = layout(split) + rng.uniform(-12, 12, (len(layout(split)), 2))
    candidates = np.asarray(
        [(x, y) for x in (20.0, 150.0, 330.0, 560.0) for y in (-110.0, 0.0, 110.0)]
    )
    targets = np.asarray([(100.0, -35.0), (270.0, 40.0), (650.0, 5.0)])
    start = datetime(2026, 4, 5, 10, tzinfo=timezone.utc)
    stamps = [(start + timedelta(minutes=j * 6)).isoformat() for j in range(4)]
    secondary = np.array([rng.uniform(-350, -155), rng.uniform(-160, 160)])
    secondary_q = float(q * rng.uniform(0.8, 1.2)) if family == "two_sources" else 0.0
    state = {
        "family": family,
        "seed": seed,
        "split": split,
        "source_xy": source.tolist(),
        "strength": q,
        "background": background,
        "background_drift": drift,
        "speed": speed,
        "direction": true_direction,
        "measured_direction": measured_direction,
        "secondary_xy": secondary.tolist(),
        "secondary_strength": secondary_q,
        "monitor_xy": monitors.tolist(),
        "candidate_xy": candidates.tolist(),
        "target_xy": targets.tolist(),
        "stamps": stamps,
    }
    # Joint latent fields are drawn before planning but never passed to production.
    # All methods selecting one site receive that site's same eventual outcome.
    initial_xy = np.tile(monitors, (4, 1))
    all_xy = np.concatenate([initial_xy, candidates, targets])
    initial_epoch = np.repeat(np.arange(4), len(monitors))
    all_epoch = np.concatenate(
        [initial_epoch, np.full(len(candidates) + len(targets), 3)]
    )
    distance = np.linalg.norm(all_xy[:, None, :] - all_xy[None, :, :], axis=-1)
    elapsed = np.abs(all_epoch[:, None] - all_epoch[None, :])
    amplitude = 3.0 if family == "correlated_errors" else 0.7
    length = 500.0 if family == "correlated_errors" else 180.0
    time_length = 3.0 if family == "correlated_errors" else 1.2
    covariance = amplitude**2 * np.exp(-distance / length - elapsed / time_length)
    field = rng.multivariate_normal(
        np.zeros(len(all_xy)), covariance + np.eye(len(all_xy)) * 1e-8
    )
    biases = rng.normal(0, 0.7, len(monitors) + len(candidates) + len(targets))
    sigma = rng.uniform(0.8, 1.5, len(all_xy))
    initial_bias = np.tile(biases[: len(monitors)], 4)
    bias = np.concatenate([initial_bias, biases[len(monitors) :]])
    mean = true_mean(all_xy, all_epoch, state)
    latent = mean + field + bias
    observed = np.maximum(
        0, latent[: len(initial_xy)] + rng.normal(0, sigma[: len(initial_xy)])
    )
    state.update(
        future_latent=latent[len(initial_xy) :].tolist(),
        future_noise_seed=seed + 1900000,
        candidate_sigma=sigma[
            len(initial_xy) : len(initial_xy) + len(candidates)
        ].tolist(),
        target_mean=mean[-len(targets) :].tolist(),
        target_sigma=sigma[-len(targets) :].tolist(),
    )
    readings = []
    for j, (xy, epoch, value) in enumerate(zip(initial_xy, initial_epoch, observed)):
        sensor = j % len(monitors)
        if family == "missingness" and (sensor == 1 or rng.random() < 0.35):
            continue
        readings.append(
            Measurement(
                sensor_id=f"M{sensor:02}",
                timestamp=stamps[epoch],
                pm25_ug_m3=float(value),
                uncertainty_ug_m3=float(sigma[j]),
                origin="synthetic",
                **lonlat(xy, split),
            )
        )
    sites = [
        Site(id=f"M{i:02}", name=f"Monitor {i + 1}", kind="sensor", **lonlat(xy, split))
        for i, xy in enumerate(monitors)
    ]
    for i, xy in enumerate(candidates):
        sites.append(
            Site(
                id=f"C{i:02}",
                name=f"Candidate {i + 1}",
                allowed=True,
                power=True,
                access=True,
                cost=float([90, 110, 120, 100][i % 4]),
                **lonlat(xy, split),
            )
        )
    weather = []
    for i, stamp in enumerate(stamps):
        direction = measured_direction
        wind_speed = speed
        if family == "unsupported_weather":
            if seed % 2:
                wind_speed = 0.2
            else:
                direction += -45 if i % 2 else 45
        weather.append(
            Weather(
                timestamp=stamp,
                wind_speed_m_s=wind_speed,
                wind_from_deg=direction % 360,
                origin="synthetic",
                provenance="Constructed contemporaneous weather, representativeness assumed",
                **lonlat((150, 0), split),
            )
        )
    anchors = [
        Point(**lonlat((x, y), split))
        for x in (-450.0, -265.0, -80.0)
        for y in (-220.0, 0.0, 220.0)
    ]
    coords = [lonlat((-800, -800), split), lonlat((1300, 800), split)]
    inv = Investigation(
        name="Constructed transport challenge",
        synthetic=True,
        area=[
            coords[0]["longitude"],
            coords[0]["latitude"],
            coords[1]["longitude"],
            coords[1]["latitude"],
        ],
        measurements=readings,
        weather=weather,
        sites=sites,
        source_locations=anchors,
        assumptions=Assumptions(
            steady=True,
            open_terrain=True,
            local_weather=True,
            note="Constructed assumptions; no field verification",
        ),
        settings=Settings(budget=250.0, equipment_limit=2, noise_ug_m3=1.2, seed=17),
    )
    return inv, state


def reveal_future(state):
    """Realize withheld observations only after the plans have been locked."""
    sigma = np.asarray(state["candidate_sigma"] + state["target_sigma"])
    rng = np.random.default_rng(state["future_noise_seed"])
    values = np.maximum(0, np.asarray(state["future_latent"]) + rng.normal(0, sigma))
    count = len(state["candidate_xy"])
    return state | {
        "candidate_outcomes": values[:count].tolist(),
        "target_outcomes": values[count:].tolist(),
    }


def true_mean(points, epochs, state):
    points = np.asarray(points)
    epochs = np.asarray(epochs)
    strengths = np.full(len(points), state["strength"])
    if state["family"] == "episodic":
        strengths = strengths * ((epochs % 2) == 0)
    plume = transport(
        points,
        state["source_xy"],
        1.0,
        state["speed"],
        state["direction"],
        state["split"],
    )
    second = transport(
        points,
        state["secondary_xy"],
        state["secondary_strength"],
        state["speed"],
        state["direction"],
        state["split"],
    )
    return (
        state["background"]
        + state["background_drift"] * (epochs - 1.5) / 3
        + strengths * plume
        + second
    )


def load_baseline():
    """Load the full preserved package, isolating all baseline dependencies."""
    name = "_upwind_overhaul_baseline"
    if name not in sys.modules:
        path = ROOT / "evaluations/overhaul/baseline-source/backend/upwind"
        spec = importlib.util.spec_from_file_location(
            name, path / "__init__.py", submodule_search_locations=[str(path)]
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return importlib.import_module(name + ".engine"), importlib.import_module(
        name + ".models"
    )


def baseline_fit(inv):
    engine, models = load_baseline()
    payload = inv.model_dump()
    payload["settings"].pop("inference_limit", None)
    payload["settings"].pop("selection_seed", None)
    old = models.Investigation.model_validate_json(json.dumps(payload))
    return engine.ensemble(old)


def baseline_analysis(inv):
    engine, models = load_baseline()
    payload = inv.model_dump()
    payload["settings"].pop("inference_limit", None)
    payload["settings"].pop("selection_seed", None)
    old = models.Investigation.model_validate_json(json.dumps(payload))
    return engine.analyze(old)


def baseline_predictive(fitted, points, inv):
    engine, _ = load_baseline()
    xy = np.asarray(
        [fitted["projection"].transform(p.longitude, p.latitude) for p in points]
    )
    c = np.asarray(fitted["configs"])
    means = c[:, 2, None] + engine.plume(
        xy[None, :, :],
        fitted["source_xy"][c[:, 0].astype(int), None, :],
        c[:, 1, None],
        fitted["speed"] * c[:, 4, None],
        fitted["wind"] + c[:, 3, None],
    )
    distance = np.linalg.norm(xy[:, None] - xy[None, :], axis=-1)
    sigma = np.asarray(
        [
            getattr(p, "uncertainty_ug_m3", None) or inv.settings.noise_ug_m3
            for p in points
        ]
    )
    ids = np.asarray(
        [getattr(p, "sensor_id", f"held-{i}") for i, p in enumerate(points)]
    )
    covariance = (
        np.diag(sigma**2)
        + (ids[:, None] == ids[None, :]).astype(float)
        + inv.settings.noise_ug_m3**2 * np.exp(-distance / 150)
    )
    return means, np.broadcast_to(covariance, (len(means), *covariance.shape))


def predictive_scores(weights, means, covariances, observed):
    weights = np.asarray(weights, dtype=float)
    means = np.asarray(means, dtype=float)
    covariances = np.asarray(covariances, dtype=float)
    observed = np.asarray(observed, dtype=float)
    if means.shape != (len(weights), len(observed)) or covariances.shape != (
        len(weights),
        len(observed),
        len(observed),
    ):
        raise ValueError("Predictive component shapes disagree with weights/targets")
    variances = np.diagonal(covariances, axis1=1, axis2=2)
    if (
        not np.isfinite(means).all()
        or not np.isfinite(variances).all()
        or np.any(variances <= 0)
    ):
        raise ValueError("Predictive variance must be finite and positive")
    sigma = np.sqrt(variances)
    logw = np.log(np.maximum(weights, np.finfo(float).tiny))
    log_density = logsumexp(
        logw[:, None] + norm.logpdf(observed[None], loc=means, scale=sigma), axis=0
    )

    def quantile(prob):
        lo = np.min(means - 12 * sigma, axis=0)
        hi = np.max(means + 12 * sigma, axis=0)
        for _ in range(55):
            middle = (lo + hi) / 2
            cdf = np.sum(
                weights[:, None] * ndtr((middle[None] - means) / sigma), axis=0
            )
            lo = np.where(cdf < prob, middle, lo)
            hi = np.where(cdf >= prob, middle, hi)
        return (lo + hi) / 2

    lower, upper = quantile(0.05), quantile(0.95)
    mean = weights @ means
    return {
        "rmse_ug_m3": float(np.sqrt(np.mean((mean - observed) ** 2))),
        "nlpd": float(-np.mean(log_density)),
        "interval90_coverage": float(
            np.mean((observed >= lower) & (observed <= upper))
        ),
        "interval90_width": float(np.mean(upper - lower)),
        "target_count": len(observed),
        "observed": observed.tolist(),
        "mean": mean.tolist(),
        "lower90": lower.tolist(),
        "upper90": upper.tolist(),
    }


def source_metrics(fitted, state, legacy=False):
    source = lonlat(state["source_xy"], state["split"])
    target = np.asarray(
        fitted["projection"].transform(source["longitude"], source["latitude"])
    )
    centers = np.asarray(fitted["source_xy"])
    weights = np.asarray(
        fitted["location_weights"] if legacy else fitted["cell_weights"]
    )
    order = np.argsort(-weights, kind="stable")
    mode = int(order[0])
    tied = np.flatnonzero(weights.max() - weights <= 1e-12)
    mean = weights @ centers
    errors = np.linalg.norm(centers[tied] - target, axis=1)
    result = {
        "localization_error_m": float(np.linalg.norm(centers[mode] - target)),
        "source_mean_error_m": float(np.linalg.norm(mean - target)),
        "source_mean_xy": mean.tolist(),
        "map_tie_count": len(tied),
        "map_min_error_m": float(errors.min()),
        "map_max_error_m": float(errors.max()),
        "entropy_nats": float(
            -np.sum(weights[weights > 0] * np.log(weights[weights > 0]))
        ),
        "max_location_weight": float(weights.max()),
        "source_present": state["strength"] > 0,
    }
    if not legacy:
        cells = np.asarray(fitted["cells_xy"])
        selected = order[: int(np.searchsorted(np.cumsum(weights[order]), 0.9)) + 1]
        # Contract bounds are [xmin,ymin,xmax,ymax].
        areas = (cells[:, 2] - cells[:, 0]) * (cells[:, 3] - cells[:, 1])
        contains = (
            (cells[:, 0] <= target[0])
            & (target[0] <= cells[:, 2])
            & (cells[:, 1] <= target[1])
            & (target[1] <= cells[:, 3])
        )
        covered = bool(np.any(contains[selected]))
        p = float(fitted["source_probability"])
        ratio = float(areas[selected].sum() / areas.sum())
        result.update(
            source_probability=p,
            source_brier=(p - float(state["strength"] > 0)) ** 2,
            source_false_alarm=bool(state["strength"] == 0 and p > 0.9),
            source_miss=bool(state["strength"] > 0 and p < 0.5),
            region90_truth_covered=covered if state["strength"] > 0 else None,
            region90_area_m2=float(areas[selected].sum()),
            region90_area_fraction=ratio,
            region90_conditional_mass=float(weights[selected].sum()),
            region90_cell_ids=selected.tolist(),
            domain_area_m2=float(areas.sum()),
            narrow_wrong_region=bool(
                state["strength"] > 0 and not covered and ratio < 0.25
            ),
            sharp_wrong_region=bool(
                state["strength"] > 0 and p > 0.9 and not covered and ratio < 0.25
            ),
        )
    return result


def new_predictive(fitted, points):
    return fitted["predictive"](
        points,
        timestamps=[p.timestamp for p in points],
        sensor_ids=[getattr(p, "sensor_id", f"held-{i}") for i, p in enumerate(points)],
        uncertainties=[getattr(p, "uncertainty_ug_m3", None) or 1.2 for p in points],
    )


def evaluate_world(inv, state, legacy=False, held_sensor=True):
    from ..inference import fit

    started = time.perf_counter()
    record = {
        "family": state["family"],
        "seed": state["seed"],
        "split": state["split"],
        "model": "legacy-0.2.1" if legacy else "mixture-0.3.0",
        "loaded_rows": len(inv.measurements),
        "input_sha256": hashlib.sha256(inv.model_dump_json().encode()).hexdigest(),
    }
    try:
        fitted = baseline_fit(inv) if legacy else fit(inv, diagnostics=True)
        record.update(status="retained", **source_metrics(fitted, state, legacy))
        record["fitted_rows"] = int(
            fitted.get("rows_used", len(fitted.get("rows", [])))
        )
        record["usable_rows"] = int(fitted.get("rows_input", len(inv.measurements)))
        record["quality_excluded_rows"] = len(inv.measurements) - record["usable_rows"]
        record["subsampled_rows"] = record["usable_rows"] - record["fitted_rows"]
        record["diagnostics"] = fitted.get("diagnostics", {})
        record["mismatch_warning"] = (
            bool(fitted.get("standardized_residual_rms", 0) > 3)
            if legacy
            else bool(fitted.get("diagnostics", {}).get("predictive_warning", False))
        )
        if held_sensor:
            ids = sorted({m.sensor_id for m in inv.measurements})
            # Cycle complete sensor blocks rather than always scoring a distant
            # low-signal receptor. This choice uses only evaluator indexing.
            held_id = ids[(state["seed"] - SPLITS[state["split"]].start) % len(ids)]
            held = [m for m in inv.measurements if m.sensor_id == held_id]
            training = inv.model_copy(deep=True)
            training.measurements = [
                m for m in inv.measurements if m.sensor_id != held_id
            ]
            try:
                trained = (
                    baseline_fit(training)
                    if legacy
                    else fit(training, diagnostics=False)
                )
                means, covs = (
                    baseline_predictive(trained, held, training)
                    if legacy
                    else new_predictive(trained, held)
                )
                record["held_sensor"] = held_id
                record["prediction"] = predictive_scores(
                    trained["weights"], means, covs, [m.pm25_ug_m3 for m in held]
                )
            except (ValueError, OverflowError) as exc:
                record["prediction_unavailable"] = str(exc)
    except (ValueError, OverflowError) as exc:
        record.update(status="refused", reason=str(exc))
    except Exception as exc:
        record.update(status="crash", reason=f"{type(exc).__name__}: {exc}")
    record["wall_ms"] = round((time.perf_counter() - started) * 1000, 3)
    return record


def select_random(inv, seed):
    ids = sorted(
        [
            i
            for i, site in enumerate(inv.sites)
            if site.kind == "candidate"
            and site.allowed
            and site.access
            and site.power
            and inv.settings.window in site.windows
            and site.cost <= inv.settings.budget
        ],
        key=lambda i: inv.sites[i].id,
    )
    np.random.default_rng(seed).shuffle(ids)
    selected, budget = [], inv.settings.budget
    for i in ids:
        if (
            len(selected) < inv.settings.equipment_limit
            and inv.sites[i].cost <= budget + 1e-9
        ):
            selected.append(inv.sites[i].id)
            budget -= inv.sites[i].cost
    return selected


def planner_world(inv, state):
    from ..engine import analyze
    from ..inference import fit

    locked = []
    new = analyze(inv)
    old = baseline_analysis(inv)
    for method, result in (("new", new), ("legacy", old)):
        if result.get("plans"):
            locked.append((method, list(result["plans"][0]["site_ids"])))
        else:
            locked.append((method, []))
    for key, prefix in (("spread", "Spatial"), ("wind", "Wind")):
        plan = next(
            (p for p in old.get("plans", []) if p["method"].startswith(prefix)), None
        )
        locked.append((key, [] if plan is None else list(plan["site_ids"])))
    locked.extend(
        (f"random-{seed}", select_random(inv, seed)) for seed in range(7000, 7020)
    )
    locked_hash = hashlib.sha256(
        json.dumps(locked, sort_keys=True).encode()
    ).hexdigest()
    # Hidden outcomes are generated only after every method has locked its plan.
    state = reveal_future(state)
    outcomes = {
        f"C{i:02}": value for i, value in enumerate(state["candidate_outcomes"])
    }
    sigma = {f"C{i:02}": value for i, value in enumerate(state["candidate_sigma"])}
    target_points = [
        Measurement(
            sensor_id=f"T{i}",
            timestamp=state["stamps"][-1],
            pm25_ug_m3=float(value),
            uncertainty_ug_m3=float(s),
            origin="synthetic",
            **lonlat(xy, state["split"]),
        )
        for i, (xy, value, s) in enumerate(
            zip(state["target_xy"], state["target_outcomes"], state["target_sigma"])
        )
    ]
    basefit = fit(inv, diagnostics=False)
    means, covs = new_predictive(basefit, target_points)
    prior = predictive_scores(basefit["weights"], means, covs, state["target_outcomes"])
    prior_source = source_metrics(basefit, state)
    records = []
    for method, selected in locked:
        updated = inv.model_copy(deep=True)
        for id in selected:
            site = next(s for s in inv.sites if s.id == id)
            updated.measurements.append(
                Measurement(
                    sensor_id="followup-" + id,
                    timestamp=state["stamps"][-1],
                    pm25_ug_m3=float(outcomes[id]),
                    uncertainty_ug_m3=float(sigma[id]),
                    origin="synthetic",
                    latitude=site.latitude,
                    longitude=site.longitude,
                )
            )
        cost = sum(s.cost for s in inv.sites if s.id in selected)
        assert (
            cost <= inv.settings.budget + 1e-9
            and len(selected) <= inv.settings.equipment_limit
        )
        row = {
            "family": state["family"],
            "seed": state["seed"],
            "split": state["split"],
            "method": method,
            "site_ids": selected,
            "cost": cost,
            "equipment": len(selected),
            "locked_plan_sha256": locked_hash,
            "prior_prediction": prior,
            "prior_source": prior_source,
        }
        try:
            fitted = fit(updated, diagnostics=False)
            means, covs = new_predictive(fitted, target_points)
            post = predictive_scores(
                fitted["weights"], means, covs, state["target_outcomes"]
            )
            metrics = source_metrics(fitted, state)
            row.update(status="retained", prediction=post, **metrics)
            row.update(
                predictive_improvement=prior["rmse_ug_m3"] - post["rmse_ug_m3"],
                log_score_improvement=prior["nlpd"] - post["nlpd"],
                localization_improvement_m=prior_source["localization_error_m"]
                - metrics["localization_error_m"],
                entropy_reduction=prior_source["entropy_nats"]
                - metrics["entropy_nats"],
            )
        except Exception as exc:
            row.update(status="crash", reason=f"{type(exc).__name__}: {exc}")
        records.append(row)
    return records


def perturbations(inv, state):
    from ..engine import analyze
    from ..inference import fit

    result = []
    original = source_metrics(fit(inv, diagnostics=False), state)
    check_plan = state["seed"] == SPLITS[state["split"]].start
    initial_plan = (
        set(analyze(inv).get("plans", [{}])[0].get("site_ids", []))
        if check_plan
        else set()
    )
    for kind in ("wind+3deg", "concentration+0.5", "input-order"):
        changed = inv.model_copy(deep=True)
        if kind == "wind+3deg":
            for w in changed.weather:
                w.wind_from_deg = (w.wind_from_deg + 3) % 360
        elif kind == "concentration+0.5":
            for m in changed.measurements:
                m.pm25_ug_m3 += 0.5
        else:
            changed.measurements.reverse()
            changed.sites.reverse()
            changed.source_locations.reverse()
        try:
            fitted = fit(changed, diagnostics=False)
            metrics = source_metrics(fitted, state)
            # Compare means geographically because projection origins can differ.
            lon0, lat0 = fitted["projection"].transform(
                *metrics["source_mean_xy"], direction="INVERSE"
            )
            basefit = fit(inv, diagnostics=False)
            projected = basefit["projection"].transform(lon0, lat0)
            displacement = float(
                np.linalg.norm(np.asarray(projected) - original["source_mean_xy"])
            )
            a, b = set(original["region90_cell_ids"]), set(metrics["region90_cell_ids"])
            row = {
                "family": state["family"],
                "seed": state["seed"],
                "perturbation": kind,
                "source_probability_change": metrics["source_probability"]
                - original["source_probability"],
                "source_mean_displacement_m": displacement,
                "region_symmetric_difference_fraction": len(a ^ b) / max(1, len(a | b)),
                "plan_overlap_checked": check_plan,
                "status": "retained",
            }
            if check_plan:
                changed_plan = set(
                    analyze(changed).get("plans", [{}])[0].get("site_ids", [])
                )
                row["plan_jaccard_overlap"] = len(initial_plan & changed_plan) / max(
                    1, len(initial_plan | changed_plan)
                )
                row["initial_plan"] = sorted(initial_plan)
                row["perturbed_plan"] = sorted(changed_plan)
            result.append(row)
        except Exception as exc:
            result.append(
                {
                    "family": state["family"],
                    "seed": state["seed"],
                    "perturbation": kind,
                    "status": "refused",
                    "reason": str(exc),
                }
            )
    return result


def supplementary_runs():
    """Development-only mechanism ablations and explicit full-data comparisons."""
    from ..inference import fit

    ablations, sampling = [], []
    for family in (
        "background_only",
        "weak_signal",
        "strong_signal",
        "direction_bias",
        "two_sources",
        "episodic",
    ):
        inv, state = make_world(family, 410000, "development")
        state = reveal_future(state)
        for name, kwargs in (
            ("full", {}),
            ("background_only", {"background_only": True}),
            ("no_wind_uncertainty", {"wind_uncertainty": False}),
        ):
            started = time.perf_counter()
            fitted = fit(inv, diagnostics=False, **kwargs)
            targets = [
                Measurement(
                    sensor_id=f"T{i}",
                    timestamp=state["stamps"][-1],
                    pm25_ug_m3=float(value),
                    uncertainty_ug_m3=float(s),
                    origin="synthetic",
                    **lonlat(xy, "development"),
                )
                for i, (xy, value, s) in enumerate(
                    zip(
                        state["target_xy"],
                        state["target_outcomes"],
                        state["target_sigma"],
                    )
                )
            ]
            means, covs = new_predictive(fitted, targets)
            ablations.append(
                {
                    "family": family,
                    "seed": 410000,
                    "ablation": name,
                    **source_metrics(fitted, state),
                    "prediction": predictive_scores(
                        fitted["weights"], means, covs, state["target_outcomes"]
                    ),
                    "wall_ms": (time.perf_counter() - started) * 1000,
                }
            )
    for size in (24, 48, 96, 192):
        inv, state = make_world("strong_signal", 410001, "development")
        monitors = np.asarray(state["monitor_xy"][:6])
        epochs = size // len(monitors)
        rng = np.random.default_rng(420000 + size)
        start = datetime.fromisoformat(state["stamps"][0])
        readings = []
        rare_keys = []
        for epoch in range(epochs):
            timestamp = (
                start + timedelta(seconds=1800 * epoch / max(1, epochs - 1))
            ).isoformat()
            # One isolated high-release episode, deliberately outside the steady
            # model. The algorithm receives concentrations only, never this flag.
            rare = epoch == epochs // 3
            for sensor, xy in enumerate(monitors):
                value = (
                    state["background"]
                    + transport(
                        [xy],
                        state["source_xy"],
                        state["strength"] * (4 if rare else 1),
                        state["speed"],
                        state["direction"],
                        "development",
                    )[0]
                    + rng.normal(0, 1.2)
                )
                readings.append(
                    Measurement(
                        sensor_id=f"M{sensor:02}",
                        timestamp=timestamp,
                        pm25_ug_m3=float(max(0, value)),
                        uncertainty_ug_m3=1.2,
                        origin="synthetic",
                        **lonlat(xy, "development"),
                    )
                )
                if rare:
                    rare_keys.append((f"M{sensor:02}", timestamp))
        inv.measurements = readings
        # Keep representative weather at both ends of the entire loaded window.
        inv.weather[-1].timestamp = readings[-1].timestamp
        reference = inv.model_copy(deep=True)
        reference.settings.inference_limit = 512
        full = fit(reference, diagnostics=False)
        full_metrics = source_metrics(full, state)
        for limit in (40, 64, 128, 512):
            for selection_seed in (0, 11) if size == 192 and limit < size else (0,):
                candidate = inv.model_copy(deep=True)
                candidate.settings.inference_limit = limit
                candidate.settings.selection_seed = selection_seed
                started = time.perf_counter()
                fitted = fit(candidate, diagnostics=False)
                metrics = source_metrics(fitted, state)
                selected_keys = {(m.sensor_id, m.timestamp) for m in fitted["rows"]}
                sampling.append(
                    {
                        "loaded_rows": size,
                        "fitted_rows": fitted["rows_used"],
                        "inference_limit": limit,
                        "selection_seed": selection_seed,
                        "rare_episode_loaded_rows": len(rare_keys),
                        "rare_episode_retained_rows": len(
                            selected_keys.intersection(rare_keys)
                        ),
                        "source_probability": metrics["source_probability"],
                        "source_probability_difference_from_full": metrics[
                            "source_probability"
                        ]
                        - full_metrics["source_probability"],
                        "source_mean_displacement_from_full_m": float(
                            np.linalg.norm(
                                np.asarray(metrics["source_mean_xy"])
                                - full_metrics["source_mean_xy"]
                            )
                        ),
                        "region90_area_m2": metrics["region90_area_m2"],
                        "full_region90_area_m2": full_metrics["region90_area_m2"],
                        "wall_ms": (time.perf_counter() - started) * 1000,
                    }
                )
    return {"split": "development", "ablations": ablations, "subsampling": sampling}


def wilson(success, total):
    if total == 0:
        return None
    p = success / total
    z = 1.96
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    radius = z / denominator * math.sqrt(p * (1 - p) / total + z * z / (4 * total**2))
    return [max(0.0, center - radius), min(1.0, center + radius)]


def distribution(values):
    values = [v for v in values if v is not None and math.isfinite(v)]
    if not values:
        return None
    return {
        "n": len(values),
        "mean": float(np.mean(values)),
        "median": float(np.median(values)),
        "p10": float(np.quantile(values, 0.1)),
        "p90": float(np.quantile(values, 0.9)),
        "min": float(min(values)),
        "max": float(max(values)),
    }


def summarize(science, followup):
    groups = []
    for family in FAMILIES:
        for model in ("legacy-0.2.1", "mixture-0.3.0"):
            rows = [r for r in science if r["family"] == family and r["model"] == model]
            retained = [r for r in rows if r["status"] == "retained"]
            group = {
                "family": family,
                "model": model,
                "total": len(rows),
                "statuses": dict(Counter(r["status"] for r in rows)),
                "retained_fraction": len(retained) / max(1, len(rows)),
            }
            source_rows = [r for r in retained if r["source_present"]]
            for metric in (
                "localization_error_m",
                "source_mean_error_m",
                "source_probability",
                "source_brier",
                "region90_area_m2",
                "region90_area_fraction",
                "wall_ms",
            ):
                group[metric] = distribution(
                    [
                        r.get(metric)
                        for r in (
                            source_rows
                            if metric.startswith("localization")
                            or metric.startswith("source_mean")
                            else retained
                        )
                    ]
                )
            for metric in (
                "region90_truth_covered",
                "sharp_wrong_region",
                "source_false_alarm",
                "source_miss",
                "mismatch_warning",
            ):
                usable = [r for r in retained if r.get(metric) is not None]
                if metric in ("source_miss", "sharp_wrong_region"):
                    usable = [r for r in usable if r["source_present"]]
                if metric == "source_false_alarm":
                    usable = [r for r in usable if not r["source_present"]]
                n = len(usable)
                count = sum(bool(r[metric]) for r in usable)
                group[metric] = {
                    "count": count,
                    "n": n,
                    "fraction": count / n if n else None,
                    "wilson95": wilson(count, n),
                }
            for metric in (
                "rmse_ug_m3",
                "nlpd",
                "interval90_coverage",
                "interval90_width",
            ):
                group["held_sensor_" + metric] = distribution(
                    [r["prediction"][metric] for r in retained if r.get("prediction")]
                )
            groups.append(group)
    planner = []
    for family in sorted(PLANNER_FAMILIES):
        rows = [
            r for r in followup if r["family"] == family and r["status"] == "retained"
        ]
        random = {}
        for seed in sorted({r["seed"] for r in rows}):
            worlds = [
                r
                for r in rows
                if r["seed"] == seed and r["method"].startswith("random-")
            ]
            if worlds:
                random[seed] = {
                    "error": float(
                        np.mean([r["localization_error_m"] for r in worlds])
                    ),
                    "rmse": float(
                        np.mean([r["prediction"]["rmse_ug_m3"] for r in worlds])
                    ),
                }
        for method in ("new", "legacy", "spread", "wind"):
            chosen = [r for r in rows if r["method"] == method and r["seed"] in random]
            rmse_adv = [
                random[r["seed"]]["rmse"] - r["prediction"]["rmse_ug_m3"]
                for r in chosen
            ]
            error_adv = [
                random[r["seed"]]["error"] - r["localization_error_m"] for r in chosen
            ]
            planner.append(
                {
                    "family": family,
                    "method": method,
                    "n": len(chosen),
                    "posterior_error_m": distribution(
                        [r["localization_error_m"] for r in chosen]
                    ),
                    "posterior_rmse": distribution(
                        [r["prediction"]["rmse_ug_m3"] for r in chosen]
                    ),
                    "rmse_advantage_vs_random20": distribution(rmse_adv),
                    "localization_advantage_vs_random20_m": distribution(error_adv),
                    "worse_rmse_than_random20": {
                        "count": sum(v < 0 for v in rmse_adv),
                        "n": len(rmse_adv),
                        "wilson95": wilson(sum(v < 0 for v in rmse_adv), len(rmse_adv)),
                    },
                    "mean_cost": float(np.mean([r["cost"] for r in chosen]))
                    if chosen
                    else None,
                }
            )
    bins = []
    rows = [
        r
        for r in science
        if r["model"] == "mixture-0.3.0" and r["status"] == "retained"
    ]
    for i in range(5):
        selected = [
            r
            for r in rows
            if i * 0.2 <= r["source_probability"]
            and (r["source_probability"] < (i + 1) * 0.2 or i == 4)
        ]
        bins.append(
            {
                "lower": i * 0.2,
                "upper": (i + 1) * 0.2,
                "n": len(selected),
                "mean_weight": float(
                    np.mean([r["source_probability"] for r in selected])
                )
                if selected
                else None,
                "fraction_source": float(
                    np.mean([r["source_present"] for r in selected])
                )
                if selected
                else None,
            }
        )
    return {
        "protocol": PROTOCOL,
        "science_world_results": len(science),
        "planner_results": len(followup),
        "crashes": sum(r["status"] == "crash" for r in science + followup),
        "by_condition": groups,
        "planner": planner,
        "source_reliability_bins": bins,
        "reliability_population_note": "Artificial challenge prevalence (8/9 supported conditions have sources); not a field source probability calibration.",
    }


def hashes():
    # UI/report wording can be integrated while numerical outcomes run. Freeze
    # every scientific dependency and evaluator; never ignore a numeric edit.
    production = (
        "inference.py",
        "design.py",
        "engine.py",
        "legacy.py",
        "models.py",
        "numerics.py",
        "quality.py",
        "weather.py",
    )
    paths = [ROOT / "backend/upwind" / name for name in production]
    paths += list((ROOT / "backend/upwind/validation").glob("*.py"))
    paths += [ROOT / "docs/ENGINE_EVALUATION_PROTOCOL.md", ROOT / "requirements.lock"]
    return {
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(paths)
    }


def self_checks():
    assert np.allclose(
        transport([(100, 0)], (0, 0), 1000, 2, 270, "final"),
        transport([(0, -100)], (0, 0), 1000, 2, 0, "final"),
    )
    assert transport([(-100, 0)], (0, 0), 1000, 2, 270, "final")[0] == 0
    assert np.allclose(
        transport([(100, 0)], (0, 0), 2000, 2, 270, "final"),
        2 * transport([(100, 0)], (0, 0), 1000, 2, 270, "final"),
    )
    assert np.allclose(
        transport([(100, 0)], (0, 0), 1000, 4, 270, "final"),
        0.5 * transport([(100, 0)], (0, 0), 1000, 2, 270, "final"),
    )
    means = np.array([[0.0, 0.0]])
    scores = predictive_scores(np.array([1.0]), means, np.array([np.eye(2)]), [0, 0])
    assert abs(scores["interval90_width"] - 2 * norm.ppf(0.95)) < 1e-10
    assert abs(scores["nlpd"] - 0.5 * math.log(2 * math.pi)) < 1e-12
    return {"independent_generator_and_predictive_score_checks": 6, "passed": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=SPLITS, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--limit-seeds", type=int)
    parser.add_argument("--skip-planner", action="store_true")
    parser.add_argument("--families", nargs="+", choices=FAMILIES)
    parser.add_argument("--supplementary-only", action="store_true")
    args = parser.parse_args()
    if args.split == "final" and (args.limit_seeds is not None or args.families):
        parser.error("Partial final runs are prohibited; use development for debugging")
    if args.supplementary_only and args.split != "development":
        parser.error("Ablations and sampling diagnostics use development data only")
    if args.out.exists() and any(args.out.iterdir()):
        parser.error("Output folder must be empty; preserve prior results")
    args.out.mkdir(parents=True, exist_ok=True)
    seeds = list(SPLITS[args.split])
    if args.limit_seeds is not None:
        if args.limit_seeds < 1:
            parser.error("--limit-seeds must be positive")
        seeds = seeds[: args.limit_seeds]
    families = args.families or FAMILIES
    frozen = hashes()
    cpu = (
        next(
            (
                line.split(":", 1)[1].strip()
                for line in Path("/proc/cpuinfo").read_text().splitlines()
                if line.startswith("model name")
            ),
            platform.processor(),
        )
        if Path("/proc/cpuinfo").exists()
        else platform.processor()
    )
    metadata = {
        "protocol": PROTOCOL,
        "split": args.split,
        "seeds": seeds,
        "families": list(families),
        "partial": args.limit_seeds is not None or bool(args.families),
        "planner_skipped": args.skip_planner,
        "supplementary_only": args.supplementary_only,
        "command": sys.argv,
        "utc": datetime.now(timezone.utc).isoformat(),
        "source_hashes_before": frozen,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "processor": cpu,
        "numpy": np.__version__,
        "blas_threads": os.environ.get("OPENBLAS_NUM_THREADS"),
        "self_checks": self_checks(),
    }
    write(args.out / "metadata.json", metadata)
    if args.supplementary_only:
        write(args.out / "supplementary.json", supplementary_runs())
        print("Development ablations and sampling comparison saved", flush=True)
        return
    science, followup, stability, truths = [], [], [], []
    started = time.perf_counter()
    for family in families:
        for seed in seeds:
            inv, state = make_world(family, seed, args.split)
            truths.append(state)
            for old in (True, False):
                row = evaluate_world(inv, state, old)
                science.append(row)
                if row["status"] == "crash":
                    print("CRASH", family, seed, row.get("reason"), flush=True)
            if family != "unsupported_weather" and seed in seeds[:4]:
                try:
                    stability.extend(perturbations(inv, state))
                except Exception as exc:
                    stability.append(
                        {
                            "family": family,
                            "seed": seed,
                            "status": "crash",
                            "reason": str(exc),
                        }
                    )
            if (
                not args.skip_planner
                and family in PLANNER_FAMILIES
                and seed in seeds[:12]
            ):
                try:
                    followup.extend(planner_world(inv, state))
                except Exception as exc:
                    followup.append(
                        {
                            "family": family,
                            "seed": seed,
                            "status": "crash",
                            "method": "all",
                            "reason": f"{type(exc).__name__}: {exc}",
                        }
                    )
        write(args.out / "science.json", science)
        write(args.out / "followup.json", followup)
        write(args.out / "stability.json", stability)
        write(args.out / "truth.json", truths)
        print(
            f"{family}: {len(seeds)} worlds, {len(science)} inference results, {len(followup)} followups",
            flush=True,
        )
    summary = summarize(science, followup)
    summary.update(
        wall_seconds=round(time.perf_counter() - started, 3),
        peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
        source_hashes_unchanged=frozen == hashes(),
    )
    write(args.out / "summary.json", summary)
    metadata["source_hashes_after"] = hashes()
    write(args.out / "metadata.json", metadata)
    print(
        json.dumps(
            {
                k: summary[k]
                for k in (
                    "science_world_results",
                    "planner_results",
                    "crashes",
                    "wall_seconds",
                    "source_hashes_unchanged",
                )
            }
        ),
        flush=True,
    )
    if summary["crashes"] or not summary["source_hashes_unchanged"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
