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
from .weather_evidence import joint_weather_grid, WEATHER_CONFIG, wrap
from .source_grid import subdivide, location_summary, posterior_region_structure
from .gaussian_design import grouped_design

MODEL_VERSION = "plume-robust-0.9.0"
PROTOCOL_VERSION = "UW-ENGINE-2026-09"
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
    "adaptive_target_mass": 0.9,
    "adaptive_max_parents": 96,
    "adaptive_min_width_m": 10.0,
    "domain_edge_fraction": 0.1,
    "domain_edge_mass_limit": 0.5,
    "max_components": 2000000,
    # A single fixed release-scale prior can move a location toward a
    # higher-concentration, lower-Q explanation. These factors are a declared
    # sensitivity diagnostic, not a second fitted prior.
    "strength_prior_sensitivity_factors": [0.1, 1.0, 10.0],
    "strength_prior_sensitivity_mean_shift_m": 100.0,
    "strength_prior_sensitivity_cell_tv": 0.25,
    # A humidity response is not corrected from PM2.5 alone.  This is a
    # sensor-specific random coefficient on the high-humidity excess and is
    # marginalized as covariance, preserving the recorded humidity value.
    "humidity_response_sd_ug_m3": 2.0,
    "humidity_threshold_percent": 70.0,
    "humidity_scale_percent": 20.0,
    "externality_pair_delta_chi2": 9.210340371976184,
    # Adjacent nested source/weather quadrature levels must satisfy every
    # tolerance before the posterior can receive source-supported status.
    "quadrature_policy": {
        "weather_steps_deg": [2.0, 1.0, 0.5],
        "max_levels": 3,
        "refine_target_mass": 0.9,
        "max_refined_parents_per_level": 96,
        "log_evidence_delta": 0.01,
        "source_probability_delta": 0.01,
        "cell_mass_tv": 0.05,
        "posterior_mean_delta_m": 10.0,
        "covariance_relative_delta": 0.05,
        "region_mass_delta": 0.02,
        "region_area_fraction_delta": 0.05,
        "weather_mass_tv": 0.05,
    },
}


def _humidity_design(values, expected_length):
    """Return the retained high-humidity covariate without inventing data.

    NaN is the in-memory representation of a missing humidity reading. Other
    non-finite values are malformed inputs and must not silently become a very
    large covariance term through ``nan_to_num``.
    """
    values = np.asarray(values, dtype=float)
    if values.shape != (expected_length,):
        raise ValueError("Humidity designs must match covariance coordinates")
    if np.any(np.isinf(values)):
        raise ValueError("Humidity values must be finite or missing")
    return np.maximum(
        (np.nan_to_num(values, nan=0.0) - CONFIG["humidity_threshold_percent"])
        / CONFIG["humidity_scale_percent"],
        0.0,
    )


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


def _strength_prior_sensitivity(
    *,
    log_bg,
    norm,
    dot,
    tau,
    base_index,
    base_integration,
    log_prior,
    integration_xy,
    integration_cell,
    cells,
    baseline_cell_weights,
    baseline_mean_xy,
    bounds,
    projection,
    factors=None,
):
    """Reweight the existing source mixture under declared strength scales.

    This is a sensitivity calculation, not a second fitted model.  The GLS
    norm/dot terms are unchanged; only the HalfNormal release-scale prior is
    multiplied by each declared factor.  Keeping the same source/weather
    components makes shifts attributable to the release prior rather than a
    changed grid or likelihood.
    """
    factors = np.asarray(
        CONFIG["strength_prior_sensitivity_factors"] if factors is None else factors,
        dtype=float,
    )
    if (
        factors.ndim != 1
        or len(factors) == 0
        or not np.isfinite(factors).all()
        or np.any(factors <= 0)
    ):
        raise ValueError("Strength-prior sensitivity factors must be finite and positive")
    norm = np.asarray(norm, dtype=float)
    dot = np.asarray(dot, dtype=float)
    tau = np.asarray(tau, dtype=float)
    base_index = np.asarray(base_index, dtype=int)
    base_integration = np.asarray(base_integration, dtype=int)
    log_prior = np.asarray(log_prior, dtype=float)
    if (
        norm.shape != dot.shape
        or tau.shape != base_index.shape
        or tau.shape != log_prior.shape
    ):
        raise ValueError("Strength-prior sensitivity arrays have incompatible shapes")
    integration_xy = np.asarray(integration_xy, dtype=float)
    integration_cell = np.asarray(integration_cell, dtype=int)
    baseline_cell_weights = np.asarray(baseline_cell_weights, dtype=float)
    baseline_mean_xy = np.asarray(baseline_mean_xy, dtype=float)
    if (
        integration_xy.ndim != 2
        or integration_xy.shape[1] != 2
        or integration_cell.shape != (len(integration_xy),)
        or base_integration.ndim != 1
        or np.any(base_index < 0)
        or np.any(base_index >= len(base_integration))
        or np.any(base_integration < 0)
        or np.any(base_integration >= len(integration_xy))
        or np.any(integration_cell < 0)
        or np.any(integration_cell >= len(cells))
        or baseline_cell_weights.shape != (len(cells),)
        or baseline_mean_xy.shape != (2,)
    ):
        raise ValueError("Incompatible source quadrature arrays")

    background_mass = log_bg + np.log1p(-CONFIG["source_prior"])
    rows = []
    baseline_factor = None
    for factor in factors:
        effective_tau = tau * factor
        precision = 1 / effective_tau**2 + norm[base_index]
        q_sd = 1 / np.sqrt(precision)
        q_mean = dot[base_index] / precision
        z = q_mean / q_sd
        log_source = (
            log_bg
            - 0.5 * np.log(precision * effective_tau**2)
            + 0.5 * z**2
            + np.log(2)
            + log_ndtr(z)
        )
        source_log_mass = log_source + log_prior + np.log(CONFIG["source_prior"])
        log_mass = np.r_[background_mass, source_log_mass]
        weights = np.exp(log_mass - logsumexp(log_mass))
        source_probability = float(np.clip(weights[1:].sum(), 0, 1))
        conditional = np.exp(source_log_mass - logsumexp(source_log_mass))
        component_node = base_integration[base_index]
        component_cell = integration_cell[component_node]
        cell_weights = np.bincount(
            component_cell,
            weights=conditional,
            minlength=len(cells),
        )
        # ``integration_cell`` indexes the cells, while the source location
        # is represented by the quadrature nodes.  Recover node mass directly
        # from the source/weather component ordering.
        node_mass = np.bincount(
            component_node,
            weights=conditional,
            minlength=len(integration_xy),
        )
        summary = location_summary(
            integration_xy,
            node_mass,
            cells,
            cell_weights,
            bounds,
            projection,
            edge_fraction=CONFIG["domain_edge_fraction"],
            edge_limit=CONFIG["domain_edge_mass_limit"],
        )
        mean_xy = node_mass @ integration_xy
        mean_shift = float(np.linalg.norm(mean_xy - baseline_mean_xy))
        cell_tv = float(0.5 * np.abs(cell_weights - baseline_cell_weights).sum())
        record = {
            "factor": float(factor),
            "source_probability": source_probability,
            "posterior_mean": summary["posterior_mean"],
            "density_mode": summary["density_mode"],
            "spatial_rms_m": float(summary["spatial_rms_m"]),
            "cell_tv_distance": cell_tv,
            "posterior_mean_shift_m": mean_shift,
        }
        rows.append(record)
        if np.isclose(factor, 1.0, rtol=0, atol=1e-12):
            baseline_factor = float(factor)

    if baseline_factor is None:
        # The declared factors should include the fitted prior.  If a caller
        # supplies a custom list without 1.0, use the closest declared scale
        # as the reference and make that choice explicit in the output.
        index = int(np.argmin(np.abs(np.log(factors))))
        baseline_factor = float(factors[index])
    threshold_mean = float(CONFIG["strength_prior_sensitivity_mean_shift_m"])
    threshold_tv = float(CONFIG["strength_prior_sensitivity_cell_tv"])
    material = [
        row["factor"]
        for row in rows
        if not np.isclose(row["factor"], baseline_factor, rtol=0, atol=1e-12)
        and (
            row["posterior_mean_shift_m"] > threshold_mean
            or row["cell_tv_distance"] > threshold_tv
        )
    ]
    return {
        "factors": [float(factor) for factor in factors],
        "baseline_factor": baseline_factor,
        "alternatives": rows,
        "thresholds": {
            "posterior_mean_shift_m": threshold_mean,
            "cell_tv_distance": threshold_tv,
        },
        "material_factors": material,
        "blocking": bool(material),
        "meaning": "Sensitivity of the conditional source posterior to the declared HalfNormal release-scale prior. Material shifts with fixed observations indicate that location is prior-dependent and source support is withheld; this is not a calibrated uncertainty interval.",
    }


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
    humidity=None,
    other_humidity=None,
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
    covariance = (
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
    # Humidity response is treated as an uncalibrated, sensor-persistent
    # nuisance coefficient.  We only give high humidity a nonzero design
    # value; missing humidity therefore cannot be mistaken for a measurement.
    if (humidity is None) != (other_humidity is None):
        raise ValueError("Both covariance humidity vectors are required together")
    if humidity is not None:
        h = _humidity_design(humidity, len(x))
        oh = _humidity_design(other_humidity, len(other_x))
        covariance = covariance + (
            CONFIG["humidity_response_sd_ug_m3"] ** 2
            * np.outer(h, oh)
            * (ids[:, None] == other_ids[None, :])
        )
    return covariance


def _fit_once(
    inv,
    diagnostics=True,
    *,
    background_only=False,
    wind_uncertainty=True,
    spatial_order=None,
    weather_bias_sd=None,
    weather_step_deg=None,
    _adaptive=False,
    _cells=None,
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
    root_cells = cells.copy()
    original_area = float(np.prod(cells[:, 2:] - cells[:, :2], axis=1).sum())
    if _cells is not None:
        cells = _cells
        source_xy = (cells[:, :2] + cells[:, 2:]) / 2
        area = np.prod(cells[:, 2:] - cells[:, :2], axis=1)
        cell_prior = area / area.sum()
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
    centers = (cells[:, :2] + cells[:, 2:]) / 2
    if continuous:
        root_nx = len(np.unique(root_cells[:, 0]))
        root_ny = len(np.unique(root_cells[:, 1]))
        root_xs = np.unique(root_cells[:, 0])
        root_ys = np.unique(root_cells[:, 1])
        parent_x = np.clip(np.searchsorted(root_xs, centers[:, 0], side="right") - 1, 0, root_nx - 1)
        parent_y = np.clip(np.searchsorted(root_ys, centers[:, 1], side="right") - 1, 0, root_ny - 1)
        root_cell_indices = parent_x * root_ny + parent_y
    else:
        root_centers = (root_cells[:, :2] + root_cells[:, 2:]) / 2
        root_cell_indices = np.argmin(
            np.linalg.norm(centers[:, None, :] - root_centers[None, :, :], axis=-1),
            axis=1,
        )
    source_xy, cells, cell_prior, root_cell_indices = (
        source_xy[supported_cells],
        cells[supported_cells],
        cell_prior[supported_cells],
        root_cell_indices[supported_cells],
    )
    cell_prior /= cell_prior.sum()
    # Midpoint-only integration is inadequate when a narrow plume changes
    # appreciably inside a source cell. Use the same four-node tensor rule for
    # single windows and campaigns; callers may still request order one for a
    # bounded compatibility diagnostic.
    order = 2 if spatial_order is None else spatial_order
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
    humidity = np.array(
        [np.nan if m.humidity_percent is None else m.humidity_percent for m in rows],
        dtype=float,
    )
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
        humidity,
        humidity,
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
        offsets, raw_scales, weather_components, weather_summary = joint_weather_grid(
            inv, tr, all_met, bias_sd=weather_bias_sd, step_deg=weather_step_deg
        )
        joint_prior = weather_components.sum(axis=0)
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
        joint_prior = np.outer(offset_prior, raw_speed_prior)
        weather_components = joint_prior[None]
        weather_summary = {
            "status": "diagnostic_fixed",
            "weather_warning": False,
            "direction_comparison_correction_deg": 0.0,
            "speed_comparison_factor": 1.0,
            "meaning": "Internal mathematical oracle: directional uncertainty disabled, not an operational weather verification.",
        }
    signature_rows, signature_index = np.unique(np.column_stack((x,
        [w.wind_speed_m_s for w in met], [w.wind_from_deg for w in met])), axis=0, return_inverse=True)
    if (
        len(signature_rows) * len(integration_xy) * len(offsets)
        > WEATHER_CONFIG["max_design_entries"]
    ):
        raise ValueError(
            "Weather uncertainty exceeds the supported numerical workload for this study size. Reduce maximum fitted readings or supply appropriate independent wind comparisons; all raw readings are retained."
        )
    nominal = np.array([w.wind_speed_m_s for w in all_met] + [speed])
    retained_speed = np.all((nominal[:, None] * raw_scales >= 0.8) & (nominal[:, None] * raw_scales <= 8), axis=0)
    joint_prior = joint_prior[:, retained_speed]
    weather_components = weather_components[:, :, retained_speed]
    scale_z = joint_prior.sum()
    if not scale_z:
        raise ValueError("No weather speed-bias scenarios remain within supported transport speeds.")
    joint_prior /= scale_z
    weather_components /= scale_z
    scales = raw_scales[retained_speed]
    scale_prior = list(zip(scales, joint_prior.sum(axis=0)))
    offset_prior = joint_prior.sum(axis=1)
    weather_angle, weather_speed = np.nonzero(joint_prior > 0)
    n_weather = len(weather_angle)
    if len(integration_xy) * n_weather > CONFIG["max_components"]:
        raise ValueError("Joint source/weather component count exceeds the supported numerical workload; retain raw data and reduce the study dimensions.")
    configs = np.column_stack((np.repeat(np.arange(len(integration_xy)), n_weather),
                               np.tile(offsets[weather_angle], len(integration_xy)),
                               np.tile(scales[weather_speed], len(integration_xy))))
    integration_index = configs[:, 0].astype(int)
    cell_index = integration_cell[integration_index]
    dw, scale = configs[:, 1], configs[:, 2]
    # C(Q,u*s)=C(Q/s,u). Integrate a HalfNormal(tau/s) effective
    # strength on each unique location/direction column, rather than solving
    # three identical scaled design matrices. The original prior mass remains.
    base_configs = np.array(
        [(i, offset) for i in range(len(integration_xy)) for offset in offsets]
    )
    base_index = (np.arange(len(integration_xy))[:, None] * len(offsets) + weather_angle[None]).ravel()
    base_integration = base_configs[:, 0].astype(int)
    base_direction = base_configs[:, 1]
    weather_prior = joint_prior[weather_angle, weather_speed]
    prior = (integration_prior[:, None] * weather_prior).ravel()
    g = plume_columns(
        signature_rows[:, :2], integration_xy[base_integration],
        signature_rows[:, 2], signature_rows[:, 3], base_direction,
        inv.settings.source_height_m, inv.settings.receptor_height_m,
    )
    norm, dot, inverse_basis = grouped_design(chol, signature_index, residual, g)
    tau = CONFIG["strength_halfnormal_scale_ug_s"] / scale
    precision = 1 / tau**2 + norm[base_index]
    q_sd = 1 / np.sqrt(precision)
    q_mean = dot[base_index] / precision
    log_source = (
        log_bg
        - 0.5 * np.log(precision * tau**2)
        + 0.5 * (q_mean / q_sd) ** 2
        + np.log(2)
        + log_ndtr(q_mean / q_sd)
    )
    qm, qv = positive_normal_moments(q_mean, q_sd)
    log_prior = np.full_like(prior, -np.inf)
    np.log(prior, out=log_prior, where=prior > 0)
    log_mass = np.r_[
        log_bg + np.log1p(-CONFIG["source_prior"]),
        log_source + log_prior + np.log(CONFIG["source_prior"]),
    ]
    if background_only:
        log_mass[1:] = -np.inf
    weights = np.exp(log_mass - logsumexp(log_mass))
    weights /= weights.sum()
    source_probability = float(np.clip(weights[1:].sum(), 0, 1))
    # Conditional source distribution remains defined even if its family mass underflows.
    conditional = np.exp(
        log_source + log_prior - logsumexp(log_source + log_prior)
    )
    cell_weights = np.bincount(
        cell_index, weights=conditional, minlength=len(source_xy)
    )
    quadrature = {"level": None, "limitation": None}
    node_mass = conditional.reshape(len(integration_xy), n_weather).sum(axis=1)
    location = location_summary(integration_xy, node_mass, cells, cell_weights,
                                (anchor_xy.min(axis=0), anchor_xy.max(axis=0)), tr,
                                edge_fraction=CONFIG["domain_edge_fraction"], edge_limit=CONFIG["domain_edge_mass_limit"])
    strength_prior_sensitivity = _strength_prior_sensitivity(
        log_bg=log_bg,
        norm=norm,
        dot=dot,
        tau=tau,
        base_index=base_index,
        base_integration=base_integration,
        log_prior=log_prior,
        integration_xy=integration_xy,
        integration_cell=integration_cell,
        cells=cells,
        baseline_cell_weights=cell_weights,
        baseline_mean_xy=node_mass @ integration_xy,
        bounds=(anchor_xy.min(axis=0), anchor_xy.max(axis=0)),
        projection=tr,
    )
    # Attribute posterior weather mass by the actual joint prior responsibilities,
    # never by selecting only the best source/weather pair.
    posterior_pair_mass = conditional.reshape(len(integration_xy), n_weather).sum(axis=0)
    posterior_weather = np.zeros_like(joint_prior)
    posterior_weather[weather_angle, weather_speed] = posterior_pair_mass
    responsibilities = np.divide(weather_components, joint_prior[None],
        out=np.zeros_like(weather_components), where=joint_prior[None] > 0)
    weather_summary["common_mode_posterior_probability"] = float(np.sum(posterior_weather * responsibilities[1])) if len(responsibilities) > 1 else 0.0
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
    inv_g = inverse_basis
    inv_y = cho_solve((chol, True), residual, check_finite=False)

    first_mass = np.bincount(base_index, weights=weights[1:] * qm, minlength=len(base_configs))
    base_mass = np.bincount(base_index, weights=weights[1:], minlength=len(base_configs))
    base_strength_mean = np.divide(first_mass, base_mass, out=np.zeros_like(first_mass), where=base_mass > 0)
    within_mass = np.bincount(base_index, weights=weights[1:] * (qv + (qm - base_strength_mean[base_index])**2), minlength=len(base_configs))

    def prediction_base(
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
        if count * len(base_configs) > WEATHER_CONFIG["max_design_entries"]:
            raise ValueError("Predictive transport design exceeds numerical workload; request fewer target points at once.")
        if count * count > WEATHER_CONFIG["max_design_entries"]:
            raise ValueError("Predictive target covariance exceeds numerical workload; request fewer target points at once.")
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
            np.zeros(count),
            humidity,
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
                np.zeros(count),
                np.zeros(count),
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
            - ((cross @ inv_g) @ g).T
        )
        return base_mean, base_cov, target_g

    def predictive(
        points, timestamps=None, sensor_ids=None, weather=None, uncertainties=None
    ):
        if len(weights) * len(points)**2 > WEATHER_CONFIG["max_design_entries"]:
            raise ValueError("Component predictive covariance exceeds numerical workload; use exact prediction_moments or predictive_draws instead.")
        base_mean, base_cov, target_base = prediction_base(
            points, timestamps, sensor_ids, weather, uncertainties
        )
        target_g = target_base[base_index]
        means = np.vstack((base_mean, base_mean + qm[:, None] * target_g))
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
        base_mean, base_cov, target_g = prediction_base(
            points, timestamps, sensor_ids, weather, uncertainties
        )
        increment = first_mass @ target_g
        average = base_mean + increment
        dev = base_strength_mean[:, None] * target_g - increment
        total = (base_cov + (dev.T * base_mass) @ dev
                 + (target_g.T * within_mass) @ target_g
                 + weights[0] * np.outer(increment, increment))
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
        base_mean, base, target_g = prediction_base(
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
        draw = np.broadcast_to(base_mean, (samples, d)).copy()
        from scipy.special import ndtri

        draw += ndtri(u[:, 1 : d + 1]) @ np.linalg.cholesky(base).T
        source = component > 0
        k = component[source] - 1
        qdraw = truncnorm.ppf(
            u[source, -1], -q_mean[k] / q_sd[k], np.inf, loc=q_mean[k], scale=q_sd[k]
        )
        draw[source] += qdraw[:, None] * target_g[base_index[k]]
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
        base_mean, base, h = prediction_base(
            points, timestamps, sensor_ids, weather, uncertainties
        )
        values = np.asarray(observed, float)
        v = np.diag(base)[None]
        bg_log = -0.5 * (
            np.log(2 * np.pi * np.diag(base)) + (values - base_mean) ** 2 / np.diag(base)
        )
        result = np.log(max(weights[0], np.finfo(float).tiny)) + bg_log
        for begin in range(0, len(q_mean), 8192):
            s = slice(begin, begin + 8192)
            hs = h[base_index[s]]
            qm0 = q_mean[s, None]
            qs = q_sd[s, None]
            variance = v + qs**2 * hs**2
            residual_future = values[None] - base_mean - qm0 * hs
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
        + (g @ effective_mean_mass)[signature_index]
        - latent_cov @ (inv_g @ (g @ effective_mean_mass))
    )
    # Retain the posterior source contribution separately for adequacy checks.
    # The residual screen must distinguish a changing release from a broad
    # background shift without treating the decomposition as an observation.
    source_prediction = (
        (g @ effective_mean_mass)[signature_index]
        - latent_cov @ (inv_g @ (g @ effective_mean_mass))
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
    node_pair_mass = conditional.reshape(len(integration_xy), n_weather)
    node_direction = np.zeros((len(integration_xy), len(offsets)))
    for j, angle_index in enumerate(weather_angle):
        node_direction[:, angle_index] += node_pair_mass[:, j]
    direction_mass = node_direction.sum(axis=0)
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
        "location_estimate": location,
        "strength_prior_sensitivity": strength_prior_sensitivity,
        "quadrature_diagnostics": quadrature,
        "log_evidence": float(logsumexp(log_mass)),
        "weather_grid": {
            "offsets": offsets,
            "direction_prior": offset_prior,
            "speed_scales": np.array([s for s, _ in scale_prior]),
            "speed_prior": joint_prior.sum(axis=0),
            "joint_prior": joint_prior,
            "posterior_mass": posterior_weather,
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
        "root_cell_indices": root_cell_indices,
        "root_cells_xy": root_cells,
        "location_mean_xy": node_mass @ integration_xy,
        "posterior_region_structure": posterior_region_structure(cells, cell_weights),
        "continuous": continuous,
        "spatial_quadrature_order": order,
        "integration_points": len(integration_xy),
        "transport_signature_groups": len(signature_rows),
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
            "signature_index": signature_index,
            "times": t,
            "coordinates": x,
            "bg_times": bg_t,
            "window_ids": window_ids,
            "sigma": sigma,
            "sensor_ids": ids,
            "configs": base_configs,
            "base_index": base_index,
            "source_cell_indices": integration_cell[base_integration],
            "humidity": humidity,
            "measurement_noise": inv.settings.noise_ug_m3,
        },
        "observed_values": y,
        "fitted_values": average,
        "source_prediction": source_prediction,
        "observation_covariance": covariance,
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


def _mass_by_root_cell(fitted):
    return np.bincount(
        fitted["root_cell_indices"],
        weights=fitted["cell_weights"],
        minlength=len(fitted["root_cells_xy"]),
    )


def _weather_mass_vector(fitted):
    grid = fitted["weather_grid"]
    offsets = np.asarray(grid["offsets"], float)
    speeds = np.asarray(grid["speed_scales"], float)
    mass = np.asarray(grid["posterior_mass"], float)
    out = {}
    for i, offset in enumerate(offsets):
        position = (offset % 360.0) / 5.0
        lower = int(np.floor(position)) % 72
        fraction = position - np.floor(position)
        for j, speed in enumerate(speeds):
            speed_key = round(float(np.log(speed)), 5)
            lower_key = (lower, speed_key)
            upper_key = ((lower + 1) % 72, speed_key)
            out[lower_key] = out.get(lower_key, 0.0) + float(mass[i, j]) * (1 - fraction)
            out[upper_key] = out.get(upper_key, 0.0) + float(mass[i, j]) * fraction
    total = sum(out.values())
    return {key: value / total for key, value in out.items()} if total else out


def _region_integral_metrics(fitted):
    cells = fitted["cells_xy"]
    mass = fitted["cell_weights"]
    area = np.prod(cells[:, 2:] - cells[:, :2], axis=1)
    density = np.divide(mass, area, out=np.zeros_like(mass), where=area > 0)
    order = np.argsort(-density, kind="stable")
    count = min(len(mass), int(np.searchsorted(np.cumsum(mass[order]), 0.9)) + 1)
    selected = order[:count]
    total_area = float(area.sum())
    return {
        "mass": float(mass[selected].sum()),
        "area_fraction": float(area[selected].sum() / total_area) if total_area else 0.0,
    }


def _quadrature_snapshot(fitted):
    return {
        "root_mass": _mass_by_root_cell(fitted),
        "mean": np.asarray(fitted["location_mean_xy"], float).copy(),
        "covariance": np.asarray(fitted["location_estimate"]["covariance_east_north_m2"], float).copy(),
        "weather_mass": _weather_mass_vector(fitted),
        "region": _region_integral_metrics(fitted),
        "log_evidence": float(fitted["log_evidence"]),
        "source_probability": float(fitted["source_probability"]),
    }


def _compare_quadrature_levels(previous, current, tolerances):
    prev_root, curr_root = previous["root_mass"], current["root_mass"]
    if prev_root.shape != curr_root.shape:
        raise ValueError("Nested quadrature levels do not share root source cells")
    prev_mean, curr_mean = previous["mean"], current["mean"]
    prev_cov, curr_cov = previous["covariance"], current["covariance"]
    prev_weather, curr_weather = previous["weather_mass"], current["weather_mass"]
    weather_tv = 0.5 * sum(
        abs(prev_weather.get(key, 0.0) - curr_weather.get(key, 0.0))
        for key in (set(prev_weather) | set(curr_weather))
    )
    prev_region, curr_region = previous["region"], current["region"]
    deltas = {
        "log_evidence": abs(current["log_evidence"] - previous["log_evidence"]),
        "source_probability": abs(current["source_probability"] - previous["source_probability"]),
        "cell_mass_tv": 0.5 * float(np.abs(curr_root - prev_root).sum()),
        "posterior_mean_m": float(np.linalg.norm(curr_mean - prev_mean)),
        "covariance_relative": float(
            np.linalg.norm(curr_cov - prev_cov, ord="fro")
            / max(np.linalg.norm(curr_cov, ord="fro"), np.linalg.norm(prev_cov, ord="fro"), 1.0)
        ),
        "region_mass": abs(curr_region["mass"] - prev_region["mass"]),
        "region_area_fraction": abs(curr_region["area_fraction"] - prev_region["area_fraction"]),
        "weather_mass_tv": float(weather_tv),
    }
    limits = {
        "log_evidence": tolerances["log_evidence_delta"],
        "source_probability": tolerances["source_probability_delta"],
        "cell_mass_tv": tolerances["cell_mass_tv"],
        "posterior_mean_m": tolerances["posterior_mean_delta_m"],
        "covariance_relative": tolerances["covariance_relative_delta"],
        "region_mass": tolerances["region_mass_delta"],
        "region_area_fraction": tolerances["region_area_fraction_delta"],
        "weather_mass_tv": tolerances["weather_mass_tv"],
    }
    passed = {key: bool(deltas[key] <= limits[key]) for key in limits}
    return deltas, passed


def fit(
    inv,
    diagnostics=True,
    *,
    background_only=False,
    wind_uncertainty=True,
    spatial_order=None,
    weather_bias_sd=None,
    weather_step_deg=None,
    quadrature_policy=None,
    _cells=None,
):
    """Fit the conditional model and verify adjacent nested integral levels.

    The finest finite level is always retained. A finite estimate receives no
    source-support status unless evidence, source mass, spatial moments, region
    geometry and the weather marginal all stabilize within the declared policy.
    """
    policy = dict(CONFIG["quadrature_policy"] if quadrature_policy is None else quadrature_policy)
    steps = list(policy["weather_steps_deg"])
    if weather_step_deg is not None:
        steps = [float(weather_step_deg) / (2 ** i) for i in range(len(steps))]
    max_levels = min(int(policy.get("max_levels", len(steps))), len(steps))
    if max_levels < 1:
        raise ValueError("At least one quadrature level is required")
    if _cells is not None:
        # Private compatibility hook for exact local-grid diagnostics.
        max_levels = 1
    tolerance_keys = (
        "log_evidence_delta",
        "source_probability_delta",
        "cell_mass_tv",
        "posterior_mean_delta_m",
        "covariance_relative_delta",
        "region_mass_delta",
        "region_area_fraction_delta",
        "weather_mass_tv",
    )
    tolerances = {key: float(policy[key]) for key in tolerance_keys}
    levels = []
    previous_snapshot = None
    previous_cells = None
    previous_cell_weights = None
    previous_continuous = False
    last_fitted = None
    current_cells = _cells
    converged = False
    limitation = None
    for level in range(max_levels):
        if level > 0 and current_cells is None and previous_continuous:
            cell_width = np.max(previous_cells[:, 2:] - previous_cells[:, :2])
            if cell_width > CONFIG["adaptive_min_width_m"]:
                current_cells, _ = subdivide(
                    previous_cells,
                    previous_cell_weights,
                    target=float(policy["refine_target_mass"]),
                    limit=int(policy["max_refined_parents_per_level"]),
                )
            else:
                current_cells = previous_cells
        if level > 0:
            # The comparison only needs compact mass/moment summaries. Release
            # closures over the previous design before allocating the next.
            del last_fitted
            last_fitted = None
        try:
            fitted = _fit_once(
                inv,
                diagnostics=False,
                background_only=background_only,
                wind_uncertainty=wind_uncertainty,
                spatial_order=spatial_order,
                weather_bias_sd=weather_bias_sd,
                weather_step_deg=steps[level],
                _adaptive=False,
                _cells=current_cells,
            )
        except (ValueError, OverflowError, FloatingPointError, np.linalg.LinAlgError) as exc:
            if previous_snapshot is None:
                raise
            limitation = f"Quadrature level {level} was not completed: {type(exc).__name__}: {exc}"
            # Recompute the last finite level after releasing its large design
            # arrays; this preserves the best available posterior without
            # holding two source/weather matrices concurrently.
            last_fitted = _fit_once(
                inv,
                diagnostics=False,
                background_only=background_only,
                wind_uncertainty=wind_uncertainty,
                spatial_order=spatial_order,
                weather_bias_sd=weather_bias_sd,
                weather_step_deg=steps[level - 1],
                _adaptive=False,
                _cells=previous_cells,
            )
            break
        level_row = {
            "level": level,
            "weather_step_deg": float(fitted["meteorology"].get("angular_step_deg", steps[level])),
            "source_cells": int(len(fitted["cells_xy"])),
            "integration_points": int(fitted["integration_points"]),
            "weather_direction_nodes": int(len(fitted["weather_grid"]["offsets"])),
            "weather_speed_nodes": int(len(fitted["weather_grid"]["speed_scales"])),
            "source_weather_components": int(fitted["scenario_count"] - 1),
            "log_evidence": float(fitted["log_evidence"]),
            "source_probability": float(fitted["source_probability"]),
        }
        current_snapshot = _quadrature_snapshot(fitted)
        if previous_snapshot is not None:
            deltas, passed = _compare_quadrature_levels(previous_snapshot, current_snapshot, tolerances)
            level_row["deltas"] = deltas
            level_row["tolerance_pass"] = passed
            converged = all(passed.values())
            if converged:
                levels.append(level_row)
                previous_snapshot = current_snapshot
                last_fitted = fitted
                break
        levels.append(level_row)
        previous_snapshot = current_snapshot
        previous_cells = fitted["cells_xy"].copy()
        previous_cell_weights = fitted["cell_weights"].copy()
        previous_continuous = bool(fitted["continuous"])
        last_fitted = fitted
        current_cells = None
    if last_fitted is None:
        raise ValueError("No finite quadrature level was completed")
    fitted = last_fitted
    if _cells is not None:
        converged = False
        limitation = "A caller-supplied fixed source grid has no nested convergence comparison."
    elif len(levels) == 1:
        converged = False
        limitation = limitation or "At least two nested source/weather levels are required to assess numerical convergence."
    elif not converged:
        limitation = limitation or "Maximum declared quadrature level reached before every numerical tolerance passed."
    fitted["quadrature_diagnostics"] = {
        "policy": policy,
        "levels": levels,
        "level_count": len(levels),
        "converged": bool(converged),
        "limitation": limitation,
        "meaning": "Nested deterministic area-weighted source and coherent-weather integrals. Numerical convergence is separate from physical model adequacy and is not a field-accuracy guarantee.",
    }
    fitted["numerical_converged"] = bool(converged)
    fitted["numerical_refusal_reason"] = limitation
    if diagnostics:
        usable, _ = measurement_quality(inv)
        fitted["diagnostics"] = sensor_diagnostics(inv, fitted, usable)
        fitted["diagnostics"]["weather_warning"] = fitted["meteorology"]["weather_warning"]
    return fitted


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
    areas = np.prod(cells[:, 2:] - cells[:, :2], axis=1)
    density = np.divide(w, areas, out=w.copy(), where=areas > 0)
    order = np.argsort(-density, kind="stable")
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
        "connected_region_structure": fitted.get("posterior_region_structure"),
    }
