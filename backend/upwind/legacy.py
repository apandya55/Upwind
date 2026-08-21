"""Legacy single-source dispersion and monitoring design models."""

from functools import lru_cache
from itertools import combinations, product
import hashlib
import json
import time
import numpy as np
from scipy.linalg import solve_triangular
from .numerics import projector, flow_vector, plume, stable_information
from .quality import measurement_quality, balanced_rows
from .weather import matched_weather
from scipy.special import logsumexp
from .models import Investigation

MODEL_VERSION = "plume-ensemble-0.2.1"
BAD_FLAGS = {"negative", "duplicate", "extreme_review"}


def spatial_projector(inv):
    # Fixed geographic origin regardless of CSV/site-list order.
    return projector(
        float(np.mean(sorted(s.latitude for s in inv.sites))),
        float(np.mean(sorted(s.longitude for s in inv.sites))),
    )


def clean_measurements(inv):
    return measurement_quality(inv)[0]


def ensemble(inv):
    if not all(
        [
            inv.assumptions.steady,
            inv.assumptions.open_terrain,
            inv.assumptions.local_weather,
        ]
    ):
        raise ValueError(
            "Confirm steady conditions, open terrain, and representative local weather to enable experimental reconstruction."
        )
    rows = clean_measurements(inv)
    if len({m.sensor_id for m in rows}) < 2:
        raise ValueError(
            "At least two distinct sensors with usable readings are required for scenario comparison."
        )
    if len(inv.source_locations) < 2:
        raise ValueError(
            "Mark at least two plausible source scenario locations (maximum 25)."
        )
    lat, lon = (
        np.mean([p.latitude for p in inv.source_locations]),
        np.mean([p.longitude for p in inv.source_locations]),
    )
    tr = projector(lat, lon)
    xy = lambda points: np.array(
        [tr.transform(p.longitude, p.latitude) for p in points]
    )
    source_xy, measured_xy, site_xy = (
        xy(inv.source_locations),
        xy(rows),
        xy(inv.sites).reshape(-1, 2),
    )
    if (
        max(np.linalg.norm(measured_xy, axis=1)) > 3000
        or max(np.linalg.norm(source_xy, axis=1)) > 1500
    ):
        raise ValueError(
            "Study area exceeds supported short-range geometry (3 km receptors, 1.5 km source radius)."
        )
    source_distance = np.linalg.norm(
        source_xy[:, None, :] - source_xy[None, :, :], axis=-1
    )
    if np.any(source_distance[np.triu_indices(len(source_xy), 1)] < 1):
        raise ValueError("Source hypothesis locations must be at least 1 m apart")
    pairs = np.linalg.norm(measured_xy[:, None, :] - source_xy[None, :, :], axis=-1)
    if pairs.min() < 20 or pairs.max() > 3000:
        raise ValueError(
            "Every observation/source pair must be between 20 m and 3 km; unsupported pairs are not zero evidence"
        )
    all_met, wind, speed = matched_weather(inv, rows, tr)
    met_by_key = {(m.sensor_id, m.timestamp): w for m, w in zip(rows, all_met)}
    input_count = len(rows)
    rows = balanced_rows(rows)
    met = [met_by_key[m.sensor_id, m.timestamp] for m in rows]
    measured_xy = xy(rows)
    # Uniform discrete nuisance prior, truncated to supported wind speeds.
    nominal = np.array([w.wind_speed_m_s for w in all_met] + [speed])
    scales = [
        scale
        for scale in [0.85, 1.15]
        if np.all((nominal * scale >= 0.8) & (nominal * scale <= 8))
    ]
    if not scales:
        raise ValueError("Weather uncertainty scenarios exceed supported wind speeds")
    configs = list(
        product(
            range(len(source_xy)),
            [1500.0, 5000.0, 12000.0],
            [4.0, 10.0, 18.0],
            [-12.0, 0.0, 12.0],
            scales,
        )
    )
    config = np.asarray(configs)
    groups = config[:, 0].astype(int)
    q, bg, dw, scale = (config[:, i, None] for i in range(1, 5))
    pred = bg + plume(
        measured_xy[None, :, :],
        source_xy[groups, None, :],
        q,
        np.array([w.wind_speed_m_s for w in met])[None, :] * scale,
        np.array([w.wind_from_deg for w in met])[None, :] + dw,
    )
    cp = bg + plume(
        site_xy[None, :, :], source_xy[groups, None, :], q, speed * scale, wind + dw
    )
    sigma = np.array([m.uncertainty_ug_m3 or inv.settings.noise_ug_m3 for m in rows])
    ids = np.array([m.sensor_id for m in rows])
    # Shared 1 ug/m³ instrument bias: repeated readings do not become independent truth.
    distance = np.linalg.norm(
        measured_xy[:, None, :] - measured_xy[None, :, :], axis=-1
    )
    covariance = (
        np.diag(sigma**2)
        + (ids[:, None] == ids[None, :]).astype(float)
        + inv.settings.noise_ug_m3**2 * np.exp(-distance / 150)
    )
    residual = np.array([m.pm25_ug_m3 for m in rows]) - pred
    chol = np.linalg.cholesky(covariance)
    white = solve_triangular(chol, residual.T, lower=True, check_finite=False)
    ll = -0.5 * np.sum(white**2, axis=0)
    weights = np.exp(ll - logsumexp(ll))
    groups = np.array([c[0] for c in configs])
    lp = np.bincount(groups, weights=weights, minlength=len(source_xy))
    mean_prediction = weights @ pred
    rmse = float(
        np.sqrt(
            np.mean((mean_prediction - np.array([m.pm25_ug_m3 for m in rows])) ** 2)
        )
    )
    residual_mean = np.array([m.pm25_ug_m3 for m in rows]) - mean_prediction
    standardized = float(
        np.sqrt(
            np.mean(
                solve_triangular(chol, residual_mean, lower=True, check_finite=False)
                ** 2
            )
        )
    )
    return {
        "standardized_residual_rms": standardized,
        "weights": weights,
        "groups": groups,
        "location_weights": lp,
        "candidate_predictions": cp,
        "site_xy": site_xy,
        "source_xy": source_xy,
        "wind": wind,
        "speed": speed,
        "rmse": rmse,
        "rows_used": len(rows),
        "scenario_count": len(configs),
        "configs": configs,
        "projection": tr,
        "rows": rows,
        "rows_input": input_count,
        "candidate_supported": np.all(
            (np.linalg.norm(site_xy[:, None, :] - source_xy[None, :, :], axis=-1) >= 20)
            & (
                np.linalg.norm(site_xy[:, None, :] - source_xy[None, :, :], axis=-1)
                <= 3000
            ),
            axis=1,
        ),
    }


def eligible_indices(inv):
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
        ],
        key=lambda i: inv.sites[i].id,
    )


def information_matrices(e, noise):
    p, w, groups = e["candidate_predictions"], e["weights"], e["groups"]
    mu = w @ p
    within = np.zeros((p.shape[1], p.shape[1]))
    between = np.zeros_like(within)
    for loc, prob in enumerate(e["location_weights"]):
        if prob < 1e-14:
            continue
        mask = groups == loc
        conditional = w[mask] / prob
        local_mean = conditional @ p[mask]
        dev = p[mask] - local_mean
        within += prob * (dev.T * conditional) @ dev
        between += prob * np.outer(local_mean - mu, local_mean - mu)
    d = np.linalg.norm(e["site_xy"][:, None, :] - e["site_xy"][None, :, :], axis=-1)
    # Correlated local/model error plus independent instrument noise. Near sites redundant.
    r = within + noise**2 * (np.eye(len(d)) + np.exp(-d / 150)) + np.eye(len(d))
    return r, between


def select_plan(inv, method, score, eligible, rng):
    chosen, remaining = [], inv.settings.budget
    indices = eligible.copy()
    if method == "random":
        indices.sort(key=lambda i: inv.sites[i].id)
        rng.shuffle(indices)
    while len(chosen) < inv.settings.equipment_limit:
        feasible = [
            i
            for i in indices
            if i not in chosen and inv.sites[i].cost <= remaining + 1e-9
        ]
        if not feasible:
            break
        if method == "information":
            best = min(
                feasible,
                key=lambda i: (
                    -round(
                        (score(chosen + [i]) - score(chosen))
                        / max(inv.sites[i].cost, 1),
                        12,
                    ),
                    inv.sites[i].id,
                ),
            )
            if score(chosen + [best]) - score(chosen) <= 1e-10:
                break
        elif method == "spread":
            tr = spatial_projector(inv)
            xy = lambda i: np.array(
                tr.transform(inv.sites[i].longitude, inv.sites[i].latitude)
            )
            anchors = chosen + [
                i for i, s in enumerate(inv.sites) if s.kind == "sensor"
            ]
            center = np.mean([xy(i) for i in indices], axis=0)

            def separation(i):
                return min(
                    [np.linalg.norm(xy(i) - xy(j)) for j in anchors]
                    or [np.linalg.norm(xy(i) - center)]
                )

            best = min(
                feasible,
                key=lambda i: (-round(float(separation(i)), 8), inv.sites[i].id),
            )
        elif method == "wind":
            # Score function injected with wind order by caller.
            best = feasible[0]
        else:
            best = feasible[0]
        chosen.append(best)
        remaining -= inv.sites[best].cost
    return chosen


def analyze(inv: Investigation):
    # Validate a JSON round-trip so default numbers and imported numbers have the
    # same schema types (e.g. 350 and 350.0). Archives must reproduce their hash.
    canonical = Investigation.model_validate_json(inv.model_dump_json())
    payload = canonical.model_dump(exclude={"result", "plan_history", "id"})
    return json.loads(_cached_analysis(json.dumps(payload, sort_keys=True)))


@lru_cache(maxsize=32)
def _cached_analysis(payload):
    inv = Investigation.model_validate_json(payload)
    started = time.perf_counter()
    key = hashlib.sha256((MODEL_VERSION + payload).encode()).hexdigest()
    warnings = [
        "Experimental conditional scenario weights; no field-validated attribution.",
        "Future measurement scheduling is unsupported. This compares sites in a specified observed steady window.",
    ]
    if inv.synthetic:
        warnings.insert(
            0,
            "SYNTHETIC investigation: contains simulated inputs; no field validation. See row origins for imported or synthetic measurements/weather.",
        )
    eligible = eligible_indices(inv)
    e, reason = None, None
    try:
        e = ensemble(inv)
    except (ValueError, OverflowError) as exc:
        reason = str(exc)
    if inv.settings.objective == "scenario_information" and e is None:
        return json.dumps(
            {
                "status": "insufficient_data",
                "reason": reason,
                "warnings": warnings,
                "model_version": MODEL_VERSION,
                "input_hash": key,
                "plans": [],
                "sources": [],
            }
        )
    if inv.settings.objective == "scenario_information":
        unsupported = [
            inv.sites[i].id for i in eligible if not e["candidate_supported"][i]
        ]
        eligible = [i for i in eligible if e["candidate_supported"][i]]
        if unsupported:
            warnings.append(
                "Excluded candidates outside supported source-distance geometry: "
                + ", ".join(unsupported)
            )
        r, b = information_matrices(e, inv.settings.noise_ug_m3)

        def score(indices):
            if not indices:
                return 0.0
            return stable_information(r, b, indices)

        interpretation = "Approximate location information (nats); Gaussian moments marginalize strength, background, and weather uncertainty. Not a probability or health benefit."
    else:
        if not inv.sites:
            return json.dumps(
                {
                    "status": "infeasible",
                    "reason": "Add candidate sites.",
                    "plans": [],
                    "sources": [],
                    "warnings": warnings,
                    "model_version": MODEL_VERSION,
                    "input_hash": key,
                }
            )
        tr = spatial_projector(inv)
        xy = np.array([tr.transform(s.longitude, s.latitude) for s in inv.sites])
        anchors = [i for i, s in enumerate(inv.sites) if s.kind == "sensor"]
        if not np.isfinite(xy).all() or np.max(np.linalg.norm(xy, axis=1)) > 100000:
            raise ValueError("Spatial coverage requires a local study within 100 km")
        targets = xy[
            [
                i
                for i, s in enumerate(inv.sites)
                if s.kind == "candidate"
                and s.allowed
                and s.power
                and s.access
                and inv.settings.window in s.windows
            ]
        ]

        def covered(indices):
            points = indices + anchors
            return (
                float(
                    np.exp(
                        -np.linalg.norm(
                            targets[:, None, :] - xy[points][None, :, :], axis=-1
                        ).min(axis=1)
                        / 400
                    ).mean()
                )
                if points and len(targets)
                else 0.0
            )

        baseline = covered([])
        score = lambda indices: max(0.0, covered(indices) - baseline)
        interpretation = "Increment in mean spatial coverage over all permissible candidate targets (independent of budget); exp(-distance/400m). Descriptive geometry, not pollution prediction."
        if reason:
            warnings.append("Source reconstruction unavailable: " + reason)
    _, quality = measurement_quality(inv)
    if quality["conflicting_keys"]:
        warnings.append(
            f"Excluded {len(quality['conflicting_keys'])} conflicting sensor/time groups; resolve originals before interpreting inference."
        )
    if e is not None and e["rows_input"] > e["rows_used"]:
        warnings.append(
            f"Used {e['rows_used']} of {e['rows_input']} usable rows with balanced per-sensor sampling; full-window weather and geometry were checked."
        )
    rng = np.random.default_rng(inv.settings.seed)
    plans = []

    def pack(method, selected):
        return {
            "method": method,
            "site_ids": [inv.sites[i].id for i in selected],
            "cost": sum(inv.sites[i].cost for i in selected),
            "score": score(selected),
            "equipment": len(selected),
            "window": inv.settings.window,
        }

    optimized = select_plan(inv, "information", score, eligible, rng)
    # Exact small-case search makes objective/cost tradeoffs independently inspectable.
    exact = len(eligible) <= 12
    feasible_count, ties = 0, 0
    if exact:
        best_score = -1.0
        for k in range(min(inv.settings.equipment_limit, len(eligible)) + 1):
            for subset in combinations(eligible, k):
                if sum(inv.sites[i].cost for i in subset) <= inv.settings.budget + 1e-9:
                    feasible_count += 1
                    val = score(list(subset))
                    if val > best_score + 1e-10:
                        best_score, optimized, ties = val, list(subset), 1
                    elif abs(val - best_score) <= 1e-10:
                        ties += 1
    plans.append(
        pack("Optimized" if not exact else "Optimized · exhaustive", optimized)
    )
    plans.append(
        pack("Spatial spread", select_plan(inv, "spread", score, eligible, rng))
    )
    randoms = [
        pack(
            "Random",
            select_plan(
                inv,
                "random",
                score,
                eligible,
                np.random.default_rng(inv.settings.seed + i),
            ),
        )
        for i in range(20)
    ]
    random_plan = randoms[0] | {
        "method": "Random · seed " + str(inv.settings.seed),
        "mean_score": float(np.mean([p["score"] for p in randoms])),
        "min_score": min(p["score"] for p in randoms),
        "max_score": max(p["score"] for p in randoms),
        "seeds": 20,
    }
    plans.append(random_plan)
    if e is not None:
        flow = flow_vector(e["wind"])
        center = np.mean(e["source_xy"], axis=0)

        def wind_priority(i):
            delta = e["site_xy"][i] - center
            return -(
                float(delta @ flow)
                - abs(float(flow[0] * delta[1] - flow[1] * delta[0]))
            )

        ranked = sorted(eligible, key=wind_priority)
        plans.append(
            pack("Wind corridor", select_plan(inv, "wind", score, ranked, rng))
        )
    if not exact:
        best = max(plans, key=lambda p: (p["score"], -p["cost"], -p["equipment"]))
        indices = [i for i, s in enumerate(inv.sites) if s.id in best["site_ids"]]
        if best["score"] <= 1e-10:
            indices = []
        optimized = indices
        plans[0] = pack("Optimized · best heuristic", indices) | {
            "origin_method": best["method"]
        }
    sources = (
        []
        if e is None
        else [
            {
                "id": f"S{i + 1}",
                **p.model_dump(),
                "weight": float(e["location_weights"][i]),
            }
            for i, p in enumerate(inv.source_locations)
        ]
    )
    entropy = (
        None
        if e is None
        else float(
            -np.sum(
                e["location_weights"]
                * np.log(np.maximum(e["location_weights"], 1e-300))
            )
        )
    )
    if e and e["standardized_residual_rms"] > 3:
        warnings.append(
            "MODEL MISMATCH: covariance-standardized residual RMS exceeds 3. Single-source model may be inadequate; this is a heuristic, not a calibrated test; do not interpret sharp weights as accuracy."
        )
    result = {
        "status": "ok" if optimized else "uninformative" if eligible else "infeasible",
        "reason": None
        if optimized
        else "Feasible candidates have no distinguishable utility above the 1e-10 numerical tie tolerance; this is not an access or budget failure."
        if eligible
        else "No feasible plan: check budget, permission, power, access, supported geometry and window.",
        "plans": plans,
        "sources": sources,
        "interpretation": interpretation,
        "warnings": warnings,
        "model_version": MODEL_VERSION,
        "input_hash": key,
        "eligible_sites": len(eligible),
        "exact_search": exact,
        "feasible_subsets": feasible_count if exact else None,
        "ties": ties if exact else None,
        "entropy_nats": entropy,
        "fitted_rmse_ug_m3": None if e is None else e["rmse"],
        "standardized_residual_rms": None
        if e is None
        else e["standardized_residual_rms"],
        "rows_used": 0 if e is None else e["rows_used"],
        "rows_input": 0 if e is None else e["rows_input"],
        "quality": quality,
        "scenario_count": 0 if e is None else e["scenario_count"],
        "runtime_ms": round((time.perf_counter() - started) * 1000, 2),
    }
    return json.dumps(result, allow_nan=False)
