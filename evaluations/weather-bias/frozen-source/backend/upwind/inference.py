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
from scipy.stats import qmc, truncnorm
from .numerics import projector, plume
from .quality import measurement_quality, select_rows
from .campaign import observed_weather, assignment
from .weather_evidence import weather_grid, WEATHER_CONFIG, wrap

MODEL_VERSION = "plume-weather-0.5.0"
CONFIG = {
    "weather_bias": WEATHER_CONFIG,
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


def plume_columns(
    receptors, sources, speeds, directions, offsets, height, receptor_height
):
    """Exact unit-strength columns, bounded temporary broadcast arrays.

    Retain the required design matrix, but never materialize every source ×
    receptor coordinate difference and exponential temporary at once.
    """
    result = np.empty((len(receptors), len(sources)))
    for begin in range(0, len(sources), 2048):
        block = slice(begin, begin + 2048)
        result[:, block] = plume(
            receptors[None],
            sources[block, None],
            1.0,
            speeds[None],
            directions[None] + offsets[block, None],
            height,
            receptor_height,
        ).T
    return result


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


def _base_cov(
    x,
    t,
    ids,
    other_x,
    other_t,
    other_ids,
    noise,
    window_ids=None,
    other_window_ids=None,
    bg_t=None,
    other_bg_t=None,
):
    distance = np.linalg.norm(x[:, None] - other_x[None, :], axis=-1)
    dt = np.abs(t[:, None] - other_t[None, :])
    mask = (
        1.0
        if window_ids is None
        else (window_ids[:, None] == other_window_ids[None, :])
    )
    trend_t = t if bg_t is None else bg_t
    other_trend_t = other_t if other_bg_t is None else other_bg_t
    return (
        noise**2
        * np.exp(
            -distance / CONFIG["spatial_scale_m"] - dt / CONFIG["temporal_scale_s"]
        )
        + CONFIG["instrument_bias_sd_ug_m3"] ** 2 * (ids[:, None] == other_ids[None, :])
        + CONFIG["background_sd_ug_m3"] ** 2 * mask
        + CONFIG["background_trend_sd_ug_m3_hour"] ** 2
        * np.outer(trend_t / 3600, other_trend_t / 3600)
        * mask
    )


def fit(
    inv,
    diagnostics=True,
    *,
    background_only=False,
    wind_uncertainty=True,
    spatial_order=None,
    weather_bias_sd=None,
    weather_step_deg=None,
):
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
    order = (2 if inv.study_windows else 1) if spatial_order is None else spatial_order
    if order not in (1, 2):
        raise ValueError("Spatial quadrature order must be one or two")
    if order == 2 and continuous:
        half = (cells[:, 2:] - cells[:, :2]) / (2 * np.sqrt(3))
        integration_xy = np.concatenate(
            [
                source_xy[:, None, :]
                + half[:, None, :] * np.array([[-1, -1], [-1, 1], [1, -1], [1, 1]])
            ],
            axis=1,
        ).reshape(-1, 2)
        integration_cell = np.repeat(np.arange(len(cells)), 4)
        integration_prior = np.repeat(cell_prior / 4, 4)
    else:
        order = 1
        integration_xy = source_xy
        integration_cell = np.arange(len(cells))
        integration_prior = cell_prior
    corners = np.concatenate(
        [cells[:, [0, 1]], cells[:, [0, 3]], cells[:, [2, 1]], cells[:, [2, 3]]]
    )
    all_met, wind, speed = observed_weather(inv, usable, tr)
    met_lookup = {(m.sensor_id, m.timestamp): w for m, w in zip(usable, all_met)}
    labels, _ = assignment(inv, [r.timestamp for r in usable])
    groups = {
        (r.sensor_id, r.timestamp): f"{int(w)}:{len(r.sensor_id)}:{r.sensor_id}"
        for r, w in zip(usable, labels)
    }
    rows = select_rows(
        usable,
        inv.settings.inference_limit,
        inv.settings.selection_seed,
        group_key=(lambda r: groups[r.sensor_id, r.timestamp])
        if inv.study_windows
        else None,
    )
    met = [met_lookup[m.sensor_id, m.timestamp] for m in rows]
    x, stamps = xy(rows), seconds(rows)
    center_time = float((seconds(usable).min() + seconds(usable).max()) / 2)
    t = stamps - center_time
    window_ids, bg_t = assignment(inv, [r.timestamp for r in rows])
    if not inv.study_windows:
        window_ids, bg_t = None, None
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
    covariance = _base_cov(
        x,
        t,
        ids,
        x,
        t,
        ids,
        inv.settings.noise_ug_m3,
        window_ids,
        window_ids,
        bg_t,
        bg_t,
    ) + np.diag(sigma**2)
    chol = np.linalg.cholesky(covariance)
    residual = y - CONFIG["background_mean_ug_m3"]
    white_y = solve_triangular(chol, residual, lower=True, check_finite=False)
    log_bg = -0.5 * (
        white_y @ white_y
        + 2 * np.log(np.diag(chol)).sum()
        + len(rows) * np.log(2 * np.pi)
    )
    if wind_uncertainty:
        offsets, offset_prior, raw_scales, raw_speed_prior, weather_summary = (
            weather_grid(
                inv, tr, all_met, bias_sd=weather_bias_sd, step_deg=weather_step_deg
            )
        )
    else:
        # Existing internal known-weather mathematical oracle, never used by API.
        offsets = np.array([0.0])
        offset_prior = np.array([1.0])
        raw_scales = (
            1
            + (np.array(CONFIG["speed_scales"]) - 1)
            * inv.settings.met_speed_fraction
            / 0.3
        )
        raw_speed_prior = np.array(CONFIG["speed_prior"])
        weather_summary = {
            "status": "diagnostic_fixed",
            "weather_warning": False,
            "direction_comparison_correction_deg": 0.0,
            "speed_comparison_factor": 1.0,
            "meaning": "Internal mathematical oracle: directional uncertainty disabled, not an operational weather verification.",
        }
    if (
        len(rows) * len(integration_xy) * len(offsets)
        > WEATHER_CONFIG["max_design_entries"]
    ):
        raise ValueError(
            "Weather uncertainty exceeds the supported numerical workload for this study size. Reduce maximum fitted readings or supply appropriate independent wind comparisons; all raw readings are retained."
        )
    nominal = np.array([w.wind_speed_m_s for w in all_met] + [speed])
    combined_scales = {}
    for value, prob in zip(raw_scales, raw_speed_prior):
        combined_scales[value] = combined_scales.get(value, 0) + prob
    scale_prior = [
        (s, p)
        for s, p in combined_scales.items()
        if np.all((nominal * s >= 0.8) & (nominal * s <= 8))
    ]
    scale_z = sum(p for _, p in scale_prior)
    if not scale_z:
        raise ValueError(
            "No weather speed-bias scenarios remain within supported transport speeds."
        )
    configs = np.array(
        [
            (i, offset, s)
            for i in range(len(integration_xy))
            for offset in offsets
            for s, _ in scale_prior
        ]
    )
    integration_index = configs[:, 0].astype(int)
    cell_index = integration_cell[integration_index]
    dw, scale = configs[:, 1], configs[:, 2]
    # C(Q,u*s)=C(Q/s,u). Integrate a HalfNormal(tau/s) effective
    # strength on each unique location/direction column, rather than solving
    # three identical scaled design matrices. The original prior mass remains.
    base_configs = np.array(
        [(i, offset) for i in range(len(integration_xy)) for offset in offsets]
    )
    base_index = np.repeat(np.arange(len(base_configs)), len(scale_prior))
    base_integration = base_configs[:, 0].astype(int)
    base_direction = base_configs[:, 1]
    weather_prior = np.array(
        [p / scale_z * op for op in offset_prior for _, p in scale_prior]
    )
    prior = (integration_prior[:, None] * weather_prior).ravel()
    g = plume_columns(
        x,
        integration_xy[base_integration],
        np.array([w.wind_speed_m_s for w in met]),
        np.array([w.wind_from_deg for w in met]),
        base_direction,
        inv.settings.source_height_m,
        inv.settings.receptor_height_m,
    )
    white_g = solve_triangular(chol, g, lower=True, check_finite=False)
    tau = CONFIG["strength_halfnormal_scale_ug_s"] / scale
    precision = 1 / tau**2 + np.sum(white_g**2, axis=0)[base_index]
    q_sd = 1 / np.sqrt(precision)
    q_mean = (white_g.T @ white_y)[base_index] / precision
    del white_g
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

    def prediction_parts(
        points, timestamps=None, sensor_ids=None, weather=None, uncertainties=None
    ):
        """Exact conditional predictive moments and residual strength signatures.

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
        if timestamps is None and inv.study_windows:
            timestamps = [max(r.timestamp for r in usable)] * count
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
        future_windows, future_bg_t = (
            assignment(inv, timestamps) if inv.study_windows else (None, None)
        )
        future_ids = np.array(
            sensor_ids
            if sensor_ids is not None
            else [f"new-instrument-{i}" for i in range(count)]
        )
        cross = _base_cov(
            z,
            future_t,
            future_ids,
            x,
            t,
            ids,
            inv.settings.noise_ug_m3,
            future_windows,
            window_ids,
            future_bg_t,
            bg_t,
        )
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
                future_windows,
                future_windows,
                future_bg_t,
                future_bg_t,
            )
            + np.diag(future_sigma**2)
            - cross @ cho_solve((chol, True), cross.T, check_finite=False)
        )
        base_cov = (base_cov + base_cov.T) / 2
        base_mean = CONFIG["background_mean_ug_m3"] + cross @ inv_y
        if weather is None and inv.study_windows:
            from types import SimpleNamespace

            queries = [
                SimpleNamespace(latitude=p.latitude, longitude=p.longitude, timestamp=s)
                for p, s in zip(pts, timestamps)
            ]
            weather, _, _ = observed_weather(inv, queries, tr, require_sensors=False)
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
            plume_columns(
                z,
                integration_xy[base_integration],
                speeds,
                angles,
                base_direction,
                inv.settings.source_height_m,
                inv.settings.receptor_height_m,
            ).T
            - (cross @ inv_g).T
        )
        target_g = target_g[base_index]
        means = np.vstack((base_mean, base_mean + qm[:, None] * target_g))
        return means, base_cov, target_g

    def predictive(
        points, timestamps=None, sensor_ids=None, weather=None, uncertainties=None
    ):
        means, base_cov, target_g = prediction_parts(
            points, timestamps, sensor_ids, weather, uncertainties
        )
        covariances = np.concatenate(
            (
                base_cov[None],
                base_cov[None]
                + qv[:, None, None] * target_g[:, :, None] * target_g[:, None, :],
            )
        )
        return means, covariances

    def prediction_moments(
        points, timestamps=None, sensor_ids=None, weather=None, uncertainties=None
    ):
        """Exact total first/second moments of the declared posterior mixture.

        Avoid allocating K×d×d component covariances. This supports deterministic
        Bayes-linear prediction design; it is not exact nonlinear Bayes risk.
        """
        means, base_cov, target_g = prediction_parts(
            points, timestamps, sensor_ids, weather, uncertainties
        )
        average = weights @ means
        dev = means - average
        total = (
            base_cov
            + (dev.T * weights) @ dev
            + (target_g.T * (weights[1:] * qv)) @ target_g
        )
        return average, (total + total.T) / 2

    def predictive_draws(
        points,
        timestamps=None,
        sensor_ids=None,
        weather=None,
        uncertainties=None,
        *,
        samples=2048,
        seed=0,
    ):
        """Sobol samples of the exact truncated-strength conditional distribution.

        The approximation is finite geographic/weather quadrature and finite
        integration, not Gaussian moment matching of source-strength tails.
        """
        if samples < 2 or samples > 8192 or samples & (samples - 1):
            raise ValueError(
                "Predictive samples must be a power of two between2 and8192"
            )
        means, base, target_g = prediction_parts(
            points, timestamps, sensor_ids, weather, uncertainties
        )
        d = len(points)
        u = qmc.Sobol(d=d + 2, scramble=True, seed=seed).random_base2(
            int(np.log2(samples))
        )
        u = np.clip(u, np.finfo(float).eps, 1 - np.finfo(float).eps)
        cumulative = np.cumsum(weights)
        cumulative[-1] = 1
        component = np.searchsorted(cumulative, u[:, 0])
        draw = means[component].copy()
        from scipy.special import ndtri

        draw += ndtri(u[:, 1 : d + 1]) @ np.linalg.cholesky(base).T
        source = component > 0
        k = component[source] - 1
        qdraw = truncnorm.ppf(
            u[source, -1], -q_mean[k] / q_sd[k], np.inf, loc=q_mean[k], scale=q_sd[k]
        )
        draw[source] += (qdraw - qm[k])[:, None] * target_g[k]
        return draw

    def predictive_log_density(
        observed,
        points,
        timestamps=None,
        sensor_ids=None,
        weather=None,
        uncertainties=None,
    ):
        """Exact marginal densities of the truncated-strength mixture.

        Gaussian conditioning gives p(y|q>0)=p(y)*P(q>0|y)/P(q>0).
        These are marginal scores, not a product likelihood for correlated rows.
        """
        means, base, h = prediction_parts(
            points, timestamps, sensor_ids, weather, uncertainties
        )
        values = np.asarray(observed, float)
        v = np.diag(base)[None]
        bg_log = -0.5 * (
            np.log(2 * np.pi * np.diag(base)) + (values - means[0]) ** 2 / np.diag(base)
        )
        result = np.log(max(weights[0], np.finfo(float).tiny)) + bg_log
        for begin in range(0, len(q_mean), 8192):
            s = slice(begin, begin + 8192)
            hs = h[s]
            qm0 = q_mean[s, None]
            qs = q_sd[s, None]
            variance = v + qs**2 * hs**2
            residual_future = values[None] - means[0] - qm0 * hs
            conditional_m = qm0 + qs**2 * hs / variance * residual_future
            conditional_sd = qs * np.sqrt(v / variance)
            source_log = (
                -0.5 * (np.log(2 * np.pi * variance) + residual_future**2 / variance)
                + log_ndtr(conditional_m / conditional_sd)
                - log_ndtr(qm0 / qs)
            )
            result = np.logaddexp(
                result,
                logsumexp(
                    np.log(np.maximum(weights[1:][s], np.finfo(float).tiny))[:, None]
                    + source_log,
                    axis=0,
                ),
            )
        return result

    latent_cov = covariance - np.diag(sigma**2)
    base_average = CONFIG["background_mean_ug_m3"] + latent_cov @ inv_y
    effective_mean_mass = np.bincount(
        base_index, weights=weights[1:] * qm, minlength=len(base_configs)
    )
    average = (
        base_average
        + g @ effective_mean_mass
        - latent_cov @ (inv_g @ effective_mean_mass)
    )
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
    component_keys = ["background"] + [
        f"cell-{int(i):04d}-wind-{o:+07.2f}-speed-{s:.2f}" for i, o, s in configs
    ]
    if len(set(component_keys)) != len(component_keys):
        # Very small but valid user speed uncertainty can collide at two decimal
        # places. Preserve existing integration order otherwise; never merge
        # scientifically distinct scenarios merely to make display keys unique.
        component_keys = ["background"] + [
            f"node-{int(i)}-wind-{float(o).hex()}-speed-{float(s).hex()}"
            for i, o, s in configs
        ]
    direction_mass = conditional.reshape(
        len(integration_xy), len(offsets), len(scale_prior)
    ).sum(axis=(0, 2))
    node_direction = conditional.reshape(
        len(integration_xy), len(offsets), len(scale_prior)
    ).sum(axis=2)
    direction_locations = np.divide(
        node_direction.T @ integration_xy,
        direction_mass[:, None],
        out=np.zeros((len(offsets), 2)),
        where=direction_mass[:, None] > 0,
    )
    wind_order = np.argsort(-direction_mass, kind="stable")
    retained = wind_order[
        : int(np.searchsorted(np.cumsum(direction_mass[wind_order]), 0.9)) + 1
    ]
    weather_summary["pollution_conditioned_offset_mean_deg"] = float(
        np.rad2deg(np.angle(np.sum(direction_mass * np.exp(1j * np.deg2rad(offsets)))))
    )
    weather_summary["source_weather_location_span_m"] = float(
        np.linalg.norm(
            direction_locations[retained, None] - direction_locations[None, retained],
            axis=-1,
        ).max()
    )
    weather_summary["alternative_offsets"] = [
        {
            "direction_offset_deg": float(wrap(offsets[j])),
            "conditional_source_weight": float(direction_mass[j]),
        }
        for j in wind_order[:8]
    ]
    weather_summary["inferred_correction_meaning"] = (
        "Pollution-conditioned offset is model inference, not an independently measured wind correction. All source/weather components enter regions and plans."
    )
    e = {
        "meteorology": weather_summary,
        "weather_grid": {
            "offsets": offsets,
            "direction_prior": offset_prior,
            "speed_scales": np.array([s for s, _ in scale_prior]),
            "speed_prior": np.array([p / scale_z for _, p in scale_prior]),
        },
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
        "spatial_quadrature_order": order,
        "integration_points": len(integration_xy),
        "projection": tr,
        "predictive": predictive,
        "prediction_moments": prediction_moments,
        "predictive_draws": predictive_draws,
        "predictive_log_density": predictive_log_density,
        "window_count": len(np.unique(window_ids)) if window_ids is not None else 1,
        "met_uncertainty_provenance": inv.settings.met_uncertainty_provenance,
        "site_xy": site_xy,
        "wind": (wind + weather_summary["direction_comparison_correction_deg"]) % 360,
        "speed": speed * weather_summary["speed_comparison_factor"],
        "rows": rows,
        "rows_used": len(rows),
        "rows_input": len(usable),
        "rows_loaded": len(inv.measurements),
        "rows_excluded": quality["excluded_rows"] + quality["identical_duplicates"],
        "scenario_count": len(weights),
        "rmse": rmse,
        "component_keys": component_keys,
        "standardized_residual_rms": float(
            np.sqrt(np.mean(solve_triangular(chol, y - average, lower=True) ** 2))
        ),
        "candidate_supported": supported,
        "quality": quality,
        "profile_context": {
            "observed": y,
            "signatures": g,
            "times": t,
            "bg_times": bg_t,
            "window_ids": window_ids,
            "sigma": sigma,
            "sensor_ids": ids,
            "configs": base_configs,
            "source_cell_indices": integration_cell[base_integration],
        },
        "diagnostics": {
            "held_out_sensor": [],
            "predictive_warning": False,
            "method": "Not run: diagnostic refits disabled for this internal fit.",
        },
    }
    if diagnostics:
        e["diagnostics"] = sensor_diagnostics(inv, e, usable)
    e["diagnostics"]["weather_warning"] = weather_summary["weather_warning"]
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
    from .predictive_checks import screen

    return screen(inv, usable, fit)


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
        "meaning": "Conditional single-source area-quadrature mass; not a calibrated real-world geographic probability. Discrete anchors have no area.",
        "support": "Rectangle spanned by domain anchors, excluding unsupported near-field/distant cells at existing monitors"
        if fitted["continuous"]
        else "Discrete supported anchors (degenerate rectangle)",
        "area_m2": float(areas[chosen].sum()),
        "domain_area_m2": float(areas.sum()),
        "excluded_domain_area_m2": fitted["excluded_domain_area_m2"],
        "resolution_m": float(np.max(cells[:, 2:] - cells[:, :2])),
        "cells": result,
    }
