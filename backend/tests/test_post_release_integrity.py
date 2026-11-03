"""Regression checks for the post-release metadata integrity patch."""

import pytest

from upwind.fixtures import synthetic_case
from upwind.inference import fit
from upwind.models import Investigation, Measurement
from upwind.inference import MODEL_VERSION, PROTOCOL_VERSION
from upwind.quality import measurement_quality
from upwind.weather import matched_weather


def test_measurement_metadata_conflict_is_not_deduplicated():
    row = Measurement(
        sensor_id="sensor-a",
        timestamp="2026-01-01T00:00:00Z",
        latitude=40,
        longitude=-75,
        pm25_ug_m3=10,
        flags=[],
    )
    conflicting = row.model_copy(update={"humidity_percent": 55})
    usable, quality = measurement_quality(
        Investigation(measurements=[row, conflicting])
    )
    assert usable == []
    assert quality["identical_duplicates"] == 0
    assert quality["conflicting_keys"] == [
        {"sensor_id": "sensor-a", "timestamp": row.timestamp, "rows": 2}
    ]


def test_importer_duplicate_marker_does_not_make_identical_rows_conflict():
    row = Measurement(
        sensor_id="sensor-a",
        timestamp="2026-01-01T00:00:00Z",
        latitude=40,
        longitude=-75,
        pm25_ug_m3=10,
        flags=[],
    )
    duplicate = row.model_copy(update={"flags": ["duplicate"]})
    usable, quality = measurement_quality(
        Investigation(measurements=[row, duplicate])
    )
    assert len(usable) == 1
    assert quality["identical_duplicates"] == 1
    assert not quality["conflicting_keys"]


def test_weather_duplicate_provenance_conflict_is_refused():
    inv, _ = synthetic_case()
    fitted = fit(inv, diagnostics=False)
    first = inv.weather[0]
    inv.weather = [first, first.model_copy(update={"provenance": "other"})]
    with pytest.raises(ValueError, match="Conflicting duplicate meteorology"):
        matched_weather(inv, inv.measurements[:2], fitted["projection"])


def test_identical_weather_duplicate_remains_order_independent():
    inv, _ = synthetic_case()
    fitted = fit(inv, diagnostics=False)
    first = inv.weather[0]
    inv.weather = [first, first.model_copy()]
    matched = matched_weather(inv, inv.measurements[:2], fitted["projection"])
    assert len(matched[0]) == 2
    assert all(w.model_dump() == first.model_dump() for w in matched[0])


def test_linear_algebra_failure_is_reported_as_analysis_refusal(monkeypatch):
    import upwind.engine as engine

    inv, _ = synthetic_case()
    inv.concern = "unique linear algebra refusal regression"

    def fail(*args, **kwargs):
        raise __import__("numpy").linalg.LinAlgError("singular test matrix")

    monkeypatch.setattr(engine, "fit", fail)
    result = engine.analyze(inv)
    assert result["status"] == "insufficient_data"
    assert result["reason"] == "singular test matrix"


def test_protocol_revision_archives_same_model_result_before_reanalysis():
    inv, _ = synthetic_case()
    legacy = {
        "model_version": MODEL_VERSION,
        "protocol_version": "UW-ENGINE-OLD",
        "input_hash": "0" * 64,
        "status": "ok",
        "plans": [],
    }
    inv.result = legacy
    from upwind.models import migrate_analysis

    migrated = migrate_analysis(inv)
    assert migrated.result is None
    assert migrated.archived_results[0] == legacy
    assert PROTOCOL_VERSION in migrated.compatibility_notes[-1]


def test_health_reports_model_and_protocol_identifiers():
    from fastapi.testclient import TestClient
    from upwind.api import app

    payload = TestClient(app).get("/api/health").json()
    assert payload["model_version"] == MODEL_VERSION
    assert payload["protocol_version"] == PROTOCOL_VERSION
