"""Nuisance-profile diagnostics and geometry-only experimental design.

These are conditional sensitivity calculations, not source probabilities.
They do not use evaluator truth and cannot certify global identifiability.
"""

import numpy as np
from scipy.linalg import solve_triangular


def whiten_profile(observed, signatures, covariance, nuisance):
    """Profile nonnegative release strength and unrestricted linear nuisance.

    Columns of signatures are unit-release observation vectors. Whiten first,
    then remove the nuisance column space using its numerical SVD rank. This
    implements GLS profiling, including rank-deficient/constant-time designs.
    """
    y, g, r, x = map(
        lambda a: np.asarray(a, dtype=float),
        (observed, signatures, covariance, nuisance),
    )
    if (
        y.ndim != 1
        or g.ndim != 2
        or x.ndim != 2
        or g.shape[0] != len(y)
        or x.shape[0] != len(y)
        or r.shape != (len(y), len(y))
        or not all(np.isfinite(a).all() for a in (y, g, r, x))
    ):
        raise ValueError(
            "Finite, compatible observation/design/covariance arrays required"
        )
    if not np.allclose(r, r.T, atol=1e-12, rtol=1e-10):
        raise ValueError("Observation covariance must be symmetric")
    chol = np.linalg.cholesky(r)
    yw = solve_triangular(chol, y, lower=True, check_finite=False)
    gw = solve_triangular(chol, g, lower=True, check_finite=False)
    xw = solve_triangular(chol, x, lower=True, check_finite=False)
    u, singular, _ = np.linalg.svd(xw, full_matrices=False)
    cutoff = (
        np.finfo(float).eps
        * max(xw.shape, default=1)
        * (singular[0] if len(singular) else 0)
    )
    basis = u[:, singular > cutoff]
    yp = yw - basis @ (basis.T @ yw)
    gp = gw - basis @ (basis.T @ gw)
    norm = np.sum(gp**2, axis=0)
    dot = gp.T @ yp
    strength = np.divide(
        np.maximum(dot, 0), norm, out=np.zeros_like(dot), where=norm > 1e-200
    )
    # Direct residual calculation avoids cancellation for exact noiseless fits.
    residual = yp[:, None] - gp * strength
    loss = np.sum(residual**2, axis=0)
    return {
        "strength": strength,
        "loss": loss,
        "background_loss": float(yp @ yp),
        "projected_signatures": gp,
        "projected_observed": yp,
        "nuisance_rank": int(basis.shape[1]),
        "residual_dimensions": len(y) - basis.shape[1],
    }


def pair_separation(signatures, covariance, nuisance, strength):
    """Directed squared Mahalanobis distances after alternative q/background fit.

    Entry[i,j] is separation of strength*g_i from best nonnegative q*g_j plus
    free nuisance. It is directional: weak alternatives can require enormous
    strength. The supplied reference strength is an explicit scenario assumption.
    """
    g = np.asarray(signatures, dtype=float)
    prof = whiten_profile(np.zeros(g.shape[0]), g, covariance, nuisance)
    gp = prof["projected_signatures"]
    gram = gp.T @ gp
    norm = np.maximum(np.diag(gram), 0)
    explained = np.divide(
        np.maximum(gram, 0) ** 2,
        norm[None],
        out=np.zeros_like(gram),
        where=norm[None] > 1e-200,
    )
    return np.maximum(0, strength**2 * (norm[:, None] - explained))


def local_resolution(signature_derivatives, signature, covariance, nuisance, strength):
    """Local Fisher axes after profiling strength/background; not a global bound."""
    derivatives = np.asarray(signature_derivatives, dtype=float)
    x = np.column_stack((nuisance, signature))
    prof = whiten_profile(np.zeros(len(signature)), derivatives, covariance, x)
    j = strength * prof["projected_signatures"]
    eigen = np.linalg.eigvalsh(j.T @ j)
    axes = [None if value <= 1e-12 else float(1 / np.sqrt(value)) for value in eigen]
    return {
        "fisher_eigenvalues_per_m2": eigen.tolist(),
        "local_one_sigma_axes_m": axes,
        "meaning": "Local linear sensitivity only; disconnected/global ambiguities may remain.",
    }


def diagnose_fit(fitted, noise):
    """Global finite-grid profile alongside, rather than replacing, posterior mass."""
    c = fitted["profile_context"]
    xy = fitted["projection"].transform(
        [r.longitude for r in fitted["rows"]], [r.latitude for r in fitted["rows"]]
    )
    xy = np.column_stack(xy)
    d = np.linalg.norm(xy[:, None] - xy[None], axis=-1)
    times = c["times"]
    ids = c["sensor_ids"]
    from .inference import CONFIG

    covariance = (
        np.diag(c["sigma"] ** 2)
        + CONFIG["instrument_bias_sd_ug_m3"] ** 2 * (ids[:, None] == ids[None])
        + noise**2
        * np.exp(
            -d / CONFIG["spatial_scale_m"]
            - abs(times[:, None] - times[None]) / CONFIG["temporal_scale_s"]
        )
    )
    labels = (
        c["window_ids"]
        if c["window_ids"] is not None
        else np.zeros(len(times), dtype=int)
    )
    trend = c["bg_times"] if c["bg_times"] is not None else times
    windows = sorted(set(labels))
    nuisance = np.column_stack(
        [
            column
            for w in windows
            for column in ((labels == w).astype(float), (labels == w) * trend / 3600)
        ]
    )
    signatures = c["signatures"]
    if "signature_index" in c:
        signatures = signatures[c["signature_index"]]
    prof = whiten_profile(c["observed"], signatures, covariance, nuisance)
    cell = c["source_cell_indices"]
    best = np.argmin(prof["loss"])
    minimum = np.full(len(fitted["source_xy"]), np.inf)
    np.minimum.at(minimum, cell, prof["loss"])
    compatible = minimum <= minimum.min() + 4.605170186
    area = np.prod(fitted["cells_xy"][:, 2:] - fitted["cells_xy"][:, :2], axis=1)
    area_fraction = (
        float(area[compatible].sum() / area.sum())
        if area.sum() > 0
        else float(compatible.mean())
    )
    distances = np.linalg.norm(
        fitted["source_xy"] - fitted["source_xy"][cell[best]], axis=1
    )
    prior = area / area.sum() if area.sum() > 0 else np.full(len(area), 1 / len(area))
    weights = fitted["cell_weights"]
    positive = weights > 0
    return {
        "method": "GLS profile over all source/weather configurations, fitting nonnegative strength and independent per-window background/trend.",
        "profile_background_improvement": float(
            prof["background_loss"] - minimum.min()
        ),
        "profile_compatible_domain_fraction": area_fraction,
        "far_compatible_cells": int(np.sum(compatible & (distances >= 100))),
        "profile_best_strength_ug_s": float(prof["strength"][best]),
        "conditional_location_information_nats": float(
            np.sum(weights[positive] * np.log(weights[positive] / prior[positive]))
        ),
        "windows_observed": len(windows),
        "nuisance_rank": prof["nuisance_rank"],
        "meaning": "Compatibility uses delta chi-square4.605 as an uncalibrated diagnostic, not a geographic confidence region. Strength is effective Q/speed-scale at nominal wind speed and is unbounded; huge fitted values expose prior/identifiability sensitivity. Distant compatible cells can indicate global ambiguity. No source count or responsibility is established.",
    }
