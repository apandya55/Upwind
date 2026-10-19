"""Independent weather/evidence arithmetic and compatibility contracts."""

import numpy as np
import pytest
from upwind.fixtures import synthetic_case
from upwind.weather_evidence import (
    station_distribution,
    weather_grid,
    wrap,
    update_normal,
)
from upwind.numerics import projector


def comparison_case(offset=-25.0):
    inv, _ = synthetic_case()
    for w in inv.weather:
        w.upstream_id = "primary-instrument"
        w.source_id = "station-A"
    inv.weather += [
        w.model_copy(
            update={
                "role": "reference",
                "source_id": "reference-B",
                "upstream_id": "independent-B",
                "wind_from_deg": float((w.wind_from_deg + offset) % 360),
                "wind_speed_m_s": w.wind_speed_m_s * 0.8,
                "direction_systematic_sd_deg": 2.0,
                "speed_systematic_fraction": 0.03,
                "direction_random_sd_deg": 1.0,
                "comparison_provenance": "Synthetic paired-instrument calibration example",
            }
        )
        for w in inv.weather
    ]
    inv.settings.met_direction_sd_deg = 3.0
    inv.settings.met_speed_fraction = 0.05
    return inv


def distribution(inv):
    primary = [w for w in inv.weather if w.role == "primary"]
    tr = projector(primary[0].latitude, primary[0].longitude)
    return station_distribution(inv, tr, primary)


def test_persistent_station_floor_does_not_treat_provenance_string_as_calibration():
    inv, _ = synthetic_case()
    inv.settings.met_direction_sd_deg = 0.5
    inv.settings.met_uncertainty_provenance = "verified accurate"
    center, sd, _, _, summary = distribution(inv)
    assert center == 0 and sd >= 20 and summary["status"] == "unverified"


def test_paired_comparison_corrects_sign_speed_and_keeps_systematic_uncertainty():
    inv = comparison_case()
    center, sd, logmean, _, summary = distribution(inv)
    assert center == pytest.approx(-25, abs=0.7) and np.exp(logmean) == pytest.approx(
        0.8, abs=0.02
    )
    assert sd > 3 and summary["persistent_direction_sd_deg"] >= 1.98
    assert summary["comparison_count"] > 0 and not summary["weather_warning"]
    assert all(w.wind_from_deg == 270 for w in inv.weather if w.role == "primary")


def test_shared_upstream_cannot_verify_its_primary_or_average_away_systematic_error():
    inv = comparison_case()
    base = distribution(inv)
    refs = [w for w in inv.weather if w.role == "reference"]
    inv.weather += [
        w.model_copy(update={"source_id": f"product-{i}"})
        for i in range(10)
        for w in refs
    ]
    repeated = distribution(inv)
    assert repeated[-1]["independent_upstream_groups"] == 1
    assert repeated[-1]["persistent_direction_sd_deg"] >= 1.98
    assert repeated[-1]["comparison_count"] == base[-1]["comparison_count"]
    assert repeated[1] == pytest.approx(base[1], abs=1e-12)
    for w in inv.weather:
        if w.role == "reference":
            w.upstream_id = "primary-instrument"
    rejected = distribution(inv)
    assert rejected[-1]["status"] == "unverified" and rejected[1] >= 20
    assert rejected[-1]["comparison_count"] == 0


def test_circular_difference_and_quadrature_mass_across_north():
    inv = comparison_case(offset=2.0)
    for w in inv.weather:
        w.wind_from_deg = 359.0 if w.role == "primary" else 1.0
    center, sd, _, _, _ = distribution(inv)
    assert 1.8 < center < 2.1 and wrap(1.0 - 359.0) == 2
    primary = [w for w in inv.weather if w.role == "primary"]
    a, p, s, sp, summary = weather_grid(
        inv, projector(primary[0].latitude, primary[0].longitude), primary
    )
    assert (
        p.sum() == pytest.approx(1)
        and sp.sum() == pytest.approx(1)
        and np.isfinite(a).all()
    )
    assert p @ a == pytest.approx(center, abs=1e-10)


def test_correlated_comparison_posterior_matches_independent_numeric_integration():
    from scipy.integrate import quad
    from scipy.stats import multivariate_normal, norm

    values = np.array([-22.0, -26.0, -25.0])
    cov = np.array([[9.0, 4.0, 4.0], [4.0, 12.0, 4.0], [4.0, 4.0, 10.0]])
    actual = update_normal(values, cov, 20.0)
    f = lambda x: multivariate_normal.pdf(
        values, mean=np.full(3, x), cov=cov
    ) * norm.pdf(x, scale=20)
    z = quad(f, -100, 100, epsabs=1e-15)[0]
    mean = quad(lambda x: x * f(x), -100, 100, epsabs=1e-15)[0] / z
    variance = quad(lambda x: (x - mean) ** 2 * f(x), -100, 100, epsabs=1e-15)[0] / z
    assert actual[0] == pytest.approx(mean, abs=1e-8) and actual[
        1
    ] ** 2 == pytest.approx(variance, abs=1e-8)


def test_inconsistent_period_comparisons_raise_weather_screen_not_verified_label():
    inv = comparison_case()
    refs = [w for w in inv.weather if w.role == "reference"]
    for i, w in enumerate(refs):
        w.wind_from_deg = (270 + (-25 if i % 2 else 25)) % 360
    assert distribution(inv)[-1]["weather_warning"]


def test_saved_legacy_analysis_is_archived_and_requires_new_analysis(
    tmp_path, monkeypatch
):
    from upwind import store

    inv, _ = synthetic_case()
    inv.result = {
        "model_version": "plume-campaign-0.4.0",
        "input_hash": "0" * 64,
        "status": "ok",
        "plans": [],
        "source_probability": 1.0,
    }
    original = [w.model_dump() for w in inv.weather]
    monkeypatch.setenv("UPWIND_DATA_DIR", str(tmp_path))
    saved = store.save(inv)
    restored = store.load(saved.id)
    assert restored.result is None and restored.archived_results[0] == inv.result
    assert (
        restored.compatibility_notes
        and [w.model_dump() for w in restored.weather] == original
    )
    assert store.load(saved.id).archived_results == restored.archived_results


def test_reference_import_preserves_raw_roles_lineage_uncertainties_and_utc():
    from upwind.models import ImportRequest
    from upwind.importers import parse_csv

    raw = (
        "timestamp,latitude,longitude,wind_speed_m_s,wind_from_deg,role,source_id,upstream_id,direction_systematic_sd_deg,speed_systematic_fraction,direction_random_sd_deg,comparison_provenance\n"
        "2026-08-10T05:00-04:00,35,-80,2.5,359,primary,A,instrument-A,,,,\n"
        "2026-08-10T09:00Z,35,-80,2.4,1,reference,B,instrument-B,2,.03,1,paired calibration certificate claim\n"
    )
    rows, record = parse_csv(
        ImportRequest(csv=raw, kind="weather", units="m/s,degrees-from-north")
    )
    assert len(rows) == 2 and record.raw_csv == raw and record.summary["invalid"] == 0
    assert rows[0].timestamp == rows[1].timestamp == "2026-08-10T09:00:00+00:00"
    assert rows[1].direction_systematic_sd_deg == 2 and rows[1].role == "reference"
    assert rows[0].wind_from_deg == 359 and rows[1].wind_from_deg == 1


def test_far_async_and_stale_reference_records_do_not_constrain_bias():
    from datetime import datetime, timedelta

    for kind in ("far", "async", "stale"):
        inv = comparison_case()
        matched = [w for w in inv.weather if w.role == "primary"]
        if kind == "stale":
            old = [
                w.model_copy(
                    update={
                        "timestamp": (
                            datetime.fromisoformat(w.timestamp) - timedelta(days=20)
                        ).isoformat()
                    }
                )
                for w in inv.weather
            ]
            inv.weather = [w for w in inv.weather if w.role == "primary"] + old
        else:
            for w in inv.weather:
                if w.role == "reference":
                    if kind == "far":
                        w.latitude += 0.1
                    else:
                        w.timestamp = (
                            datetime.fromisoformat(w.timestamp) + timedelta(minutes=40)
                        ).isoformat()
        tr = projector(matched[0].latitude, matched[0].longitude)
        result = station_distribution(inv, tr, matched)
        assert result[-1]["status"] == "unverified" and result[1] >= 20


def test_comparison_limit_is_explicit_and_raw_data_remain_available():
    inv = comparison_case()
    refs = [w for w in inv.weather if w.role == "reference"]
    inv.weather += [
        w.model_copy(
            update={"source_id": f"product-{i}", "upstream_id": f"independent-{i}"}
        )
        for i in range(40)
        for w in refs
    ]
    with pytest.raises(ValueError, match="128 eligible"):
        distribution(inv)
    assert len(inv.weather) > 128


def test_weather_cache_configuration_changes_input_hash_and_does_not_reuse_result(
    monkeypatch,
):
    from upwind.engine import analyze
    from upwind.weather_evidence import WEATHER_CONFIG

    inv, _ = synthetic_case()
    a = analyze(inv)
    monkeypatch.setitem(WEATHER_CONFIG, "station_direction_bias_sd_deg", 25.0)
    b = analyze(inv)
    assert a["input_hash"] != b["input_hash"]
    assert a["meteorology_evidence"]["persistent_direction_sd_deg"] == 20
    assert b["meteorology_evidence"]["persistent_direction_sd_deg"] == 25


def test_weather_evidence_html_and_legacy_api_import_preserve_archive(
    tmp_path, monkeypatch
):
    from fastapi.testclient import TestClient
    from upwind.api import app
    from upwind.engine import analyze
    from upwind.report import evidence_report

    monkeypatch.setenv("UPWIND_DATA_DIR", str(tmp_path))
    inv = comparison_case()
    inv.result = analyze(inv)
    report = evidence_report(inv)
    assert (
        "Weather-only direction correction" in report
        and "not measured calibration" in report
    )
    assert "user-declared provenance" in report and "weather hardware" in report
    legacy = {
        "model_version": "plume-campaign-0.4.0",
        "input_hash": "0" * 64,
        "status": "ok",
        "plans": [],
        "source_probability": 1.0,
    }
    inv.result = legacy
    response = TestClient(app).post("/api/investigations/import", json=inv.model_dump())
    assert response.status_code == 200
    restored = response.json()
    assert restored["result"] is None and restored["archived_results"][0] == legacy
    assert restored["weather"] == [w.model_dump() for w in inv.weather]


def test_disagreeing_same_upstream_products_are_not_independent_calibration():
    inv = comparison_case()
    ref = next(w for w in inv.weather if w.role == "reference")
    inv.weather.append(
        ref.model_copy(
            update={
                "source_id": "derived-product",
                "wind_from_deg": ref.wind_from_deg + 1,
            }
        )
    )
    with pytest.raises(ValueError, match="sharing an upstream timestamp disagree"):
        distribution(inv)


def test_shared_hidden_reference_bias_is_unobservable_and_not_verified():
    inv = comparison_case(offset=0.0)
    center, _, _, _, evidence = distribution(inv)
    assert center == pytest.approx(0.0) and not evidence["weather_warning"]
    assert evidence["status"] == "comparison_supplied"
    assert "not externally verified" in evidence["meaning"]


def test_chunked_plume_columns_match_independent_scalar_cardinal_rotation():
    from upwind.inference import plume_columns
    from upwind.validation.cases import scalar_plume

    sources = np.tile(np.array([[-200.0, 0.0]]), (2051, 1))
    receivers = np.array([[100.0, 0.0], [100.0, 40.0]])
    offsets = np.linspace(-20, 20, len(sources))
    result = plume_columns(
        receivers,
        sources,
        np.array([2.0, 3.0]),
        np.array([270.0, 270.0]),
        offsets,
        5.0,
        2.0,
    )
    for i in (0, 2047, 2048, 2050):
        for j in range(2):
            expected = scalar_plume(
                receivers[j], sources[i], 1.0, [2.0, 3.0][j], 270.0 + offsets[i]
            )
            assert result[j, i] == pytest.approx(expected, rel=1e-12, abs=1e-16)
    # Rotating coordinates90deg CCW rotates meteorological wind-from90deg backwards.
    rot = np.array([[0.0, -1.0], [1.0, 0.0]])
    rotated = plume_columns(
        receivers @ rot.T,
        sources @ rot.T,
        np.array([2.0, 3.0]),
        np.array([180.0, 180.0]),
        offsets,
        5.0,
        2.0,
    )
    assert rotated == pytest.approx(result, rel=1e-11, abs=1e-16)


def test_weather_only_mismatch_blocks_source_support_and_explains_used_evidence():
    from upwind.engine import analyze
    from upwind.report import evidence_report

    inv = comparison_case()
    for i, w in enumerate(w for w in inv.weather if w.role == "reference"):
        w.wind_from_deg = (270 + (-25 if i % 2 else 25)) % 360
    inv.result = analyze(inv)
    assert inv.result["meteorology_evidence"]["weather_warning"]
    assert inv.result["evidence_status"] == "model_mismatch"
    used = inv.result["meteorology_evidence"]["comparisons_used"]
    assert len(used) == 7 and used[0]["upstream_id"] == "independent-B"
    report = evidence_report(inv)
    assert "weather or held-out predictive checks flag a mismatch" in report
    assert "Comparison readings used (user-declared provenance)" in report
    assert "reference-B" in report and "Synthetic paired-instrument" in report
