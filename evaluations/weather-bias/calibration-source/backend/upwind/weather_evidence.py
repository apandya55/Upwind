"""Persistent weather bias, conditioned only on explicit comparison readings.

Pollution never verifies meteorology. Same-upstream references cannot calibrate
their own primary; repeated systematic reference errors never average away.
"""

import numpy as np
from scipy.linalg import cho_solve
from scipy.stats import chi2
from .weather import micros

WEATHER_CONFIG = {
    "station_direction_bias_sd_deg": 20.0,
    "station_log_speed_sd": 0.2,
    "direction_step_deg": 2.0,
    "normal_extent_sd": 3.0,
    "reference_max_distance_m": 250.0,
    "reference_max_time_s": 120.0,
    "comparison_tail": 0.01,
    "max_design_entries": 28000000,
    "max_comparisons": 128,
    "reference_max_age_s": 14 * 86400,
}


def wrap(degrees):
    return (np.asarray(degrees) + 180) % 360 - 180


def update_normal(values, covariance, prior_sd):
    y = np.asarray(values, float)
    c = np.asarray(covariance, float)
    one = np.ones(len(y))
    L = np.linalg.cholesky(c)
    sol = cho_solve((L, True), one)
    information = float(one @ sol)
    precision = 1 / prior_sd**2 + information
    variance = 1 / precision
    mean = float(variance * (sol @ y))
    gls = float(sol @ y / information)
    residual = y - gls
    stat = float(residual @ cho_solve((L, True), residual))
    return (
        mean,
        float(np.sqrt(variance)),
        stat,
        1.0 if len(y) < 2 else float(chi2.sf(stat, len(y) - 1)),
    )


def station_distribution(inv, projection, matched, *, bias_sd=None):
    cfg = WEATHER_CONFIG
    prior_sd = cfg["station_direction_bias_sd_deg"] if bias_sd is None else bias_sd
    if not np.isfinite(prior_sd) or prior_sd <= 0:
        raise ValueError("Persistent weather-bias SD must be finite and positive")
    ids = {w.source_id for w in matched}
    if len(ids) != 1:
        raise ValueError(
            "Choose one primary weather source per campaign; multiple uncalibrated primary stations cannot share one persistent bias."
        )
    primary_id = next(iter(ids))
    primary = [
        w for w in inv.weather if w.role == "primary" and w.source_id == primary_id
    ]
    primary.sort(key=lambda w: (w.timestamp, w.latitude, w.longitude))
    primary_times = np.array([micros(w.timestamp) for w in primary], dtype=np.int64)
    px, py = projection.transform(
        [w.longitude for w in primary], [w.latitude for w in primary]
    )
    primary_xy = np.column_stack((px, py))
    matched_times = np.array([micros(w.timestamp) for w in matched], dtype=np.int64)
    refs = [w for w in inv.weather if w.role == "reference"]
    used = []
    unusable = []
    seen = {}
    for w in sorted(
        refs, key=lambda x: (x.timestamp, x.source_id, x.latitude, x.longitude)
    ):
        key = (w.source_id, w.timestamp, w.latitude, w.longitude)
        value = (
            w.wind_from_deg,
            w.wind_speed_m_s,
            w.upstream_id,
            w.direction_systematic_sd_deg,
            w.speed_systematic_fraction,
            w.direction_random_sd_deg,
        )
        if key in seen:
            if seen[key] != value:
                raise ValueError("Conflicting duplicate reference-weather records")
            continue
        seen[key] = value
        b = np.array(projection.transform(w.longitude, w.latitude))
        gaps = np.abs(primary_times - micros(w.timestamp))
        nearest = np.flatnonzero(gaps == gaps.min())
        distances = np.linalg.norm(primary_xy[nearest] - b, axis=1)
        chosen = int(nearest[np.argmin(distances)])
        p = primary[chosen]
        lag = float(gaps[chosen] / 1e6)
        distance = float(np.linalg.norm(primary_xy[chosen] - b))
        reason = None
        if (
            float(np.min(np.abs(micros(w.timestamp) - matched_times))) / 1e6
            > cfg["reference_max_age_s"]
        ):
            reason = "Comparison is more than 14 days from the fitted campaign; station stability is not established."
        elif (
            not p.upstream_id
            or not w.upstream_id
            or p.upstream_id == w.upstream_id
            or p.source_id == w.source_id
        ):
            reason = "Missing or shared upstream lineage: cannot establish an independent comparison."
        elif (
            not w.comparison_provenance
            or w.direction_systematic_sd_deg is None
            or w.speed_systematic_fraction is None
        ):
            reason = "Comparison uncertainty/provenance missing; metadata alone does not establish calibration."
        elif (
            lag > cfg["reference_max_time_s"]
            or distance > cfg["reference_max_distance_m"]
        ):
            reason = "Comparison is not sufficiently simultaneous and co-located for station-bias conditioning."
        elif not 0.8 <= p.wind_speed_m_s <= 8 or not 0.8 <= w.wind_speed_m_s <= 8:
            reason = "Reference speed outside supported range."
        if reason:
            unusable.append(
                {"source_id": w.source_id, "timestamp": w.timestamp, "reason": reason}
            )
            continue
        used.append((w, p, lag, distance))
    grouped = {}
    for w, p, lag, distance in used:
        key = (w.upstream_id, w.timestamp)
        if key in grouped:
            other = grouped[key][0]
            if (w.wind_from_deg, w.wind_speed_m_s) != (
                other.wind_from_deg,
                other.wind_speed_m_s,
            ):
                raise ValueError(
                    "Comparison products sharing an upstream timestamp disagree. Select one documented raw reference source; derived products cannot be treated as independent measurements."
                )
            conservative = other.model_copy(
                update={
                    field: max(getattr(other, field), getattr(w, field))
                    for field in (
                        "direction_systematic_sd_deg",
                        "speed_systematic_fraction",
                        "direction_random_sd_deg",
                    )
                }
            )
            grouped[key] = (conservative, *grouped[key][1:])
            unusable.append(
                {
                    "source_id": w.source_id,
                    "timestamp": w.timestamp,
                    "reason": "Same-upstream reading already represented; duplicate products add no independent calibration precision.",
                }
            )
        else:
            grouped[key] = (w, p, lag, distance)
    used = list(grouped.values())
    if len(used) > cfg["max_comparisons"]:
        raise ValueError(
            "At most 128 eligible paired weather comparisons can be conditioned in one analysis; retain raw data and select a documented comparison subset."
        )
    center = 0.0
    sd = prior_sd
    log_center = 0.0
    log_sd = cfg["station_log_speed_sd"]
    warning = False
    tests = {}
    if used:
        times = np.array([micros(w.timestamp) / 1e6 for w, _, _, _ in used])
        groups = np.array([w.upstream_id for w, _, _, _ in used])
        correlated = np.exp(-np.abs(times[:, None] - times[None, :]) / 600)
        angle_cov = inv.settings.met_direction_sd_deg**2 * correlated + np.diag(
            [w.direction_random_sd_deg**2 for w, _, _, _ in used]
        )
        speed_cov = (
            max(inv.settings.met_speed_fraction, 0.01) ** 2 * correlated
            + np.eye(len(used)) * 0.02**2
        )
        for group in sorted(set(groups)):
            mask = (groups == group).astype(float)
            # Shared upstream systematic floor; never divide by number of rows/products.
            angle_cov += max(
                w.direction_systematic_sd_deg
                for w, _, _, _ in used
                if w.upstream_id == group
            ) ** 2 * np.outer(mask, mask)
            speed_cov += max(
                w.speed_systematic_fraction
                for w, _, _, _ in used
                if w.upstream_id == group
            ) ** 2 * np.outer(mask, mask)
        deltas = wrap(
            np.array([w.wind_from_deg - p.wind_from_deg for w, p, _, _ in used])
        )
        anchor = float(np.rad2deg(np.angle(np.mean(np.exp(1j * np.deg2rad(deltas))))))
        angle = anchor + wrap(deltas - anchor)
        center, sd, stat, tail = update_normal(angle, angle_cov, prior_sd)
        ratios = np.log([w.wind_speed_m_s / p.wind_speed_m_s for w, p, _, _ in used])
        log_center, log_sd, sstat, stail = update_normal(ratios, speed_cov, log_sd)
        warning = bool(
            tail < cfg["comparison_tail"] / 2
            or stail < cfg["comparison_tail"] / 2
            or abs(anchor) > 90
        )
        tests = {
            "direction_statistic": stat,
            "direction_tail": tail,
            "speed_statistic": sstat,
            "speed_tail": stail,
            "degrees_of_freedom": max(0, len(used) - 1),
        }
    return (
        center,
        float(np.hypot(sd, inv.settings.met_direction_sd_deg)),
        log_center,
        float(np.hypot(log_sd, inv.settings.met_speed_fraction)),
        {
            "status": "comparison_supplied" if used else "unverified",
            "comparison_count": len(used),
            "unusable_comparisons": unusable,
            "primary_source_id": primary_id,
            "independent_upstream_groups": len({w.upstream_id for w, _, _, _ in used}),
            "direction_comparison_correction_deg": float(wrap(center)),
            "persistent_direction_sd_deg": sd,
            "speed_comparison_factor": float(np.exp(log_center)),
            "persistent_log_speed_sd": log_sd,
            "weather_warning": warning,
            "comparison_checks": tests,
            "maximum_comparison_distance_m": max(
                (d for _, _, _, d in used), default=None
            ),
            "maximum_comparison_lag_s": max(
                (lag for _, _, lag, _ in used), default=None
            ),
            "meaning": "Bias conditioned on user-supplied paired weather measurements only. Independence/calibration claims are not externally verified; shared upstream systematic errors do not average away. No pollution residual certifies weather. A station comparison does not verify spatial representativeness or clock accuracy elsewhere.",
            "additional_evidence": "An independent co-located wind comparison or separating wind regimes may help. Pollution-site plans do not include weather hardware, deployment time or cost; budget any new weather instrument separately.",
        },
    )


def weather_grid(inv, projection, matched, *, bias_sd=None, step_deg=None):
    center, sd, log_mean, log_sd, summary = station_distribution(
        inv, projection, matched, bias_sd=bias_sd
    )
    spacing = min(
        WEATHER_CONFIG["direction_step_deg"] if step_deg is None else step_deg, sd / 2
    )
    if not np.isfinite(spacing) or spacing <= 0:
        raise ValueError("Weather quadrature spacing must be finite and positive")
    steps = max(1, int(np.ceil(WEATHER_CONFIG["normal_extent_sd"] * sd / spacing)))
    delta = np.arange(-steps, steps + 1) * spacing
    prior = np.exp(-0.5 * (delta / sd) ** 2)
    prior /= prior.sum()
    scales = np.exp(log_mean + np.sqrt(3) * np.array([-1.0, 0.0, 1.0]) * log_sd)
    summary.update(
        direction_center_deg=center,
        total_direction_sd_deg=sd,
        angular_step_deg=spacing,
        angular_nodes=len(delta),
        normal_tail_truncation="Finite approximately±3SD quadrature; not a hard bound on real weather errors.",
    )
    return center + delta, prior, scales, np.array([1 / 6, 2 / 3, 1 / 6]), summary
