"""Independent contracts for the externality-aware 0.7 candidate."""

import numpy as np

from upwind.engine import analyze
from upwind.fixtures import synthetic_case
import upwind.identifiability as identifiability
from upwind.identifiability import _externality_checks, _two_source_profile
from upwind.inference import CONFIG, PROTOCOL_VERSION, _base_cov


def test_humidity_response_is_sensor_persistent_and_missing_is_neutral():
    xy = np.array([[0.0, 0.0], [10.0, 0.0]])
    t = np.zeros(2)
    ids = np.array(["A", "A"])
    base = _base_cov(xy, t, ids, xy, t, ids, 1.0)
    humid = _base_cov(
        xy,
        t,
        ids,
        xy,
        t,
        ids,
        1.0,
        humidity=np.array([90.0, 90.0]),
        other_humidity=np.array([90.0, 90.0]),
    )
    missing = _base_cov(
        xy,
        t,
        ids,
        xy,
        t,
        ids,
        1.0,
        humidity=np.array([np.nan, np.nan]),
        other_humidity=np.array([np.nan, np.nan]),
    )
    assert np.allclose(missing, base)
    assert humid[0, 1] - base[0, 1] == CONFIG["humidity_response_sd_ug_m3"] ** 2


def test_humidity_covariance_rejects_one_sided_or_nonfinite_metadata():
    xy = np.array([[0.0, 0.0]])
    with np.testing.assert_raises(ValueError):
        _base_cov(xy, np.zeros(1), np.array(["A"]), xy, np.zeros(1), np.array(["A"]), 1.0, humidity=np.array([80.0]))
    with np.testing.assert_raises(ValueError):
        _base_cov(
            xy,
            np.zeros(1),
            np.array(["A"]),
            xy,
            np.zeros(1),
            np.array(["A"]),
            1.0,
            humidity=np.array([np.inf]),
            other_humidity=np.array([np.inf]),
        )


def test_two_source_profile_requires_two_active_separated_sources():
    profile = {
        "loss": np.array([20.0, 20.0, 20.0]),
        "projected_signatures": np.array(
            [[1.0, 0.0, 0.5], [0.0, 1.0, 0.5], [0.0, 0.0, 0.1]]
        ),
        "projected_observed": np.array([1.0, 1.0, 0.0]),
    }
    fitted = {"source_xy": np.array([[0.0, 0.0], [100.0, 0.0], [200.0, 0.0]])}
    result = _two_source_profile(profile, np.array([0, 1, 2]), fitted)
    assert result["material_competing_pair"]
    assert result["separation_m"] >= 50


def test_two_source_profile_cannot_borrow_distinct_persistent_weather_offsets():
    profile = {
        "loss": np.array([20.0, 20.0]),
        "projected_signatures": np.eye(2),
        "projected_observed": np.array([1.0, 1.0]),
        "weather_offsets": np.array([0.0, 20.0]),
    }
    fitted = {"source_xy": np.array([[0.0, 0.0], [100.0, 0.0]])}
    result = _two_source_profile(profile, np.array([0, 1]), fitted)
    assert not result["material_competing_pair"]
    assert result["source_cells"] == []


def test_two_source_profile_refuses_nonfinite_nnls(monkeypatch):
    profile = {
        "loss": np.array([20.0, 19.0]),
        "projected_signatures": np.eye(2),
        "projected_observed": np.array([1.0, 1.0]),
    }
    fitted = {"source_xy": np.array([[0.0, 0.0], [100.0, 0.0]])}

    def nonfinite_nnls(*args, **kwargs):
        return np.array([np.nan, np.inf]), np.inf

    monkeypatch.setattr(identifiability, "nnls", nonfinite_nnls)
    result = _two_source_profile(profile, np.array([0, 1]), fitted)
    assert result["diagnostic_unavailable"]
    assert result["invalid_pair_fits"] == 1
    assert result["source_cells"] == []
    assert not result["material_competing_pair"]


def test_structured_externality_blocks_resolution_without_diagnosing_cause():
    fitted = {
        "observed_values": np.array([0.0, 0.0, 10.0, 10.0]),
        "fitted_values": np.zeros(4),
        "observation_covariance": np.eye(4),
        "profile_context": {
            "humidity": np.array([50.0, 50.0, 50.0, 50.0]),
            "times": np.array([0.0, 1.0, 2.0, 3.0]),
            "sensor_ids": np.array(["A", "A", "A", "A"]),
            "coordinates": np.zeros((4, 2)),
        },
    }
    result = _externality_checks(fitted)
    assert result["blocking"]
    assert "heavy_tails_or_unflagged_event" in result["flags"]
    assert "not diagnoses" in result["meaning"]


def test_analysis_exposes_new_protocol_and_externality_sections():
    inv, _ = synthetic_case()
    result = analyze(inv)
    assert result["protocol_version"] == PROTOCOL_VERSION == "UW-ENGINE-2026-09"
    assert "externalities" in result["observability"]
    assert "source_count" in result["observability"]
