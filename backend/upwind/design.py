"""Optimal sensor placement and experimental design algorithms."""

from collections.abc import Callable, Sequence
import math
import numpy as np
from scipy.special import logsumexp, ndtri
from scipy.stats import qmc

Predictive = Callable[[list[int]], tuple[np.ndarray, np.ndarray]]


def _entropy(probabilities):
    positive = probabilities[probabilities > 0]
    return float(-np.sum(positive * np.log(positive)))


def _allocate(probabilities, total, capacities=None):
    """Largest-remainder allocation with every positive group represented."""
    count = len(probabilities)
    if total < count:
        raise ValueError("Numerical budget must represent every positive group")
    if capacities is None:
        capacities = np.full(count, total, dtype=int)
    else:
        capacities = np.asarray(capacities, dtype=int)
        total = min(total, int(capacities.sum()))
    allocations = np.ones(count, dtype=int)
    remaining = total - count
    while remaining:
        active = np.flatnonzero(allocations < capacities)
        fractional = remaining * probabilities[active] / probabilities[active].sum()
        additions = np.minimum(
            np.floor(fractional).astype(int), capacities[active] - allocations[active]
        )
        if additions.sum():
            allocations[active] += additions
            remaining -= int(additions.sum())
            continue
        order = np.lexsort((active, -fractional))
        chosen = active[order[:remaining]]
        allocations[chosen] += 1
        remaining -= len(chosen)
    return allocations


def _represented_mixture(weights, groups, max_components, component_keys):
    labels, inverse = np.unique(groups, return_inverse=True)
    group_weights = np.bincount(inverse, weights=weights, minlength=len(labels))
    allocations = _allocate(group_weights, max_components, np.bincount(inverse))
    represented = np.zeros(len(weights))
    for group_index, number in enumerate(allocations):
        indices = np.flatnonzero(inverse == group_index)
        if component_keys is not None:
            indices = np.array(sorted(indices, key=lambda i: component_keys[i]))
        conditional = weights[indices] / group_weights[group_index]
        # Exact preservation when a group has no more components than its budget.
        if len(indices) <= number:
            represented[indices] = weights[indices]
            continue
        cumulative = np.cumsum(conditional)
        cumulative[-1] = 1
        samples = np.searchsorted(cumulative, (np.arange(number) + 0.5) / number)
        counts = np.bincount(samples, minlength=len(indices))
        represented[indices] = group_weights[group_index] * counts / number
    selected = np.flatnonzero(represented > 0)
    return selected, represented[selected], labels, group_weights, represented


def design_score(
    weights,
    groups,
    predictive: Predictive,
    seed=0,
    *,
    max_components=128,
    samples=128,
    replicates=2,
    component_keys: Sequence[str] | None = None,
):
    """Return ``(score(indices), metadata)`` for conditional group information.

    ``predictive(indices)`` returns means [K,d] and covariance [K,d,d], already
    conditional on past observations, for the K weighted mixture components.
    Groups identify the scientific target (e.g. background-only and coarse
    spatial anchor regions), rather than arbitrary nuisance configurations.

    Weighted-quantile component reduction preserves each positive group's mass.
    Every integration replicate stratifies by group and uses scrambled Sobol
    normal draws within groups. Raw entropy differences may be slightly negative
    from integration error; no clipping or probability tempering is applied.
    Replicate disagreement is a numerical diagnostic, not a confidence interval.

    Mixture reduction follows caller component order, or sorted unique supplied
    component_keys. Supplying stable keys makes reduction invariant to input
    component permutation. Source prediction accuracy is not assessed here.
    """
    w = np.asarray(weights, dtype=float)
    g = np.asarray(groups)
    if (
        w.ndim != 1
        or not len(w)
        or g.shape != w.shape
        or not np.issubdtype(g.dtype, np.integer)
        or not np.isfinite(w).all()
        or np.any(w < 0)
        or not np.isfinite(w.sum())
        or w.sum() <= 0
    ):
        raise ValueError(
            "Finite nonnegative weights and integer group per component required"
        )
    if not isinstance(seed, (int, np.integer)) or seed < 0:
        raise ValueError("Seed must be a nonnegative integer")
    for name, value in (
        ("max_components", max_components),
        ("samples", samples),
        ("replicates", replicates),
    ):
        if not isinstance(value, (int, np.integer)) or value < 1:
            raise ValueError(f"{name} must be a positive integer")
    if max_components > 2048 or samples > 4096 or replicates > 8:
        raise ValueError("Design numerical budget exceeds supported bounds")
    if component_keys is not None:
        if len(component_keys) != len(w) or len(set(component_keys)) != len(w):
            raise ValueError("Component keys must be unique and match mixture length")
    original_count = len(w)
    positive = np.flatnonzero(w > 0)
    w = w / w.sum()
    # Zero-weight groups cannot be learned and need no integration allocation.
    labels = np.unique(g[positive])
    if len(labels) > min(max_components, samples):
        raise ValueError("Design budget must represent every positive target group")
    selected, represented_w, labels, group_w, represented_full = _represented_mixture(
        w[positive],
        g[positive],
        max_components,
        None if component_keys is None else [component_keys[i] for i in positive],
    )
    retained_indices = positive[selected]
    retained_groups = g[retained_indices]
    # Maintain canonical integration order when callers provide component keys.
    if component_keys is not None:
        order = np.array(
            sorted(
                range(len(retained_indices)),
                key=lambda i: component_keys[retained_indices[i]],
            )
        )
        retained_indices, represented_w, retained_groups = (
            retained_indices[order],
            represented_w[order],
            retained_groups[order],
        )
    inverse = np.searchsorted(labels, retained_groups)
    group_w = np.bincount(inverse, weights=represented_w, minlength=len(labels))
    prior_entropy = _entropy(group_w)
    sample_counts = _allocate(group_w, samples)
    metadata = {
        "method": "discrete-mixture group information; stratified scrambled Sobol integration",
        "target": "caller-defined discrete groups",
        "seed": int(seed),
        "original_components": original_count,
        "positive_components": len(positive),
        "represented_components": len(retained_indices),
        "max_components": int(max_components),
        "positive_target_groups": len(labels),
        "target_group_labels": labels.tolist(),
        "target_group_weights": group_w.tolist(),
        "target_entropy_nats": prior_entropy,
        "component_original_mass_represented": float(w[retained_indices].sum()),
        "component_total_variation": float(
            0.5 * np.abs(represented_full - w[positive]).sum()
        ),
        "component_reduction": len(retained_indices) < len(positive),
        "component_order": "canonical keys"
        if component_keys is not None
        else "caller order",
        "samples_per_replicate": int(samples),
        "replicates": int(replicates),
        "covariance": "callback conditional on observed data; Gaussian per component",
        "score_calls": 0,
        "largest_replicate_range_nats": 0.0,
        "negative_estimates": 0,
        "limitations": [
            "Numerical group information under the supplied model, not demonstrated field improvement.",
            "Finite component and integration budgets can change plan rankings; assess convergence.",
            "Replicate disagreement does not bound systematic component-approximation error.",
        ],
    }
    cache = {(): 0.0}

    def score(indices):
        key = tuple(sorted(indices))
        if len(key) != len(set(key)) or any(
            not isinstance(i, (int, np.integer)) or i < 0 for i in key
        ):
            raise ValueError(
                "Selected sites must have unique nonnegative integer indices"
            )
        if key in cache:
            return cache[key]
        dimension = len(key)
        if dimension > 8:
            raise ValueError("At most eight simultaneous measurements supported")
        means, covariances = (np.asarray(x, dtype=float) for x in predictive(list(key)))
        if means.shape != (original_count, dimension) or covariances.shape != (
            original_count,
            dimension,
            dimension,
        ):
            raise ValueError(
                "Predictive callback returned incompatible component dimensions"
            )
        means, covariances = means[retained_indices], covariances[retained_indices]
        if not np.isfinite(means).all() or not np.isfinite(covariances).all():
            raise ValueError("Predictive moments must be finite")
        if not np.allclose(
            covariances, covariances.swapaxes(1, 2), rtol=1e-10, atol=1e-12
        ):
            raise ValueError("Predictive covariance must be symmetric")
        try:
            cholesky = np.linalg.cholesky(covariances)
        except np.linalg.LinAlgError as exc:
            raise ValueError("Predictive covariance must be positive definite") from exc
        log_weights = np.log(represented_w)
        log_normalizers = dimension * np.log(2 * np.pi) + 2 * np.log(
            np.diagonal(cholesky, axis1=1, axis2=2)
        ).sum(axis=1)
        results = []
        for replicate in range(replicates):
            observations, observation_weights = [], []
            for group_index, count in enumerate(sample_counts):
                component_indices = np.flatnonzero(inverse == group_index)
                conditional_w = represented_w[component_indices] / group_w[group_index]
                cumulative = np.cumsum(conditional_w)
                cumulative[-1] = 1
                # SeedSequence isolates streams without dependence on observed outcomes.
                stream_seed = int(
                    np.random.SeedSequence(
                        [int(seed), replicate, group_index]
                    ).generate_state(1)[0]
                )
                uniforms = qmc.Sobol(
                    d=dimension + 1, scramble=True, seed=stream_seed
                ).random_base2(math.ceil(math.log2(int(count))))[:count]
                chosen = component_indices[np.searchsorted(cumulative, uniforms[:, 0])]
                normal = ndtri(
                    np.clip(
                        uniforms[:, 1:], np.finfo(float).eps, 1 - np.finfo(float).eps
                    )
                )
                outcomes = means[chosen] + np.einsum(
                    "nij,nj->ni", cholesky[chosen], normal
                )
                observations.append(outcomes)
                observation_weights.extend([group_w[group_index] / count] * int(count))
            observations = np.concatenate(observations)
            residual = observations[None, :, :] - means[:, None, :]
            white = np.linalg.solve(cholesky, residual.swapaxes(1, 2))
            log_joint = (
                -0.5 * (np.sum(white**2, axis=1) + log_normalizers[:, None])
                + log_weights[:, None]
            )
            log_group_joint = np.stack(
                [
                    logsumexp(log_joint[inverse == group_index], axis=0)
                    for group_index in range(len(labels))
                ]
            )
            log_group_posterior = log_group_joint - logsumexp(log_group_joint, axis=0)
            posterior_entropy = -np.sum(
                np.exp(log_group_posterior) * log_group_posterior, axis=0
            )
            expected_entropy = np.asarray(observation_weights) @ posterior_entropy
            results.append(float(prior_entropy - expected_entropy))
        value = float(np.mean(results))
        if not np.isfinite(value):
            raise ValueError("Nonfinite information estimate")
        metadata["score_calls"] += 1
        metadata["largest_replicate_range_nats"] = max(
            metadata["largest_replicate_range_nats"], max(results) - min(results)
        )
        metadata["negative_estimates"] += int(value < 0)
        cache[key] = value
        return value

    return score, metadata
