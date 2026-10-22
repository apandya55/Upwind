"""Contracts for the v0.9 release-scale sensitivity gate."""

import numpy as np

from upwind import engine, inference
from upwind.fixtures import synthetic_case
from upwind.inference import _strength_prior_sensitivity
from upwind.numerics import projector


def test_single_window_uses_four_node_tensor_quadrature():
    inv, _ = synthetic_case()
    fitted = inference.fit(inv, diagnostics=False, wind_uncertainty=False)
    assert fitted["spatial_quadrature_order"] == 2
    assert fitted["integration_points"] == 4 * len(fitted["cells_xy"])
    baseline = next(
        row
        for row in fitted["strength_prior_sensitivity"]["alternatives"]
        if row["factor"] == 1.0
    )
    np.testing.assert_allclose(
        baseline["source_probability"], fitted["source_probability"], rtol=0, atol=1e-12
    )
    assert baseline["cell_tv_distance"] == 0.0
    assert baseline["posterior_mean_shift_m"] == 0.0


def test_strength_sensitivity_is_finite_and_flags_prior_dependent_location():
    result = _strength_prior_sensitivity(
        log_bg=-1.0,
        norm=np.array([1.0, 1.0]),
        dot=np.array([3.0, 1.0]),
        tau=np.array([1.0, 1.0]),
        base_index=np.array([0, 1]),
        base_integration=np.array([0, 1]),
        log_prior=np.log(np.array([0.5, 0.5])),
        integration_xy=np.array([[0.0, 0.0], [100.0, 0.0]]),
        integration_cell=np.array([0, 1]),
        cells=np.array([[-1.0, -1.0, 1.0, 1.0], [99.0, -1.0, 101.0, 1.0]]),
        baseline_cell_weights=np.array([0.5, 0.5]),
        baseline_mean_xy=np.array([50.0, 0.0]),
        bounds=(np.array([0.0, 0.0]), np.array([100.0, 0.0])),
        projection=projector(0.0, 0.0),
    )
    assert result["blocking"]
    assert result["material_factors"]
    for row in result["alternatives"]:
        assert np.isfinite(row["source_probability"])
        assert np.isfinite(row["spatial_rms_m"])
        assert np.isfinite(row["cell_tv_distance"])
        assert np.isfinite(row["posterior_mean_shift_m"])


def test_engine_withholds_support_for_material_prior_sensitivity(monkeypatch):
    inv, _ = synthetic_case()
    monkeypatch.setitem(inference.CONFIG, "strength_prior_sensitivity_cell_tv", 1e-12)
    engine._cached_analysis.cache_clear()
    try:
        result = engine.analyze(inv)
    finally:
        engine._cached_analysis.cache_clear()
    assert result["strength_prior_sensitivity"]["blocking"]
    assert result["observability"]["strength_prior_sensitivity"]["blocking"]
    assert result["evidence_status"] != "source_supported"
    assert any("EMISSION-PRIOR SENSITIVITY" in warning for warning in result["warnings"])
