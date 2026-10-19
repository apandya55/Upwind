"""Background versus single-release inversion with integrated linear nuisance terms.

The source prior is half-normal, not an optimized positive point estimate. A
rank-one Gaussian update and a truncation normalizer integrate it analytically.
Geographic integration uses area-weighted rectangular cells, not named fixtures.
No truth, fixture labels, future observations or random evaluation seeds enter here.
"""

from datetime import datetime
import numpy as np
from scipy.linalg import solve_triangular, cho_solve
from scipy.special import log_ndtr, logsumexp, erfcx, ndtr
from .numerics import projector, plume
from .quality import measurement_quality, select_rows
from .weather import matched_weather

MODEL_VERSION = "plume-mixture-0.3.0"
CONFIG = {
    "source_prior": 0.5,
    "strength_halfnormal_scale_ug_s": 30000.0,
    "background_mean_ug_m3": 10.0,
    "background_sd_ug_m3": 20.0,
    "background_trend_sd_ug_m3_hour": 10.0,
    "instrument_bias_sd_ug_m3": 1.0,
    "spatial_scale_m": 150.0,
    "temporal_scale_s": 600.0,
    "wind_offsets_deg": [-45, -30, -15, 0, 15, 30, 45],
    "wind_offset_sd_deg": 20.0,
    "speed_scales": [0.7, 1.0, 1.3],
    "speed_prior": [0.25, 0.5, 0.25],
    "cell_target_m": 20.0,
    "max_cells_axis": 24,
    "sensor_check_tail": 0.01,
}


def seconds(rows):
    return np.array([datetime.fromisoformat(r.timestamp).timestamp() for r in rows])


def source_cells(points):
    """Uniform area prior on the rectangle spanned by declared domain anchors.

    Degenerate anchors retain an explicit discrete model, never invented area.
    Midpoint quadrature approximates a continuous integral; cell resolution is
    reported, and cell membership does not imply a calibrated geographic region.
    """
    low, high = points.min(axis=0), points.max(axis=0)
    if np.any(high - low < 1):
        return (
            points.copy(),
            np.column_stack((points, points)),
            np.ones(len(points)) / len(points),
            False,
        )
    nx, ny = np.minimum(
        CONFIG["max_cells_axis"],
        np.maximum(1, np.ceil((high - low) / CONFIG["cell_target_m"])),
    ).astype(int)
    xs, ys = np.linspace(low[0], high[0], nx + 1), np.linspace(low[1], high[1], ny + 1)
    cells = np.array(
        [[xs[i], ys[j], xs[i + 1], ys[j + 1]] for i in range(nx) for j in range(ny)]
    )
    centers = (cells[:, :2] + cells[:, 2:]) / 2
    return centers, cells, np.full(len(cells), 1 / len(cells)), True


def positive_normal_moments(mean, sd):
    """Moments of N(mean,sd²) conditional on positivity, stable in the tail."""
    mean, sd = np.broadcast_arrays(
        np.asarray(mean, dtype=float), np.asarray(sd, dtype=float)
    )
    if not np.isfinite(mean).all() or not np.isfinite(sd).all() or np.any(sd <= 0):
        raise ValueError(
            "Finite normal mean and positive finite standard deviation required"
        )
    z = mean / sd
    ratio = np.empty_like(z)
    negative = z < 0
    ratio[negative] = np.sqrt(2 / np.pi) / erfcx(-z[negative] / np.sqrt(2))
    ratio[~negative] = np.exp(
        -0.5 * z[~negative] ** 2 - 0.5 * np.log(2 * np.pi) - log_ndtr(z[~negative])
    )
    m = np.asarray(sd * (z + ratio)).copy()
    v = np.asarray(sd**2 * (1 - z * ratio - ratio**2)).copy()
    # Avoid subtracting nearly equal large terms in the far negative tail.
    tail = z < -20
    a = -z[tail]
    m[tail] = sd[tail] * (1 / a - 2 / a**3 + 10 / a**5 - 74 / a**7)
    v[tail] = sd[tail] ** 2 * (1 / a**2 - 6 / a**4 + 50 / a**6 - 518 / a**8)
    return m, np.maximum(v, 0)


def _base_cov(x, t, ids, other_x, other_t, other_ids, noise):
    distance = np.linalg.norm(x[:, None] - other_x[None, :], axis=-1)
    dt = np.abs(t[:, None] - other_t[None, :])
    return (
        noise**2
        * np.exp(
            -distance / CONFIG["spatial_scale_m"] - dt / CONFIG["temporal_scale_s"]
        )
        + CONFIG["instrument_bias_sd_ug_m3"] ** 2 * (ids[:, None] == other_ids[None, :])
        + CONFIG["background_sd_ug_m3"] ** 2
        + CONFIG["background_trend_sd_ug_m3_hour"] ** 2
        * np.outer(t / 3600, other_t / 3600)
    )


def fit(inv, diagnostics=True, *, background_only=False, wind_uncertainty=True):
    if not all(
        (
            inv.assumptions.steady,
            inv.assumptions.open_terrain,
            inv.assumptions.local_weather,
        )
    ):
        raise ValueError(
            "Confirm steady conditions, open terrain, and representative local weather to enable experimental reconstruction."
        )
    usable, quality = measurement_quality(inv)
    if len({m.sensor_id for m in usable}) < 2:
        raise ValueError(
            "At least two distinct sensors with usable readings are required for scenario comparison."
        )
    if len(inv.source_locations) < 2:
        raise ValueError("Mark at least two source-domain anchors (maximum 25).")
    anchors = inv.source_locations
    tr = projector(
        float(np.mean(sorted(p.latitude for p in anchors))),
        float(np.mean(sorted(p.longitude for p in anchors))),
    )

    def xy(points):
        return np.array(
            [tr.transform(p.longitude, p.latitude) for p in points]
        ).reshape(-1, 2)

    anchor_xy, all_xy, site_xy = xy(anchors), xy(usable), xy(inv.sites)
    if (
        np.linalg.norm(all_xy, axis=1).max() > 3000
        or np.linalg.norm(anchor_xy, axis=1).max() > 1500
    ):
        raise ValueError(
            "Study area exceeds supported short-range geometry (3 km receptors, 1.5 km source radius)."
        )
    pair = np.linalg.norm(anchor_xy[:, None] - anchor_xy[None, :], axis=-1)
    if np.any(pair[np.triu_indices(len(anchors), 1)] < 1):
        raise ValueError("Source hypothesis locations must be at least 1 m apart")
    source_xy, cells, cell_prior, continuous = source_cells(anchor_xy)
    original_area = float(np.prod(cells[:, 2:] - cells[:, :2], axis=1).sum())
    supported_cells = np.ones(len(cells), dtype=bool)
    # Known sensor coordinates are design information, even during a sensor-block
    # holdout. Fixing this support prevents validation from changing the location
    # prior merely because that sensor's concentrations were withheld.
    known_sensor_xy = xy([s for s in inv.sites if s.kind == "sensor"])
    for start in range(0, len(known_sensor_xy), 128):
        chunk = known_sensor_xy[start : start + 128]
        closest = np.maximum(
            np.maximum(
                cells[None, :, :2] - chunk[:, None], chunk[:, None] - cells[None, :, 2:]
            ),
            0,
        )
        supported_cells &= np.all(np.linalg.norm(closest, axis=-1) >= 20, axis=0)
    for start in range(0, len(all_xy), 128):
        chunk = all_xy[start : start + 128]
        closest = np.maximum(
            np.maximum(
                cells[None, :, :2] - chunk[:, None], chunk[:, None] - cells[None, :, 2:]
            ),
            0,
        )
        farthest = np.maximum(
            np.abs(chunk[:, None] - cells[None, :, :2]),
            np.abs(chunk[:, None] - cells[None, :, 2:]),
        )
        supported_cells &= np.all(
            (np.linalg.norm(closest, axis=-1) >= 20)
            & (np.linalg.norm(farthest, axis=-1) <= 3000),
            axis=0,
        )
    if not supported_cells.any():
        raise ValueError(
            "No source-domain cells have every observation/source pair between 20 m and 3 km; unsupported pairs are not zero evidence"
        )
    # Numerical support is explicit. Excluded area is reported, not reassigned
    # zero likelihood or silently treated as impossible physical source location.
    source_xy, cells, cell_prior = (
        source_xy[supported_cells],
        cells[supported_cells],
        cell_prior[supported_cells],
    )
    cell_prior /= cell_prior.sum()
    corners = np.concatenate(
        [cells[:, [0, 1]], cells[:, [0, 3]], cells[:, [2, 1]], cells[:, [2, 3]]]
    )
    all_met, wind, speed = matched_weather(inv, usable, tr)
    met_lookup = {(m.sensor_id, m.timestamp): w for m, w in zip(usable, all_met)}
    rows = select_rows(
        usable, inv.settings.inference_limit, inv.settings.selection_seed
    )
    met = [met_lookup[m.sensor_id, m.timestamp] for m in rows]
    x, stamps = xy(rows), seconds(rows)
    center_time = float((seconds(usable).min() + seconds(usable).max()) / 2)
    t = stamps - center_time
    ids = np.array([m.sensor_id for m in rows])
    sigma = np.array(
        [
            m.uncertainty_ug_m3
            if m.uncertainty_ug_m3 is not None
            else inv.settings.noise_ug_m3
            for m in rows
        ]
    )
    y = np.array([m.pm25_ug_m3 for m in rows])
    covariance = _base_cov(x, t, ids, x, t, ids, inv.settings.noise_ug_m3) + np.diag(
        sigma**2
    )
    chol = np.linalg.cholesky(covariance)
    residual = y - CONFIG["background_mean_ug_m3"]
    white_y = solve_triangular(chol, residual, lower=True, check_finite=False)
    log_bg = -0.5 * (
        white_y @ white_y
        + 2 * np.log(np.diag(chol)).sum()
        + len(rows) * np.log(2 * np.pi)
    )
    offsets = np.array(CONFIG["wind_offsets_deg"] if wind_uncertainty else [0.0])
    offset_prior = np.exp(-0.5 * (offsets / CONFIG["wind_offset_sd_deg"]) ** 2)
    offset_prior /= offset_prior.sum()
    nominal = np.array([w.wind_speed_m_s for w in all_met] + [speed])
    scale_prior = [
        (s, p)
        for s, p in zip(CONFIG["speed_scales"], CONFIG["speed_prior"])
        if np.all((nominal * s >= 0.8) & (nominal * s <= 8))
    ]
    scale_z = sum(p for _, p in scale_prior)
    configs = np.array(
        [
            (i, offset, s)
            for i in range(len(source_xy))
            for offset in offsets
            for s, _ in scale_prior
        ]
    )
    cell_index = configs[:, 0].astype(int)
    dw, scale = configs[:, 1], configs[:, 2]
    weather_prior = np.array(
        [p / scale_z * op for op in offset_prior for _, p in scale_prior]
    )
    prior = (cell_prior[:, None] * weather_prior).ravel()
    g = plume(
        x[None],
        source_xy[cell_index, None],
        1.0,
        np.array([w.wind_speed_m_s for w in met])[None] * scale[:, None],
        np.array([w.wind_from_deg for w in met])[None] + dw[:, None],
    ).T
    white_g = solve_triangular(chol, g, lower=True, check_finite=False)
    tau = CONFIG["strength_halfnormal_scale_ug_s"]
    precision = 1 / tau**2 + np.sum(white_g**2, axis=0)
    q_sd = 1 / np.sqrt(precision)
    q_mean = (white_g.T @ white_y) / precision
    log_source = (
        log_bg
        - 0.5 * np.log(precision * tau**2)
        + 0.5 * (q_mean / q_sd) ** 2
        + np.log(2)
        + log_ndtr(q_mean / q_sd)
    )
    qm, qv = positive_normal_moments(q_mean, q_sd)
    log_mass = np.r_[
        log_bg + np.log1p(-CONFIG["source_prior"]),
        log_source + np.log(prior) + np.log(CONFIG["source_prior"]),
    ]
    if background_only:
        log_mass[1:] = -np.inf
    weights = np.exp(log_mass - logsumexp(log_mass))
    weights /= weights.sum()
    source_probability = float(np.clip(weights[1:].sum(), 0, 1))
    # Conditional source distribution remains defined even if its family mass underflows.
    conditional = np.exp(
        log_source + np.log(prior) - logsumexp(log_source + np.log(prior))
    )
    cell_weights = np.bincount(
        cell_index, weights=conditional, minlength=len(source_xy)
    )
    nearest_anchor = np.argmin(
        np.linalg.norm(source_xy[:, None] - anchor_xy[None], axis=-1), axis=1
    )
    anchor_order = sorted(
        range(len(anchors)), key=lambda i: (anchors[i].latitude, anchors[i].longitude)
    )
    anchor_rank = np.empty(len(anchors), dtype=int)
    anchor_rank[anchor_order] = np.arange(len(anchors))
    groups = np.r_[0, anchor_rank[nearest_anchor[cell_index]] + 1]
    anchor_weights = np.bincount(
        nearest_anchor, weights=cell_weights, minlength=len(anchors)
    )
    inv_g = cho_solve((chol, True), g, check_finite=False)
    inv_y = cho_solve((chol, True), residual, check_finite=False)

    def predictive(
        points, timestamps=None, sensor_ids=None, weather=None, uncertainties=None
    ):
        """Conditional predictive moments; half-normal posterior is moment matched.

        Future background, model error and same-instrument bias are conditioned
        on history. New measurement errors are independent. No future weather is
        fetched: caller must supply a scenario or uses the observed-window mean.
        """
        pts = [p if hasattr(p, "latitude") else type("Point", (), p)() for p in points]
        z = xy(pts)
        count = len(z)
        closest_target = np.maximum(
            np.maximum(
                cells[None, :, :2] - z[:, None], z[:, None] - cells[None, :, 2:]
            ),
            0,
        )
        farthest_target = np.maximum(
            np.abs(z[:, None] - cells[None, :, :2]),
            np.abs(z[:, None] - cells[None, :, 2:]),
        )
        if np.any(np.linalg.norm(closest_target, axis=-1) < 20 - 1e-7) or np.any(
            np.linalg.norm(farthest_target, axis=-1) > 3000 + 1e-7
        ):
            raise ValueError(
                "Predictive receptors must have every source-domain pair between 20 m and 3 km"
            )
        future_t = (
            np.zeros(count)
            if timestamps is None
            else np.array(
                [
                    datetime.fromisoformat(s).timestamp() - center_time
                    for s in timestamps
                ]
            )
        )
        future_ids = np.array(
            sensor_ids
            if sensor_ids is not None
            else [f"new-instrument-{i}" for i in range(count)]
        )
        cross = _base_cov(z, future_t, future_ids, x, t, ids, inv.settings.noise_ug_m3)
        future_sigma = np.asarray(
            uncertainties
            if uncertainties is not None
            else np.full(count, inv.settings.noise_ug_m3)
        )
        base_cov = (
            _base_cov(
                z,
                future_t,
                future_ids,
                z,
                future_t,
                future_ids,
                inv.settings.noise_ug_m3,
            )
            + np.diag(future_sigma**2)
            - cross @ cho_solve((chol, True), cross.T, check_finite=False)
        )
        base_cov = (base_cov + base_cov.T) / 2
        base_mean = CONFIG["background_mean_ug_m3"] + cross @ inv_y
        speeds = (
            np.array([w.wind_speed_m_s for w in weather])
            if weather is not None
            else np.full(count, speed)
        )
        angles = (
            np.array([w.wind_from_deg for w in weather])
            if weather is not None
            else np.full(count, wind)
        )
        target_g = (
            plume(
                z[None],
                source_xy[cell_index, None],
                1.0,
                speeds[None] * scale[:, None],
                angles[None] + dw[:, None],
            )
            - (cross @ inv_g).T
        )
        means = np.vstack((base_mean, base_mean + qm[:, None] * target_g))
        covariances = np.concatenate(
            (
                base_cov[None],
                base_cov[None]
                + qv[:, None, None] * target_g[:, :, None] * target_g[:, None, :],
            )
        )
        return means, covariances

    latent_cov = covariance - np.diag(sigma**2)
    base_average = CONFIG["background_mean_ug_m3"] + latent_cov @ inv_y
    average = base_average + (weights[1:] * qm) @ (g - latent_cov @ inv_g).T
    rmse = float(np.sqrt(np.mean((average - y) ** 2)))
    candidate_distance = np.linalg.norm(site_xy[:, None] - corners[None], axis=-1)
    closest_site = np.maximum(
        np.maximum(
            cells[None, :, :2] - site_xy[:, None], site_xy[:, None] - cells[None, :, 2:]
        ),
        0,
    )
    supported = (
        (np.linalg.norm(closest_site, axis=-1).min(axis=1) >= 20)
        & (candidate_distance.max(axis=1) <= 3000)
        if len(site_xy)
        else np.array([], dtype=bool)
    )
    e = {
        "weights": weights,
        "groups": groups,
        "location_weights": anchor_weights,
        "cell_weights": cell_weights,
        "source_probability": source_probability,
        "excluded_domain_area_m2": original_area
        - float(np.prod(cells[:, 2:] - cells[:, :2], axis=1).sum()),
        "source_xy": source_xy,
        "cells_xy": cells,
        "continuous": continuous,
        "projection": tr,
        "predictive": predictive,
        "site_xy": site_xy,
        "wind": wind,
        "speed": speed,
        "rows": rows,
        "rows_used": len(rows),
        "rows_input": len(usable),
        "rows_loaded": len(inv.measurements),
        "rows_excluded": quality["excluded_rows"] + quality["identical_duplicates"],
        "scenario_count": len(weights),
        "rmse": rmse,
        "component_keys": ["background"]
        + [f"cell-{int(i):04d}-wind-{o:+07.2f}-speed-{s:.2f}" for i, o, s in configs],
        "standardized_residual_rms": float(
            np.sqrt(np.mean(solve_triangular(chol, y - average, lower=True) ** 2))
        ),
        "candidate_supported": supported,
        "quality": quality,
        "diagnostics": {
            "held_out_sensor": [],
            "predictive_warning": False,
            "method": "Leave-one-sensor-out; Gaussian moments approximate the truncated-strength predictive mixture. Tail flags are uncalibrated screening diagnostics.",
        },
    }
    if diagnostics:
        e["diagnostics"] = sensor_diagnostics(inv, e, usable)
    return e


def mixture_intervals(weights, means, variances, level=0.9):
    """Equal-tail marginal intervals for the declared moment-matched mixture."""
    sd = np.sqrt(np.maximum(variances, 1e-12))
    lows, highs = (
        means.min(axis=0) - 10 * sd.max(axis=0),
        means.max(axis=0) + 10 * sd.max(axis=0),
    )
    answers = []
    for target in ((1 - level) / 2, (1 + level) / 2):
        lo, hi = lows.copy(), highs.copy()
        for _ in range(45):
            middle = (lo + hi) / 2
            cdf = weights @ ndtr((middle[None] - means) / sd)
            lo, hi = (
                np.where(cdf < target, middle, lo),
                np.where(cdf >= target, middle, hi),
            )
        answers.append((lo + hi) / 2)
    return tuple(answers)


def sensor_diagnostics(inv, full_fit, usable):
    checks = []
    ids = sorted({r.sensor_id for r in usable})
    if len(ids) < 3:
        return {
            "held_out_sensor": [],
            "predictive_warning": False,
            "method": "Unavailable: at least three sensors required to fit on two and hold out an entire sensor. No adequacy certificate.",
        }
    # Bound diagnostic cost; deterministic spatially separated sensor blocks.
    # Unchecked sensors are explicitly counted, never implied to be validated.
    selected_ids = [
        ids[i] for i in np.linspace(0, len(ids) - 1, min(6, len(ids)), dtype=int)
    ]
    for sensor in selected_ids:
        train = inv.model_copy(deep=True)
        train.measurements = [r for r in inv.measurements if r.sensor_id != sensor]
        held = select_rows(
            [r for r in usable if r.sensor_id == sensor],
            min(24, inv.settings.inference_limit),
            inv.settings.selection_seed,
        )
        try:
            trained = fit(train, diagnostics=False)
            met, _, _ = matched_weather(inv, held, trained["projection"])
            mu, cov = trained["predictive"](
                held,
                [r.timestamp for r in held],
                [r.sensor_id for r in held],
                met,
                [
                    r.uncertainty_ug_m3
                    if r.uncertainty_ug_m3 is not None
                    else inv.settings.noise_ug_m3
                    for r in held
                ],
            )
            var = np.diagonal(cov, axis1=1, axis2=2)
            values = np.array([r.pm25_ug_m3 for r in held])
            w = trained["weights"]
            low, high = mixture_intervals(w, mu, var)
            residual = values[None] - mu
            log_density = logsumexp(
                np.log(np.maximum(w, 1e-300))[:, None]
                - 0.5 * (np.log(2 * np.pi * var) + residual**2 / var),
                axis=0,
            )
            cdf = w @ ndtr(residual / np.sqrt(var))
            # Bonferroni per-study screen accounts for tested marginal predictions;
            # independence is not assumed, but Gaussian approximation is uncalibrated.
            flagged = bool(
                np.any(
                    2 * np.minimum(cdf, 1 - cdf)
                    < CONFIG["sensor_check_tail"] / (len(selected_ids) * len(held))
                )
            )
            checks.append(
                {
                    "sensor_id": sensor,
                    "rows": len(held),
                    "rmse_ug_m3": float(np.sqrt(np.mean((w @ mu - values) ** 2))),
                    "coverage90": float(np.mean((values >= low) & (values <= high))),
                    "mean_nlpd": float(-log_density.mean()),
                    "flagged": flagged,
                }
            )
        except ValueError as exc:
            checks.append(
                {
                    "sensor_id": sensor,
                    "rows": len(held),
                    "unavailable": str(exc),
                    "flagged": False,
                }
            )
    return {
        "held_out_sensor": checks,
        "predictive_warning": any(c["flagged"] for c in checks),
        "sensors_total": len(ids),
        "sensors_checked": len(selected_ids),
        "method": "Leave-one-sensor-out predictive screening, at most six sensor blocks and 24 readings per block. 1% Bonferroni marginal-tail screen on Gaussian-moment predictive mixtures; not field calibrated and not an adequacy certificate.",
    }


def region(fitted):
    w, cells = fitted["cell_weights"], fitted["cells_xy"]
    order = np.argsort(-w, kind="stable")
    chosen = order[: min(len(w), int(np.searchsorted(np.cumsum(w[order]), 0.9)) + 1)]
    areas = np.prod(cells[:, 2:] - cells[:, :2], axis=1)
    result = []
    for i in chosen:
        x0, y0, x1, y1 = cells[i]
        polygon = []
        for x, y in [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]:
            lon, lat = fitted["projection"].transform(x, y, direction="INVERSE")
            polygon.append({"latitude": float(lat), "longitude": float(lon)})
        result.append({"polygon": polygon, "weight": float(w[i])})
    return {
        "level": 0.9,
        "meaning": "Conditional single-source midpoint-quadrature mass; not a calibrated real-world geographic probability. Discrete anchors have no area.",
        "support": "Rectangle spanned by domain anchors, excluding unsupported near-field/distant cells at existing monitors"
        if fitted["continuous"]
        else "Discrete supported anchors (degenerate rectangle)",
        "area_m2": float(areas[chosen].sum()),
        "domain_area_m2": float(areas.sum()),
        "excluded_domain_area_m2": fitted["excluded_domain_area_m2"],
        "resolution_m": float(np.max(cells[:, 2:] - cells[:, :2])),
        "cells": result,
    }
