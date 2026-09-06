"""Sensitivity diagnostics and geometric experimental design."""

import numpy as np
from scipy.linalg import solve_triangular
from scipy.optimize import nnls
from .inference import CONFIG


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


def whiten_grouped_profile(observed, signatures, covariance, nuisance, signature_index, *, block_columns=2048):
    """GLS profile with repeated signatures, bounded column workspaces.

    L^-1 (B G) = (L^-1 B) G. Preserve the full observation covariance;
    never materialize all expanded/whitened source columns simultaneously.
    """
    y,g,r,x=map(lambda a:np.asarray(a,dtype=float),(observed,signatures,covariance,nuisance))
    index=np.asarray(signature_index)
    if (y.ndim!=1 or g.ndim!=2 or x.ndim!=2 or x.shape[0]!=len(y)
        or r.shape!=(len(y),len(y)) or index.shape!=(len(y),)
        or not np.issubdtype(index.dtype,np.integer) or np.any(index<0) or np.any(index>=len(g))
        or not isinstance(block_columns,int) or not 1<=block_columns<=2048 or not all(np.isfinite(a).all() for a in (y,g,r,x))):
        raise ValueError('Finite compatible grouped profile inputs required')
    if not np.allclose(r,r.T,atol=1e-12,rtol=1e-10):raise ValueError('Observation covariance must be symmetric')
    chol=np.linalg.cholesky(r)
    yw=solve_triangular(chol,y,lower=True,check_finite=False)
    xw=solve_triangular(chol,x,lower=True,check_finite=False)
    u,singular,_=np.linalg.svd(xw,full_matrices=False)
    cutoff=np.finfo(float).eps*max(xw.shape,default=1)*(singular[0] if len(singular) else 0.)
    basis=u[:,singular>cutoff]
    yp=yw-basis@(basis.T@yw)
    white_basis=solve_triangular(chol,np.eye(len(g))[index],lower=True,check_finite=False)
    strength=np.empty(g.shape[1]);loss=np.empty(g.shape[1])
    for begin in range(0,g.shape[1],block_columns):
        sl=slice(begin,begin+block_columns)
        white=white_basis@g[:,sl]
        projected=white-basis@(basis.T@white)
        norm=np.sum(projected**2,axis=0)
        # A signature in the nuisance space carries no resolvable source signal.
        # Do not fit unbounded Q to projection roundoff in that null direction.
        resolution=np.finfo(float).eps*max(xw.shape)*np.linalg.norm(white,axis=0)
        null=norm<=resolution**2
        projected[:,null]=0.;norm[null]=0.
        dot=projected.T@yp
        q=np.divide(np.maximum(dot,0),norm,out=np.zeros_like(dot),where=norm>1e-200)
        residual=yp[:,None]-projected*q
        strength[sl]=q;loss[sl]=np.sum(residual**2,axis=0)
    return dict(
        strength=strength,
        loss=loss,
        background_loss=float(yp@yp),
        nuisance_rank=int(basis.shape[1]),
        residual_dimensions=len(y)-basis.shape[1],
        projected_observed=yp,
        nuisance_basis=basis,
        whitened_group_basis=white_basis,
    )


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
    covariance = (
        np.diag(c["sigma"] ** 2)
        + CONFIG["instrument_bias_sd_ug_m3"] ** 2 * (ids[:, None] == ids[None])
        + noise**2
        * np.exp(
            -d / CONFIG["spatial_scale_m"]
            - abs(times[:, None] - times[None]) / CONFIG["temporal_scale_s"]
        )
    )
    humidity = np.asarray(c.get("humidity", np.zeros(len(times))), float)
    humidity_design = np.maximum(
        (np.nan_to_num(humidity, nan=0.0) - CONFIG["humidity_threshold_percent"])
        / CONFIG["humidity_scale_percent"],
        0.0,
    )
    covariance += (
        CONFIG["humidity_response_sd_ug_m3"] ** 2
        * np.outer(humidity_design, humidity_design)
        * (ids[:, None] == ids[None, :])
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
    cell = c["source_cell_indices"]
    if "signature_index" in c:
        prof = whiten_grouped_profile(c["observed"], signatures, covariance, nuisance, c["signature_index"])
        # Profile pairs only under a shared persistent weather-offset
        # configuration. Keep the best 24 cells overall and, for those cells,
        # the best columns at a bounded set of eight offsets. Selecting the
        # pair across all offsets would both violate the shared-bias assumption
        # and create an unbounded diagnostic workspace.
        configs = np.asarray(c["configs"], float)
        if configs.shape != (len(cell), 2):
            raise ValueError("Profile weather configurations do not match source columns")
        offsets = configs[:, 1]
        best_by_cell = {}
        for i, source_cell in enumerate(cell):
            source_cell = int(source_cell)
            if source_cell not in best_by_cell or prof["loss"][i] < prof["loss"][best_by_cell[source_cell]]:
                best_by_cell[source_cell] = i
        selected_cells = [
            int(cell[i])
            for i in sorted(
                best_by_cell.values(),
                key=lambda i: (prof["loss"][i], int(cell[i])),
            )[:24]
        ]
        offset_scores = []
        for offset in np.unique(offsets):
            group = np.flatnonzero(np.isclose(offsets, offset, atol=1e-10, rtol=0))
            group = [i for i in group if int(cell[i]) in selected_cells]
            if group:
                offset_scores.append((float(np.min(prof["loss"][group])), float(offset)))
        selected_offsets = [offset for _, offset in sorted(offset_scores)[:8]]
        retained = []
        for offset in selected_offsets:
            group = np.flatnonzero(np.isclose(offsets, offset, atol=1e-10, rtol=0))
            for source_cell in selected_cells:
                candidates = [i for i in group if int(cell[i]) == source_cell]
                if candidates:
                    retained.append(min(candidates, key=lambda i: prof["loss"][i]))
        candidate_indices = np.asarray(retained, dtype=int)
        white = prof["whitened_group_basis"] @ signatures[:, candidate_indices]
        projected = white - prof["nuisance_basis"] @ (
            prof["nuisance_basis"].T @ white
        )
        pair_profile = {
            "loss": prof["loss"][candidate_indices],
            "projected_signatures": projected,
            "projected_observed": prof["projected_observed"],
            "weather_offsets": offsets[candidate_indices],
        }
    else:
        prof = whiten_profile(c["observed"], signatures, covariance, nuisance)
        candidate_indices = np.arange(len(cell), dtype=int)
        pair_profile = prof
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
    # A bounded two-source profile is deliberately a diagnostic, not a second
    # posterior.  It tests whether a sparse competing explanation materially
    # improves the same nuisance-profile loss before the UI presents a single
    # source as resolved.
    source_count = _two_source_profile(
        pair_profile,
        cell[candidate_indices],
        fitted,
    )
    externalities = _externality_checks(fitted)
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
        "source_count": source_count,
        "externalities": externalities,
        "meaning": "Compatibility uses delta chi-square4.605 as an uncalibrated diagnostic, not a geographic confidence region. Strength is effective Q/speed-scale at nominal wind speed and is unbounded; huge fitted values expose prior/identifiability sensitivity. Distant compatible cells can indicate global ambiguity. No source count or responsibility is established.",
    }


def _two_source_profile(profile, cell, fitted):
    """Compare a small, deterministic pair profile to the best one-source fit.

    The candidate set is the best column per source cell, then at most 24 cells
    by profile loss.  Nonnegative least squares is used after the same nuisance
    projection as the one-source profile.  This is an adequacy flag only: it
    does not assign responsibility or replace the one-source posterior.
    """
    loss = np.asarray(profile["loss"], float)
    gp = np.asarray(profile["projected_signatures"], float)
    cell = np.asarray(cell, int)
    if gp.ndim != 2 or len(loss) != gp.shape[1] or len(cell) != len(loss):
        raise ValueError("Incompatible source profile arrays")
    global_single = float(np.min(loss)) if len(loss) else float("inf")
    best = {
        "loss": global_single,
        "single_loss": global_single,
        "source_cells": [],
        "strengths": [],
        "offset": None,
        "improvement": 0.0,
    }
    offsets = profile.get("weather_offsets")
    if offsets is None:
        groups = [np.arange(len(loss), dtype=int)]
    else:
        offsets = np.asarray(offsets, float)
        if offsets.shape != (len(loss),) or not np.isfinite(offsets).all():
            raise ValueError("Weather-offset profile must match source columns")
        groups = [
            np.flatnonzero(np.isclose(offsets, offset, atol=1e-10, rtol=0))
            for offset in np.unique(offsets)
        ]
    candidate_count = 0
    invalid_fit_count = 0
    for group in groups:
        group_single = float(np.min(loss[group])) if len(group) else float("inf")
        best_by_cell = {}
        for i in group:
            c = int(cell[i])
            if c not in best_by_cell or loss[i] < loss[best_by_cell[c]]:
                best_by_cell[c] = int(i)
        indices = np.array(
            sorted(best_by_cell.values(), key=lambda i: (loss[i], int(cell[i])))[:24],
            dtype=int,
        )
        candidate_count = max(candidate_count, len(indices))
        if len(indices) < 2 or not np.isfinite(group_single):
            continue
        for a in range(len(indices)):
            for b in range(a + 1, len(indices)):
                ia, ib = int(indices[a]), int(indices[b])
                if cell[ia] == cell[ib]:
                    continue
                strength, pair_loss = nnls(
                    gp[:, [ia, ib]], profile["projected_observed"]
                )
                # Ill-conditioned projected columns can make scipy's NNLS
                # return non-finite coefficients even when the residual loss
                # is finite. Never let those values reach the public result
                # or turn a failed adequacy check into source support.
                if not np.isfinite(strength).all() or not np.isfinite(pair_loss):
                    invalid_fit_count += 1
                    continue
                pair_loss = float(pair_loss**2)
                improvement = max(0.0, group_single - pair_loss)
                if improvement > best["improvement"]:
                    best = {
                        "loss": pair_loss,
                        "single_loss": group_single,
                        "source_cells": [int(cell[ia]), int(cell[ib])],
                        "strengths": [float(x) for x in strength],
                        "offset": (
                            None if offsets is None else float(offsets[ia])
                        ),
                        "improvement": improvement,
                    }
    improvement = float(best["improvement"])
    if best["source_cells"]:
        centers = np.asarray(fitted["source_xy"])[best["source_cells"]]
        separation = float(np.linalg.norm(centers[0] - centers[1]))
        source_coordinates = []
        if "projection" in fitted:
            for east, north in centers:
                lon, lat = fitted["projection"].transform(
                    float(east), float(north), direction="INVERSE"
                )
                source_coordinates.append(
                    {"latitude": float(lat), "longitude": float(lon)}
                )
    else:
        separation = 0.0
        source_coordinates = []
    # Require both releases to carry a real amount of signal.  A pair with a
    # zero coefficient is only the one-source fit written twice.
    active = bool(
        best["source_cells"]
        and min(best["strengths"]) > 0
        and separation >= 50.0
        and improvement >= CONFIG["externality_pair_delta_chi2"]
    )
    return {
        "method": "Bounded nonnegative two-source GLS profile over the best 24 source cells; diagnostic only",
        "single_source_loss": float(best["single_loss"]),
        "global_single_source_loss": global_single,
        "best_pair_loss": float(best["loss"]),
        "improvement_delta_chi2": float(improvement),
        "shared_weather_offset_deg": best["offset"],
        "source_cells": best["source_cells"],
        "strengths_ug_s": best["strengths"],
        "source_coordinates": source_coordinates,
        "separation_m": separation,
        "candidate_cells": int(candidate_count),
        "invalid_pair_fits": int(invalid_fit_count),
        "diagnostic_unavailable": bool(invalid_fit_count),
        "material_competing_pair": active,
        "meaning": "A material pair improvement means the one-source posterior is not an adequate explanation under this finite profile. Non-finite candidate fits make the adequacy check unavailable and block source support. This diagnostic does not identify two real emitters or their responsibility.",
    }


def _externality_checks(fitted):
    """Detect structured residuals that the steady Gaussian model omits."""
    residual = np.asarray(fitted.get("observed_values"), float) - np.asarray(
        fitted.get("fitted_values"), float
    )
    covariance = np.asarray(fitted.get("observation_covariance"), float)
    c = fitted["profile_context"]
    n = len(residual)
    if n == 0 or covariance.shape != (n, n):
        return {"flags": ["missing_residual_context"], "blocking": True}
    # Standardize against residual-scale terms only. The broad background and
    # trend priors have already been estimated from these rows; retaining their
    # prior variance here would make a large observation look artificially
    # ordinary and hide structured failures.
    noise = float(c.get("measurement_noise", 1.0))
    sigma = np.asarray(c.get("sigma", np.zeros(n)), float)
    humidity = np.asarray(c.get("humidity", np.full(n, np.nan)), float)
    humidity_design = np.maximum(
        (np.nan_to_num(humidity, nan=0.0) - CONFIG["humidity_threshold_percent"])
        / CONFIG["humidity_scale_percent"],
        0.0,
    )
    residual_variance = (
        sigma**2
        + noise**2
        + CONFIG["instrument_bias_sd_ug_m3"] ** 2
        + CONFIG["humidity_response_sd_ug_m3"] ** 2 * humidity_design**2
    )
    scale = np.sqrt(np.maximum(residual_variance, 1e-12))
    z = residual / scale
    flags = []
    evidence = {}

    humidity = np.asarray(c.get("humidity", np.full(n, np.nan)), float)
    high = np.isfinite(humidity) & (humidity >= 80.0)
    low = np.isfinite(humidity) & (humidity < 70.0)
    if high.sum() >= 2 and low.sum() >= 2:
        contrast = float(np.mean(z[high]) - np.mean(z[low]))
        evidence["high_humidity_standardized_contrast"] = contrast
        if abs(contrast) >= 2.5:
            flags.append("humidity_response_or_water_artifact")

    times = np.asarray(c.get("times", np.zeros(n)), float)
    ids = np.asarray(c.get("sensor_ids", ["" for _ in range(n)]))
    sensor_correlations = []
    for sensor in sorted(set(ids.tolist())):
        mask = ids == sensor
        if mask.sum() >= 4 and np.ptp(times[mask]) > 0:
            correlation = float(np.corrcoef(times[mask], z[mask])[0, 1])
            if np.isfinite(correlation):
                sensor_correlations.append(correlation)
    evidence["max_sensor_time_correlation"] = (
        max((abs(x) for x in sensor_correlations), default=0.0)
    )
    if evidence["max_sensor_time_correlation"] >= 0.8:
        flags.append("sensor_drift_or_time_varying_release")

    # A release step can affect every sensor together and therefore evade the
    # per-sensor correlation check. Keep this as an externality signal rather
    # than fitting a time-varying source, because a broad background change,
    # weather transition or synchronized instrument event has the same pattern.
    global_time_correlation = 0.0
    if n >= 6 and np.ptp(times) > 0 and np.std(z) > 0:
        correlation = float(np.corrcoef(times, z)[0, 1])
        if np.isfinite(correlation):
            global_time_correlation = abs(correlation)
    evidence["global_time_correlation"] = global_time_correlation
    if global_time_correlation >= 0.8:
        flags.append("sensor_drift_or_time_varying_release")

    if n >= 6:
        midpoint = float(np.median(times))
        early = times <= midpoint
        late = times > midpoint
        if early.sum() >= 2 and late.sum() >= 2:
            step_contrast = float(np.mean(z[late]) - np.mean(z[early]))
            evidence["late_early_standardized_contrast"] = step_contrast
            if abs(step_contrast) >= 2.5:
                flags.append("sensor_drift_or_time_varying_release")

        source_prediction = np.asarray(
            fitted.get("source_prediction", np.zeros(n)), float
        )
        if source_prediction.shape == (n,) and np.isfinite(source_prediction).all():
            # Project each half's standardized residual onto the fitted plume
            # shape. A release step has a spatial pattern; a uniform background
            # jump should not be treated as source evidence. This remains a
            # discrepancy signal, not a time-varying-source fit.
            def source_projection(mask):
                design = source_prediction[mask] / scale[mask]
                response = z[mask]
                norm = float(np.linalg.norm(design))
                return (
                    float(design @ response / norm) if norm > 1e-12 else 0.0
                )

            early_projection = source_projection(early)
            late_projection = source_projection(late)
            evidence["late_early_source_projection_delta"] = (
                late_projection - early_projection
            )
            if abs(late_projection - early_projection) >= 2.5:
                flags.append("sensor_drift_or_time_varying_release")

    distance = None
    if "coordinates" in c:
        coordinates = np.asarray(c["coordinates"], float)
        if coordinates.shape != (n, 2) or not np.isfinite(coordinates).all():
            raise ValueError("Residual coordinates must be finite n×2 values")
        distance = np.linalg.norm(
            coordinates[:, None] - coordinates[None], axis=-1
        )
    if distance is not None and n >= 4:
        tri = np.triu_indices(n, 1)
        dt = np.abs(times[:, None] - times[None])
        near = (distance[tri] <= 200.0) & (ids[tri[0]] != ids[tri[1]]) & (dt[tri] <= 600.0)
        # Use the full model-implied off-diagonal covariance, including
        # persistent instrument/humidity/background terms. Comparing against
        # only the short-range noise term falsely labels a valid persistent
        # sensor effect as unexplained spatial background.
        expected = covariance[tri] / (scale[tri[0]] * scale[tri[1]])
        pair_products = z[tri[0]] * z[tri[1]] - expected
        if near.any():
            evidence["nearby_residual_product"] = float(np.mean(pair_products[near]))
            if evidence["nearby_residual_product"] >= 0.75:
                flags.append("unresolved_spatial_background")

    evidence["outlier_count_abs_z_ge_4"] = int(np.sum(np.abs(z) >= 4.0))
    if evidence["outlier_count_abs_z_ge_4"] >= max(2, int(np.ceil(0.1 * n))):
        flags.append("heavy_tails_or_unflagged_event")
    release_profile = _release_variation_profile(fitted)
    evidence.update(release_profile["evidence"])
    if release_profile["flag"]:
        flags.append("sensor_drift_or_time_varying_release")
    return {
        "flags": sorted(set(flags)),
        "blocking": bool(flags),
        "standardized_residual_rms": float(np.sqrt(np.mean(z**2))),
        "evidence": evidence,
        "meaning": "Structured residuals are externality indicators, not diagnoses. A flagged result requires independent weather, instrument, chemistry or source-count evidence before attribution.",
    }


def _release_variation_profile(fitted):
    """Compare constant and two-half source amplitudes for one plume shape.

    This is an adequacy check only. It uses the highest-posterior source/weather
    signature as a fixed shape and allows separate nonnegative amplitudes before
    and after the median observation time. A large improvement can also be a
    weather transition or instrument event, so it blocks support rather than
    asserting a changing emission rate.
    """
    c = fitted.get("profile_context", {})
    y = np.asarray(fitted.get("observed_values", []), float)
    covariance = np.asarray(fitted.get("observation_covariance", []), float)
    times = np.asarray(c.get("times", []), float)
    signatures = np.asarray(c.get("signatures", []), float)
    signature_index = np.asarray(c.get("signature_index", []), int)
    base_index = np.asarray(c.get("base_index", []), int)
    weights = np.asarray(fitted.get("weights", []), float)
    if (
        len(y) < 6
        or covariance.shape != (len(y), len(y))
        or times.shape != (len(y),)
        or not np.isfinite(times).all()
        or np.ptp(times) <= 0
        or signatures.ndim != 2
        or signature_index.shape != (len(y),)
        or base_index.ndim != 1
        or len(weights) != len(base_index) + 1
    ):
        return {"flag": False, "evidence": {"release_profile": "unavailable"}}
    posterior_base = np.bincount(
        base_index,
        weights=np.maximum(weights[1:], 0.0),
        minlength=signatures.shape[1],
    )
    if not np.any(posterior_base > 0):
        return {"flag": False, "evidence": {"release_profile": "unavailable"}}
    best_base = int(np.argmax(posterior_base))
    if best_base >= signatures.shape[1]:
        return {"flag": False, "evidence": {"release_profile": "unavailable"}}
    source = signatures[signature_index, best_base]
    if not np.isfinite(source).all() or np.linalg.norm(source) <= 1e-12:
        return {"flag": False, "evidence": {"release_profile": "unavailable"}}

    labels = c.get("window_ids")
    if labels is None:
        labels = np.zeros(len(y), dtype=int)
    labels = np.asarray(labels)
    trend_values = c.get("bg_times")
    trend = times if trend_values is None else np.asarray(trend_values, float)
    windows = sorted(set(labels.tolist()))
    nuisance = np.column_stack(
        [
            column
            for window in windows
            for column in (
                (labels == window).astype(float),
                (labels == window) * trend / 3600,
            )
        ]
    )
    try:
        chol = np.linalg.cholesky(covariance)
        yw = solve_triangular(chol, y, lower=True, check_finite=False)
        nw = solve_triangular(chol, nuisance, lower=True, check_finite=False)
        sw = solve_triangular(
            chol, source[:, None], lower=True, check_finite=False
        )[:, 0]
    except (np.linalg.LinAlgError, ValueError):
        return {"flag": False, "evidence": {"release_profile": "unavailable"}}
    try:
        u, singular, _ = np.linalg.svd(nw, full_matrices=False)
        cutoff = np.finfo(float).eps * max(nw.shape) * (singular[0] if len(singular) else 0)
        basis = u[:, singular > cutoff]
        yp = yw - basis @ (basis.T @ yw)
        sp = sw - basis @ (basis.T @ sw)
    except np.linalg.LinAlgError:
        return {"flag": False, "evidence": {"release_profile": "unavailable"}}
    midpoint = float(np.median(times))
    early = times <= midpoint
    late = times > midpoint
    if early.sum() < 2 or late.sum() < 2:
        return {"flag": False, "evidence": {"release_profile": "unavailable"}}
    design = np.column_stack((sp, sp * early, sp * late))
    try:
        constant_fit, constant_loss = nnls(design[:, :1], yp)
        variable_fit, variable_loss = nnls(design[:, 1:], yp)
    except (ValueError, np.linalg.LinAlgError):
        return {"flag": False, "evidence": {"release_profile": "unavailable"}}
    constant_loss = float(constant_loss**2)
    variable_loss = float(variable_loss**2)
    improvement = max(0.0, constant_loss - variable_loss)
    # Both halves must carry signal; otherwise the comparison is simply a
    # one-source fit with a redundant zero column.
    active = bool(
        min(variable_fit) > 0
        and improvement >= CONFIG["externality_pair_delta_chi2"]
    )
    return {
        "flag": active,
        "evidence": {
            "release_profile": "two_half_nonnegative_gls",
            "release_profile_constant_loss": constant_loss,
            "release_profile_variable_loss": variable_loss,
            "release_profile_improvement_delta_chi2": improvement,
            "release_profile_early_strength": float(variable_fit[0]),
            "release_profile_late_strength": float(variable_fit[1]),
        },
    }
