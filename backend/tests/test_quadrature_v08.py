"""Numerical contracts for nested source/weather quadrature in engine 0.8."""

import numpy as np

from upwind import engine, inference
from upwind.fixtures import synthetic_case
from upwind.source_grid import posterior_region_structure, subdivide


def test_refinement_conserves_area_and_parent_mass_on_nested_rectangles():
    cells = np.array([[0.0, 0.0, 2.0, 1.0], [2.0, 0.0, 4.0, 1.0]])
    mass = np.array([0.7, 0.3])
    refined, count = subdivide(cells, mass, target=0.6, limit=1)
    assert count == 1
    assert np.isclose(np.prod(refined[:, 2:] - refined[:, :2], axis=1).sum(), 4.0)
    child_mass = np.zeros(2)
    for cell, weight in zip(refined, np.r_[np.repeat(0.7 / 4, 4), 0.3]):
        parent = 0 if cell[0] < 2 else 1
        child_mass[parent] += weight
    assert np.allclose(child_mass, mass)


def test_finite_fit_records_nested_convergence_and_region_components():
    inv, _ = synthetic_case()
    fitted = inference.fit(inv, diagnostics=False, wind_uncertainty=False)
    diagnostic = fitted["quadrature_diagnostics"]
    assert diagnostic["level_count"] >= 2
    assert diagnostic["converged"] is fitted["numerical_converged"]
    assert diagnostic["levels"][-1]["tolerance_pass"]
    assert set(diagnostic["levels"][-1]["deltas"]) == {
        "log_evidence",
        "source_probability",
        "cell_mass_tv",
        "posterior_mean_m",
        "covariance_relative",
        "region_mass",
        "region_area_fraction",
        "weather_mass_tv",
    }
    structure = fitted["posterior_region_structure"]
    assert structure["component_count"] >= 1
    assert np.isclose(fitted["cell_weights"].sum(), 1.0)


def test_source_region_reports_disjoint_mass_components():
    cells = np.array([[0, 0, 1, 1], [1, 0, 2, 1], [5, 0, 6, 1]], dtype=float)
    result = posterior_region_structure(cells, np.array([0.45, 0.45, 0.10]))
    assert result["component_count"] == 1
    disconnected = posterior_region_structure(cells, np.array([0.48, 0.02, 0.50]))
    assert disconnected["component_count"] == 2
    assert disconnected["minimum_component_centroid_separation_m"] > 3


def test_weather_marginal_projection_is_stable_under_nested_angular_spacing():
    projected = []
    for step in (2.0, 1.0, 0.5):
        angles = np.arange(-60.0, 60.0 + step / 2, step)
        mass = np.exp(-0.5 * (angles / 20.0) ** 2)
        mass /= mass.sum()
        projected.append(
            inference._weather_mass_vector(
                {
                    "weather_grid": {
                        "offsets": angles,
                        "speed_scales": np.array([1.0]),
                        "posterior_mass": mass[:, None],
                    }
                }
            )
        )
    for coarse, fine in zip(projected, projected[1:]):
        tv = 0.5 * sum(abs(coarse.get(k, 0.0) - fine.get(k, 0.0)) for k in coarse.keys() | fine.keys())
        assert tv < 0.05


def test_engine_withholds_resolution_when_nested_quadrature_does_not_converge(monkeypatch):
    inv, _ = synthetic_case()
    actual_fit = inference.fit
    # A single finite level cannot establish convergence. This deterministic
    # bound avoids relying on a particular fixture having nonzero adjacent-
    # level deltas under exact-zero tolerances.
    tight_policy = dict(inference.CONFIG["quadrature_policy"], max_levels=1)

    def nonconverged_fit(study, diagnostics=True):
        return actual_fit(
            study,
            diagnostics=diagnostics,
            wind_uncertainty=False,
            quadrature_policy=tight_policy,
        )

    monkeypatch.setattr(engine, "fit", nonconverged_fit)
    monkeypatch.setattr(inference, "fit", nonconverged_fit)
    # The analysis cache key intentionally omits callable identity; ensure the
    # monkeypatched path, rather than an earlier identical fixture result, runs.
    engine._cached_analysis.cache_clear()
    try:
        result = engine.analyze(inv)
    finally:
        engine._cached_analysis.cache_clear()
    assert result["status"] in {"ok", "uninformative"}
    assert result["numerical_converged"] is False
    assert result["evidence_status"] != "source_supported"
    assert any("NUMERICAL CONVERGENCE NOT ESTABLISHED" in w for w in result["warnings"])
