"""Integrity checks for the standalone NC release script."""
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("pyarrow")
SPEC = importlib.util.spec_from_file_location("export_benchmark", Path(__file__).resolve().parents[2] / "scripts/export_and_benchmark.py")
export = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(export)


def record(**changes):
    return {"id": "37-001-0001", "state_fips": "37", "county_fips": "37001",
            "site_number": "0001", "year": 2024, "latitude": 35.0, "longitude": -80.0,
            "pm25_ug_m3": 8.0, "sample_completeness": "Y", "units": "µg/m³",
            "metric": "Quarterly Means of Daily Means",
            "evidence_type": "measured_monitor_annual_summary", **changes}


def test_dedup_and_conflicts(tmp_path):
    path = tmp_path / "monitors.json"
    path.write_text(json.dumps([record(), record(), record(latitude=100)]))
    frame, audit = export.clean(path)
    assert len(frame) == 1
    assert audit["duplicate_nc_rows_removed"] == 1
    assert audit["rejected_nc_rows"] == 1
    assert frame[list(export.WEATHER)].isna().all().all()
    path.write_text(json.dumps([record(), record(pm25_ug_m3=9)]))
    with pytest.raises(ValueError, match="Conflicting"):
        export.clean(path)


def test_weather_and_metrics(tmp_path):
    path = tmp_path / "monitors.json"
    path.write_text(json.dumps([record()]))
    frame, _ = export.clean(path)
    weather = tmp_path / "weather.csv"
    weather.write_text("id,year,temperature_c,relative_humidity_pct,wind_speed_m_s\n37-001-0001,2024,15,,2\n")
    joined = export.join_weather(frame, weather)
    assert joined.temperature_c.iloc[0] == 15
    assert np.isnan(joined.relative_humidity_pct.iloc[0])
    weather.write_text(weather.read_text() + "37-001-0001,2024,18,50,2\n")
    with pytest.raises(ValueError, match="conflicting"):
        export.join_weather(frame, weather)
    assert export.scores([1, 2, 3], [1, 2, 3])["R2"] == 1
    assert export.scores([1, 1], [2, 2])["R2"] is None
    assert export.scores([1, 2, 3], [2, 3, 4])["RMSE"] == 1


def test_holdout_excludes_target(tmp_path, monkeypatch):
    path = tmp_path / "monitors.json"
    path.write_text(json.dumps([record(id=f"37-001-{i:04d}", site_number=f"{i:04d}", latitude=33+i, pm25_ug_m3=float(i)) for i in range(1, 6)]))
    frame, _ = export.clean(path)
    original = export.predict
    def checked(method, x, y, target):
        assert not set(map(tuple, x)) & set(map(tuple, target))
        return original(method, x, y, target)
    monkeypatch.setattr(export, "predict", checked)
    result = export.benchmark(frame)
    assert len(result) == 3 * len(frame)
    assert not result.duplicated(["id", "year", "method"]).any()
    timing = export.latency(frame, 1, 1)
    assert timing["queries_per_mode"] == 100
