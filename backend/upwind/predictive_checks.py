"""Predictive model checking and residual diagnostics."""

import hashlib
import numpy as np
from scipy.linalg import solve_triangular


def joint_tail(mean, covariance, observed, draws, nuisance=None):
    """QMC tail area for a joint Mahalanobis discrepancy, optionally contrasted.

    The null distribution comes from the predictive draws, not a chi-square
    approximation to a non-Gaussian mixture. Project unknown regional background
    and trend out of a held-out window before measuring spatial disagreement.
    """
    mean, cov, values, samples = map(
        lambda x: np.asarray(x, float), (mean, covariance, observed, draws)
    )
    if (
        mean.shape != values.shape
        or cov.shape != (len(mean), len(mean))
        or samples.ndim != 2
        or samples.shape[1] != len(mean)
        or not all(np.isfinite(x).all() for x in (mean, cov, values, samples))
    ):
        raise ValueError(
            "Compatible finite predictive means/covariance/samples required"
        )
    basis = np.eye(len(mean))
    if nuisance is not None:
        x = np.asarray(nuisance, float)
        u, s, _ = np.linalg.svd(x, full_matrices=True)
        rank = (
            int(np.sum(s > np.finfo(float).eps * max(x.shape) * s.max()))
            if len(s)
            else 0
        )
        basis = u[:, rank:].T
    if not len(basis):
        raise ValueError("No residual predictive contrast dimensions")
    chol = np.linalg.cholesky(basis @ cov @ basis.T)
    white = solve_triangular(chol, basis @ (values - mean), lower=True)
    statistic = float(white @ white)
    simulated = solve_triangular(chol, basis @ (samples - mean).T, lower=True)
    tail = float(
        (1 + np.sum(np.sum(simulated**2, axis=0) >= statistic)) / (len(samples) + 1)
    )
    return {
        "tail_probability": tail,
        "joint_statistic": statistic,
        "contrast_dimensions": len(basis),
        "samples": len(samples),
        "integration_resolution": 1 / (len(samples) + 1),
    }


def stream_seed(seed, label):
    words = np.frombuffer(hashlib.sha256(label.encode()).digest()[:16], dtype="<u4")
    return int(np.random.SeedSequence([seed, *map(int, words)]).generate_state(1)[0])


def screen(inv, usable, fit_function):
    from .quality import select_rows
    from .campaign import observed_weather, assignment

    sensors = sorted({m.sensor_id for m in usable})
    if len(sensors) < 3:
        return {
            "held_out_sensor": [],
            "held_out_window": [],
            "predictive_warning": False,
            "method": "Unavailable: at least three usable sensors required. No adequacy certificate.",
        }
    # Budgeted blocks selected deterministically. For campaigns, period contrasts
    # add a different test of the shared-release assumption, not extra fits to it.
    sensor_ids = [
        sensors[i]
        for i in np.linspace(
            0,
            len(sensors) - 1,
            min(3 if inv.study_windows else 6, len(sensors)),
            dtype=int,
        )
    ]
    labels, _ = assignment(inv, [r.timestamp for r in usable])
    periods = sorted(set(labels)) if inv.study_windows else []
    period_ids = (
        [
            periods[i]
            for i in np.linspace(0, len(periods) - 1, min(3, len(periods)), dtype=int)
        ]
        if len(periods) >= 3
        else []
    )
    alpha = 0.01 / (len(sensor_ids) + len(period_ids))
    checks = []
    window_checks = []
    for kind, blocks in (("sensor", sensor_ids), ("window", period_ids)):
        for block in blocks:
            selected = [
                m
                for m, w in zip(usable, labels)
                if (m.sensor_id == block if kind == "sensor" else w == block)
            ]
            keys = {(m.sensor_id, m.timestamp) for m in selected}
            train = inv.model_copy(deep=True)
            train.measurements = [
                m for m in inv.measurements if (m.sensor_id, m.timestamp) not in keys
            ]
            row = (
                {"sensor_id": str(block), "rows": 0, "flagged": False}
                if kind == "sensor"
                else {
                    "window_id": sorted(inv.study_windows, key=lambda w: w.start)[
                        block
                    ].id,
                    "rows": 0,
                    "flagged": False,
                }
            )
            try:
                all_ids = sorted({m.sensor_id for m in selected})
                checked_ids = {
                    all_ids[i]
                    for i in np.linspace(
                        0, len(all_ids) - 1, min(24, len(all_ids)), dtype=int
                    )
                }
                held = select_rows(
                    [m for m in selected if m.sensor_id in checked_ids],
                    24,
                    inv.settings.selection_seed,
                )
                row.update(
                    rows=len(held),
                    rows_total=len(selected),
                    sensors_total=len(all_ids),
                    sensors_checked=len(checked_ids),
                )
                trained = fit_function(train, diagnostics=False)
                met, _, _ = observed_weather(
                    inv, held, trained["projection"], require_sensors=False
                )
                timestamps = [r.timestamp for r in held]
                ids = [r.sensor_id for r in held]
                sigma = [
                    r.uncertainty_ug_m3
                    if r.uncertainty_ug_m3 is not None
                    else inv.settings.noise_ug_m3
                    for r in held
                ]
                args = (held, timestamps, ids, met, sigma)
                mean, cov = trained["prediction_moments"](*args)
                samples = trained["predictive_draws"](
                    *args,
                    samples=2048,
                    seed=stream_seed(inv.settings.seed, f"{kind}:{block}"),
                )
                values = np.array([r.pm25_ug_m3 for r in held])
                nuisance = None
                if kind == "window":
                    from datetime import datetime

                    times = np.array(
                        [datetime.fromisoformat(t).timestamp() for t in timestamps]
                    )
                    times = (times - times.mean()) / 3600
                    nuisance = np.column_stack((np.ones(len(held)), times))
                outcome = joint_tail(mean, cov, values, samples, nuisance)
                row.update(
                    outcome,
                    flagged=outcome["tail_probability"] < alpha,
                    screen_alpha=alpha,
                )
                if kind == "sensor":
                    lo, hi = np.quantile(samples, [0.05, 0.95], axis=0)
                    row.update(
                        rmse_ug_m3=float(np.sqrt(np.mean((mean - values) ** 2))),
                        coverage90=float(np.mean((values >= lo) & (values <= hi))),
                        mean_nlpd=float(
                            -trained["predictive_log_density"](values, *args).mean()
                        ),
                    )
            except (ValueError, np.linalg.LinAlgError) as exc:
                row["unavailable"] = str(exc)
            (checks if kind == "sensor" else window_checks).append(row)
    return {
        "held_out_sensor": checks,
        "held_out_window": window_checks,
        "predictive_warning": any(r["flagged"] for r in checks + window_checks),
        "sensors_total": len(sensors),
        "sensors_checked": len(checks),
        "windows_checked": len(window_checks),
        "method": "Joint withheld-sensor and withheld-period contrast checks. Exact truncated-strength predictive sampling,2048 scrambled Sobol draws/block; 1% familywise Bonferroni screen over checked blocks. QMC tail resolution and unchecked blocks are explicit; not field calibrated or an adequacy certificate.",
    }
