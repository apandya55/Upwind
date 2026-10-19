"""Deterministic Bayes-linear design for a separately declared prediction task."""

import numpy as np
from scipy.linalg import cho_solve
from .quality import measurement_quality


def risk_score(observation_covariance, target_observation_covariance):
    """Mean target-variance reduction C_TA C_AA^-1 C_AT.

    Correct for the optimal linear predictor under the supplied joint moments,
    even for a non-Gaussian mixture. Not exact nonlinear posterior Bayes risk.
    Target and observation instruments must have independent readout errors.
    """
    c = np.asarray(observation_covariance, dtype=float)
    cross = np.asarray(target_observation_covariance, dtype=float)
    if (
        c.ndim != 2
        or c.shape[0] != c.shape[1]
        or cross.ndim != 2
        or cross.shape[1] != len(c)
        or not len(cross)
        or not np.isfinite(c).all()
        or not np.isfinite(cross).all()
        or not np.allclose(c, c.T)
    ):
        raise ValueError(
            "Compatible finite observation and target cross-covariances required"
        )
    np.linalg.cholesky(c)
    cache = {(): 0.0}

    def score(indices):
        key = tuple(sorted(indices))
        if len(key) != len(set(key)) or any(
            not isinstance(i, (int, np.integer)) or not 0 <= i < len(c) for i in key
        ):
            raise ValueError("Unique in-range observation indices required")
        if key not in cache:
            a = c[np.ix_(key, key)]
            b = cross[:, key]
            chol = np.linalg.cholesky(a)
            cache[key] = float(np.sum(b * cho_solve((chol, True), b.T).T) / len(cross))
        return cache[key]

    return score


def prediction_score(inv, fitted):
    # Fixed permissible target universe does not change with budget, source truth,
    # chosen sites or hidden outcomes. Unsupported receptors are explicit exclusions.
    order = sorted(range(len(inv.sites)), key=lambda i: inv.sites[i].id)
    candidates = [
        i
        for i in order
        if inv.sites[i].kind == "candidate"
        and inv.sites[i].allowed
        and inv.sites[i].power
        and inv.sites[i].access
        and inv.settings.window in inv.sites[i].windows
        and fitted["candidate_supported"][i]
    ]
    if not candidates:
        return lambda indices: 0.0, {
            "method": "Bayes-linear prediction variance reduction",
            "target_sites": [],
        }
    sites = [inv.sites[i] for i in candidates]
    timestamp = max(m.timestamp for m in measurement_quality(inv)[0])
    # Two distinct instruments at each coordinate: no reward for merely knowing
    # the selected noisy readout rather than predicting a separate receptor.
    points = sites + sites
    observation_ids = [f"followup-{s.id}" for s in sites]
    used = {m.sensor_id for m in inv.measurements} | set(observation_ids)
    target_ids = []
    for site in sites:
        instrument = f"prediction-target-{site.id}"
        while instrument in used:
            instrument = "new-" + instrument
        target_ids.append(instrument)
        used.add(instrument)
    ids = observation_ids + target_ids
    _, cov = fitted["prediction_moments"](points, [timestamp] * len(points), ids)
    n = len(sites)
    inner = risk_score(cov[:n, :n], cov[n:, :n])
    rank = {site: i for i, site in enumerate(candidates)}

    def score(indices):
        return inner([rank[i] for i in indices])

    return score, {
        "method": "Bayes-linear mean prediction-variance reduction; all posterior mixture moments, no component subsampling or Monte Carlo draws",
        "target_sites": [s.id for s in sites],
        "target_count": n,
        "target_weighting": "uniform over all permissible supported candidate receptors, independent of affordability",
        "measurement_timestamp": timestamp,
        "target_instrument_ids": target_ids,
        "units": "(ug/m3)^2",
        "task": "Spatial concentration prediction at separate instruments; not source localization or health benefit",
        "limitations": "Moment-optimal linear prediction under the declared model. Actual nonlinear refits and transport mismatch can lose to baselines; no future weather or percent improvement guarantee.",
    }
