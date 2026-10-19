"""Independent identities and quadrature for discrete-mixture measurement design."""

import math
import numpy as np
import pytest
from scipy.integrate import quad
from scipy.special import logsumexp
from upwind.design import design_score


def exact_scalar_information(weights, groups, means, variances):
    """Adaptive density integration, independently of design estimator."""
    labels = np.unique(groups)
    prior = np.array([weights[groups == g].sum() for g in labels])

    def density_contribution(y):
        log_joint = np.log(weights) - 0.5 * (
            (y - means) ** 2 / variances + np.log(2 * np.pi * variances)
        )
        grouped = np.array([logsumexp(log_joint[groups == group]) for group in labels])
        overall = logsumexp(grouped)
        return float(np.sum(np.exp(grouped) * (grouped - np.log(prior) - overall)))

    low = float(np.min(means - 10 * np.sqrt(variances)))
    high = float(np.max(means + 10 * np.sqrt(variances)))
    return quad(
        density_contribution,
        low,
        high,
        points=sorted(set(means)),
        epsabs=1e-10,
        limit=500,
    )[0]


def scalar_callback(means, variances):
    means, variances = np.asarray(means, float), np.asarray(variances, float)

    def predictive(indices):
        assert indices == [0]
        return means[:, None], variances[:, None, None]

    return predictive


def test_equal_means_distinct_mixtures_recover_information():
    weights = np.full(4, 0.25)
    groups = np.array([0, 0, 1, 1])
    means = np.array([-3, 3, -0.5, 0.5])
    variances = np.full(4, 0.09)
    exact = exact_scalar_information(weights, groups, means, variances)
    assert exact > 0.69  # Both location-conditional means are zero.
    score, metadata = design_score(
        weights, groups, scalar_callback(means, variances), samples=1024, seed=61
    )
    assert score([0]) == pytest.approx(exact, abs=0.001)
    assert metadata["component_total_variation"] == 0
    assert metadata["score_calls"] == 1
    assert score([]) == 0


def test_finite_group_entropy_bound_and_exact_scalar_quadrature():
    weights = np.array([0.5, 0.5])
    groups = np.array([0, 1])
    means = np.array([-10, 10])
    variances = np.array([0.01, 0.01])
    score, metadata = design_score(weights, groups, scalar_callback(means, variances))
    assert score([0]) == pytest.approx(math.log(2), abs=1e-12)
    assert score([0]) <= metadata["target_entropy_nats"] + 1e-12
    assert exact_scalar_information(weights, groups, means, variances) == pytest.approx(
        math.log(2), abs=1e-10
    )


def test_covariance_shape_can_discriminate_and_identical_distributions_cannot():
    weights, groups = np.array([0.5, 0.5]), np.array([0, 1])
    exact = exact_scalar_information(
        weights, groups, np.zeros(2), np.array([0.04, 9.0])
    )
    score, _ = design_score(
        weights, groups, scalar_callback([0, 0], [0.04, 9]), samples=2048, seed=92
    )
    assert score([0]) == pytest.approx(exact, abs=0.003)
    identical, _ = design_score(
        [0.2, 0.8], groups, scalar_callback([4, 4], [2, 2]), seed=12
    )
    assert identical([0]) == pytest.approx(0, abs=1e-12)


def test_correlated_repeated_outcomes_have_less_information():
    def predictive(correlation):
        def output(indices):
            means = np.array([[-0.6, -0.6], [0.6, 0.6]])[:, indices]
            covariance = np.array([[1, correlation], [correlation, 1]])
            return means, np.broadcast_to(
                covariance[np.ix_(indices, indices)], (2, len(indices), len(indices))
            )

        return output

    independent, _ = design_score(
        [0.5, 0.5], np.array([0, 1]), predictive(0), samples=1024, seed=22
    )
    correlated, _ = design_score(
        [0.5, 0.5], np.array([0, 1]), predictive(0.95), samples=1024, seed=22
    )
    assert independent([0, 1]) > correlated([0, 1]) + 0.05
    assert correlated([1, 0]) == correlated([0, 1])
    assert correlated([0, 1]) >= correlated([0]) - 0.005


def test_group_mass_preserved_and_reduction_reported():
    weights = np.arange(1, 41, dtype=float)
    weights /= weights.sum()
    groups = np.arange(40) % 4
    score, metadata = design_score(
        weights,
        groups,
        scalar_callback(np.zeros(40), np.ones(40)),
        max_components=8,
        samples=32,
    )
    expected = [float(weights[groups == g].sum()) for g in np.unique(groups)]
    assert metadata["target_group_weights"] == pytest.approx(expected)
    assert metadata["represented_components"] <= 8
    assert metadata["positive_target_groups"] == 4
    assert metadata["component_reduction"]
    assert metadata["component_original_mass_represented"] < 1
    assert 0 < metadata["component_total_variation"] < 1
    assert score([0]) == pytest.approx(0, abs=1e-12)


def test_reduction_uses_available_budget_and_keeps_small_complete_mixture():
    # Low-mass groups must not lose components when the full mixture fits.
    weights = np.array([0.98] + [0.0002] * 100)
    groups = np.array([0] + [1] * 100)
    _, complete = design_score(
        weights,
        groups,
        scalar_callback(np.zeros(101), np.ones(101)),
        max_components=128,
    )
    assert complete["represented_components"] == 101
    assert not complete["component_reduction"]
    assert complete["component_total_variation"] == pytest.approx(0, abs=1e-12)
    # The high-mass singleton consumes one slot, leaving seven for the other group.
    _, reduced = design_score(
        weights, groups, scalar_callback(np.zeros(101), np.ones(101)), max_components=8
    )
    assert reduced["represented_components"] == 8


def test_component_permutation_invariance_with_canonical_keys():
    rng = np.random.default_rng(11)
    weights = rng.uniform(0.1, 1, 60)
    groups = np.arange(60) % 3
    means = rng.normal(size=60)
    variances = rng.uniform(0.5, 2, 60)
    keys = [f"component-{j:03}" for j in range(60)]
    first, meta_first = design_score(
        weights,
        groups,
        scalar_callback(means, variances),
        seed=5,
        max_components=12,
        component_keys=keys,
    )
    order = rng.permutation(60)
    second, meta_second = design_score(
        weights[order],
        groups[order],
        scalar_callback(means[order], variances[order]),
        seed=5,
        max_components=12,
        component_keys=[keys[i] for i in order],
    )
    assert first([0]) == pytest.approx(second([0]), abs=1e-12)
    assert meta_first["component_total_variation"] == pytest.approx(
        meta_second["component_total_variation"]
    )


def test_scoring_contract_fails_for_bad_covariance_or_unrepresented_group():
    with pytest.raises(ValueError, match="every positive"):
        design_score(
            [0.5, 0.5],
            np.array([0, 1]),
            scalar_callback([0, 1], [1, 1]),
            max_components=1,
        )
    score, _ = design_score([1.0], np.array([0]), scalar_callback([0], [-1]))
    with pytest.raises(ValueError, match="positive definite"):
        score([0])
    with pytest.raises(ValueError, match="unique"):
        score([0, 0])
    with pytest.raises(ValueError, match="weights"):
        design_score([np.nan], np.array([0]), scalar_callback([0], [1]))
