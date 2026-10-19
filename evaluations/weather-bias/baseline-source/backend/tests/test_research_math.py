"""Independent GLS/linear-risk/campaign checks, not localization benchmark assertions."""

import numpy as np
import pytest
from scipy.optimize import nnls
from upwind.identifiability import whiten_profile, pair_separation, local_resolution
from upwind.prediction_design import risk_score
from upwind.inference import fit
from upwind.models import StudyWindow, Investigation
from upwind.fixtures import synthetic_case


def test_profile_matches_independent_nonnegative_least_squares():
    rng = np.random.default_rng(15)
    y = rng.normal(size=8)
    g = rng.uniform(size=(8, 7))
    a = rng.normal(size=(8, 8))
    cov = a @ a.T + np.eye(8)
    nuisance = np.column_stack((np.ones(8), np.linspace(-1, 1, 8)))
    out = whiten_profile(y, g, cov, nuisance)
    L = np.linalg.cholesky(cov)
    # NNLS signed nuisance represented by +/- pairs, independent constraint solver.
    for i in range(g.shape[1]):
        X = np.column_stack((g[:, i], nuisance, -nuisance))
        beta, residual = nnls(np.linalg.solve(L, X), np.linalg.solve(L, y))
        assert out["loss"][i] == pytest.approx(residual**2, abs=1e-10)
        assert out["strength"][i] == pytest.approx(beta[0], abs=1e-9)


def test_strength_background_equivalence_has_zero_global_separation():
    x = np.linspace(0, 1, 5)
    g = np.column_stack((x, 3 * x + 2, x * x))
    separation = pair_separation(g, np.eye(5), np.ones((5, 1)), 10)
    assert separation[0, 1] < 1e-12 and separation[1, 0] < 1e-10
    assert separation[0, 2] > 0
    local = local_resolution(np.column_stack((x, x)), x, np.eye(5), np.ones((5, 1)), 10)
    assert local["local_one_sigma_axes_m"] == [None, None]


def test_prediction_risk_matches_scalar_conditioning_and_joint_exhaustive():
    C = np.array([[5.0, 2.0], [2.0, 4.0]])
    cross = np.array([[1.0, 2.0], [2.0, 0.5]])
    score = risk_score(C, cross)
    assert score([]) == 0
    assert score([0]) == pytest.approx(np.mean(cross[:, 0] ** 2) / 5)
    expected = np.trace(cross @ np.linalg.inv(C) @ cross.T) / 2
    assert score([1, 0]) == pytest.approx(expected)
    assert score([1, 0]) >= max(score([0]), score([1]))
    with pytest.raises(ValueError):
        score([0, 0])


def test_prediction_risk_is_realized_optimal_linear_mse_under_independent_draws():
    rng = np.random.default_rng(18)
    # 100k draws resolve a moderate 0.5 variance reduction to <0.02 MSE.
    cov = np.array([[2.0, 1.0], [1.0, 1.0]])
    samples = rng.multivariate_normal([0, 0], cov, size=100000)
    score = risk_score(cov[1:, 1:], cov[:1, 1:])
    mse_before = np.mean(samples[:, 0] ** 2)
    mse_after = np.mean((samples[:, 0] - samples[:, 1]) ** 2)
    assert mse_before - mse_after == pytest.approx(score([0]), abs=0.03)


def test_total_prediction_moments_match_full_component_covariance():
    inv, _ = synthetic_case()
    e = fit(inv, diagnostics=False)
    points = [s for i, s in enumerate(inv.sites) if e["candidate_supported"][i]][:3]
    mu, cov = e["predictive"](points)
    w = e["weights"]
    average = w @ mu
    expected = np.einsum("k,kij->ij", w, cov) + ((mu - average).T * w) @ (mu - average)
    actual_mean, actual_cov = e["prediction_moments"](points)
    assert np.allclose(actual_mean, average, atol=1e-12)
    assert np.allclose(actual_cov, expected, atol=1e-10)


def test_campaign_refuses_silent_segmentation_and_requires_assumption():
    inv, _ = synthetic_case()
    inv.study_windows = [
        StudyWindow(id="a", start="2025-06-12T10:00Z", end="2025-06-12T10:30Z"),
        StudyWindow(id="b", start="2025-06-12T12:00Z", end="2025-06-12T12:30Z"),
    ]
    with pytest.raises(ValueError, match="constant release"):
        fit(inv, diagnostics=False)
    data = inv.model_dump()
    data["study_windows"][1]["start"] = "2025-06-12T10:30Z"
    data["study_windows"][1]["end"] = "2025-06-12T11:00Z"
    with pytest.raises(ValueError, match="overlap"):
        Investigation.model_validate(data)


def test_exact_predictive_density_against_independent_joint_evidence(monkeypatch):
    from datetime import timedelta
    from scipy.stats import multivariate_normal
    from test_inference_math import (
        small_study,
        START,
        point_at,
        projected_points,
        covariance_oracle,
        unit_plume_oracle,
        integrated_strength,
    )
    from upwind.inference import CONFIG
    from upwind.models import Point

    monkeypatch.setitem(CONFIG, "wind_offsets_deg", [0.0])
    monkeypatch.setitem(CONFIG, "speed_scales", [1.0])
    monkeypatch.setitem(CONFIG, "speed_prior", [1.0])
    inv = small_study()
    f = fit(inv, diagnostics=False)
    points = [Point(**point_at(230, 15))]
    stamp = (START + timedelta(seconds=300)).isoformat()
    xy = projected_points(f["projection"], f["rows"])
    future = projected_points(f["projection"], points)
    stamps = np.array([0.0, 120.0, 240.0])
    center = 120.0
    ids = np.array([r.sensor_id for r in f["rows"]])
    sigma = np.array([r.uncertainty_ug_m3 for r in f["rows"]])
    all_xy = np.vstack((xy, future))
    times = np.r_[stamps - center, 300 - center]
    all_ids = np.concatenate((ids, np.array(["new"])))
    unc = np.r_[sigma, 0.9]
    covariance = covariance_oracle(
        all_xy, times, all_ids, all_xy, times, all_ids, inv.settings.noise_ug_m3
    ) + np.diag(unc**2)
    observed = np.array([r.pm25_ug_m3 for r in f["rows"]])
    base = CONFIG["background_mean_ug_m3"]
    train_bg = multivariate_normal.pdf(
        observed, mean=np.full(3, base), cov=covariance[:3, :3]
    )
    denominator = 0.5 * train_bg
    sources = projected_points(f["projection"], inv.source_locations)
    train_source = []
    for source in sources:
        g = unit_plume_oracle(all_xy, source, 2.0)
        evidence, _, _ = integrated_strength(observed, base, covariance[:3, :3], g[:3])
        denominator += 0.25 * evidence
        train_source.append(g)
    for value in (6.0, 12.0, 25.0):
        all_y = np.r_[observed, value]
        numerator = 0.5 * multivariate_normal.pdf(
            all_y, mean=np.full(4, base), cov=covariance
        )
        for g in train_source:
            evidence, _, _ = integrated_strength(all_y, base, covariance, g)
            numerator += 0.25 * evidence
        actual = np.exp(
            f["predictive_log_density"](
                [value], points, [stamp], ["new"], uncertainties=[0.9]
            )
        )[0]
        assert actual == pytest.approx(numerator / denominator, rel=2e-8, abs=1e-13)
    mean, cov = f["prediction_moments"](points, [stamp], ["new"], uncertainties=[0.9])
    samples = f["predictive_draws"](
        points, [stamp], ["new"], uncertainties=[0.9], samples=8192, seed=12
    )
    assert samples.mean() == pytest.approx(mean[0], abs=0.02)
    assert samples.var() == pytest.approx(cov[0, 0], rel=0.025)


def test_joint_tail_matches_known_multivariate_normal_and_background_contrast():
    from scipy.stats import chi2
    from upwind.predictive_checks import joint_tail

    rng = np.random.default_rng(19)
    cov = np.array([[2.0, 1.0], [1.0, 3.0]])
    samples = rng.multivariate_normal(np.zeros(2), cov, 100000)
    observed = np.array([3.0, -1.0])
    expected = chi2.sf(observed @ np.linalg.solve(cov, observed), 2)
    assert joint_tail(np.zeros(2), cov, observed, samples)[
        "tail_probability"
    ] == pytest.approx(expected, abs=0.004)
    shift = np.ones(2) * 1000
    a = joint_tail(np.zeros(2), cov, observed, samples, np.ones((2, 1)))
    b = joint_tail(shift, cov, observed + shift, samples + shift, np.ones((2, 1)))
    assert a["tail_probability"] == b["tail_probability"]
    assert a["contrast_dimensions"] == 1


def test_campaign_moments_keep_shared_sensor_bias_across_windows():
    from upwind.inference import _base_cov

    xy = np.array([[0.0, 0.0], [0.0, 0.0]])
    times = np.array([0.0, 7200.0])
    ids = np.array(["A", "A"])
    period = np.array([0, 1])
    bg = np.zeros(2)
    cov = _base_cov(xy, times, ids, xy, times, ids, 1.0, period, period, bg, bg)
    assert cov[0, 1] == pytest.approx(1 + np.exp(-7200 / 600))
    assert cov[0, 0] == pytest.approx(402)


def test_independent_diffusion_generator_conserves_flux_and_solves_transverse_pde():
    from scipy.integrate import quad
    from upwind.validation.research.cases import diffusion_transport

    q, u = 25000.0, 2.5
    # Meteorological west wind gives x=east,y=north. Independent nested numeric
    # integration of the exported generator over y and reflected half-space z.
    for x in (50.0, 400.0):
        vertical = lambda z: quad(
            lambda y: float(
                diffusion_transport([[x, y]], [0, 0], q, u, 270, receptor_height=z)[0]
            ),
            -500,
            500,
            epsabs=1e-8,
        )[0]
        flux = u * quad(vertical, 0, 300, epsabs=1e-6)[0]
        assert flux == pytest.approx(q, rel=1e-7)
    x, y, z = 180.0, 8.0, 4.0
    h = 0.03
    f = lambda a, b, c: float(
        diffusion_transport([[a, b]], [0, 0], q, u, 270, receptor_height=c)[0]
    )
    dx = (f(x + h, y, z) - f(x - h, y, z)) / (2 * h)
    dyy = (f(x, y + h, z) - 2 * f(x, y, z) + f(x, y - h, z)) / h**2
    dzz = (f(x, y, z + h) - 2 * f(x, y, z) + f(x, y, z - h)) / h**2
    assert u * dx == pytest.approx(1.3 * dyy + 0.6 * dzz, rel=2e-5)


def test_campaign_selection_retains_sensor_period_pairs_and_utc_metadata():
    from upwind.campaign_fixture import synthetic_campaign
    from upwind.campaign import assignment

    inv = synthetic_campaign()
    inv.settings.inference_limit = 40
    f = fit(inv, diagnostics=False)
    labels, _ = assignment(inv, [m.timestamp for m in f["rows"]])
    assert len(set(zip([m.sensor_id for m in f["rows"]], labels))) == 24
    assert f["spatial_quadrature_order"] == 2
    assert f["integration_points"] == 4 * len(f["cells_xy"])
    data = inv.model_dump()
    data["study_windows"][1]["start"] = "2025-01-01T00:00"
    with pytest.raises(ValueError, match="offset"):
        Investigation.model_validate(data)


def test_campaign_more_than24_sensors_reports_diagnostic_subsampling_without_refusing_fit():
    from upwind.campaign_fixture import synthetic_campaign

    inv = synthetic_campaign()
    original = inv.measurements
    ids = sorted({m.sensor_id for m in original})
    inv.measurements = []
    for i in range(40):
        inv.measurements.extend(
            m.model_copy(update={"sensor_id": f"instrument-{i:02d}"})
            for m in original
            if m.sensor_id == ids[i % len(ids)]
        )
    inv.settings.inference_limit = 256
    # Small discrete domain isolates the many-instrument diagnostic contract.
    inv.source_locations = inv.source_locations[:2]
    f = fit(inv)
    checks = f["diagnostics"]["held_out_window"]
    assert len(checks) == 3
    assert all(
        c["rows"] == 24 and c["sensors_total"] == 40 and c["sensors_checked"] == 24
        for c in checks
    )
    assert not any(c.get("unavailable") for c in checks)


@pytest.mark.parametrize("fraction", [0.0, 0.000001, 0.05, 0.3])
def test_information_planner_keys_remain_unique_at_valid_speed_uncertainties(fraction):
    from upwind.engine import planning_score

    inv, _ = synthetic_case()
    inv.source_locations = inv.source_locations[:2]
    inv.settings.met_speed_fraction = fraction
    f = fit(inv, diagnostics=False)
    assert len(set(f["component_keys"])) == len(f["component_keys"])
    score, _ = planning_score(inv, f, max_components=32, samples=32, replicates=1)
    index = next(
        i
        for i, s in enumerate(inv.sites)
        if s.kind == "candidate" and f["candidate_supported"][i]
    )
    assert np.isfinite(score([index]))


def test_prediction_targets_are_fresh_even_if_user_instrument_id_collides():
    from upwind.prediction_design import prediction_score

    inv, _ = synthetic_case()
    site = next(s for s in inv.sites if s.kind == "candidate")
    inv.measurements[0].sensor_id = "prediction-target-" + site.id
    captured = {}

    def moments(points, timestamps, sensor_ids):
        captured["ids"] = sensor_ids
        return np.zeros(len(points)), np.eye(len(points))

    score, metadata = prediction_score(
        inv,
        {
            "candidate_supported": np.ones(len(inv.sites), dtype=bool),
            "prediction_moments": moments,
        },
    )
    assert not set(metadata["target_instrument_ids"]) & {
        m.sensor_id for m in inv.measurements
    }
    assert len(captured["ids"]) == len(set(captured["ids"]))
    assert score([]) == 0
