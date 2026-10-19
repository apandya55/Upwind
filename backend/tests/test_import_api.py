import csv
import io
import pytest
from fastapi.testclient import TestClient
from upwind.api import app
from upwind.models import ImportRequest, Investigation
from upwind.importers import parse_csv, utc_timestamp
from upwind.fixtures import synthetic_case
from upwind.report import measurements_csv, evidence_report

HEADER = "sensor_id,timestamp,latitude,longitude,pm25_ug_m3\n"


def test_campaign_analysis_save_restore_report_and_assumption_gate(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("UPWIND_DATA_DIR", str(tmp_path))
    client = TestClient(app)
    data = client.get("/api/demo/campaign").json()
    assert len(data["study_windows"]) == 4 and data["synthetic"]
    assert {m["origin"] for m in data["measurements"]} == {"synthetic"}
    response = client.post("/api/analyze", json=data)
    assert response.status_code == 200
    result = response.json()
    assert result["model_version"] == "plume-robust-0.6.0"
    assert result["study_window_count"] == 4 and result["spatial_quadrature_order"] == 2
    assert result["diagnostics"]["windows_checked"] == 3
    assert any(p["method"].startswith("Prediction variance") for p in result["plans"])
    data["result"] = result
    saved = client.post("/api/investigations", json=data)
    assert saved.status_code == 200
    id = saved.json()["id"]
    export = client.get(f"/api/investigations/{id}/export").json()
    assert export["study_windows"] == data["study_windows"]
    assert export["measurements"] == data["measurements"]
    assert (
        export["settings"]["met_uncertainty_provenance"]
        == data["settings"]["met_uncertainty_provenance"]
    )
    report = client.get(f"/api/investigations/{id}/report").text
    assert (
        "Cross-period predictive checks" in report
        and "Location distinguishability" in report
    )
    assert (
        "constant release across periods" in report
        and "SYNTHETIC DEMONSTRATION" in report
    )
    data["assumptions"]["constant_release_across_windows"] = False
    refused = client.post("/api/analyze", json=data)
    assert (
        refused.status_code == 200 and refused.json()["status"] == "insufficient_data"
    )
    assert "constant release" in refused.json()["reason"]


def test_raw_retained_flags_timezone_and_invalid():
    raw = (
        HEADER
        + "A,2025-06-12T10:00,40,-75,12\nA,2025-06-12T10:00,40,-75,-3\nB,2025-06-12T10:05,95,-75,NaN\n"
    )
    rows, record = parse_csv(ImportRequest(csv=raw, timezone="America/New_York"))
    assert record.raw_csv == raw
    assert record.summary["accepted"] == 2 and record.summary["invalid"] == 1
    assert rows[0].timestamp == "2025-06-12T14:00:00+00:00"
    assert rows[1].flags == ["duplicate", "negative"]
    assert record.summary["flagged"] == 1


def test_naive_dst_units_missing_and_empty():
    rows, record = parse_csv(
        ImportRequest(csv=HEADER + "A,2025-06-12T10:00,40,-75,12\n")
    )
    assert len(rows) == 0 and "timezone" in record.summary["issues"][0]["error"]
    with pytest.raises(ValueError, match="daylight"):
        utc_timestamp("2025-11-02T01:30:00", "America/New_York")
    with pytest.raises(ValueError, match="unit"):
        parse_csv(ImportRequest(csv=HEADER, units="mg/m3"))
    with pytest.raises(ValueError, match="Missing"):
        parse_csv(ImportRequest(csv="foo\n1"))
    with pytest.raises(ValueError, match="no data"):
        parse_csv(ImportRequest(csv=HEADER))


def test_mapping_and_weather_validation():
    rows, r = parse_csv(
        ImportRequest(
            csv="id,time,lat,lon,value\nA,2025-06-12T10:00Z,0,0,10\n",
            mapping={
                "sensor_id": "id",
                "timestamp": "time",
                "latitude": "lat",
                "longitude": "lon",
                "pm25_ug_m3": "value",
            },
        )
    )
    assert len(rows) == 1 and r.column_mapping["pm25_ug_m3"] == "value"
    raw = "timestamp,latitude,longitude,wind_speed_m_s,wind_from_deg\n2025-06-12T10:00Z,0,0,-2,270\n"
    rows, r = parse_csv(
        ImportRequest(csv=raw, kind="weather", units="m/s,degrees-from-north")
    )
    assert len(rows) == 0 and r.summary["invalid"] == 1


def test_invalid_row_does_not_hide_later_valid_row_and_synthetic_origin_survives():
    raw = (
        HEADER.replace("pm25_ug_m3", "pm25_ug_m3,origin")
        + "A,2025-06-12T10:00Z,95,0,10,synthetic\nA,2025-06-12T10:00Z,0,0,10,synthetic\nB\n"
    )
    rows, record = parse_csv(ImportRequest(csv=raw))
    assert len(rows) == 1 and rows[0].flags == []
    assert rows[0].origin == "synthetic" and record.summary["synthetic_rows"] == 1
    inv = Investigation(measurements=rows)
    assert inv.synthetic
    assert "SYNTHETIC DEMONSTRATION" in evidence_report(inv)
    assert "synthetic" in measurements_csv(inv)
    assert record.summary["invalid"] == 2


def test_aqs_adapter_contract_on_constructed_schema_only(tmp_path):
    import importlib.util
    from pathlib import Path
    import zipfile

    spec = importlib.util.spec_from_file_location(
        "aqs", Path(__file__).resolve().parents[2] / "scripts/acquire_aqs.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    archive = tmp_path / "constructed-not-real-aqs.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr(
            "sample.csv",
            "State Code,County Code,Site Num,POC,Date GMT,Time GMT,Latitude,Longitude,Sample Measurement,Units of Measure,Parameter Code,Sample Duration,Datum\n37,183,0014,1,2024-06-01,12:00,35.7,-78.6,10,Micrograms/cubic meter (LC),88101,1 HOUR,WGS84\n",
        )
    output = tmp_path / "output.csv"
    meta = module.convert(
        archive, output, "37", "2024-06-01", "2024-06-01", "https://aqs.epa.gov/example"
    )
    assert meta["rows"] == 1
    rows, record = parse_csv(ImportRequest(csv=output.read_text()))
    assert rows[0].sensor_id == "37-183-0014-POC1"
    assert rows[0].timestamp == "2024-06-01T12:00:00+00:00"


def test_save_reopen_export_restore_and_safe_report(tmp_path, monkeypatch):
    monkeypatch.setenv("UPWIND_DATA_DIR", str(tmp_path))
    client = TestClient(app)
    assert client.get("/api/health").json()["status"] == "ok"
    inv = client.get("/api/demo").json()
    inv["name"] = "<script>alert(1)</script>"
    inv["result"] = client.post("/api/analyze", json=inv).json()
    saved = client.post("/api/investigations", json=inv)
    assert saved.status_code == 200
    id = saved.json()["id"]
    assert client.get("/api/investigations/" + id).json()["name"] == inv["name"]
    exported = client.get(f"/api/investigations/{id}/export")
    restored = client.post("/api/investigations/import", json=exported.json())
    assert restored.status_code == 200 and restored.json()["id"] != id
    report = client.get(f"/api/investigations/{id}/report")
    assert "SYNTHETIC DEMONSTRATION" in report.text
    assert "<script>alert(1)</script>" not in report.text
    assert "&lt;script&gt;" in report.text
    assert "Experimental conditional" in report.text and "SHA256" not in report.text
    assert len(client.get("/api/investigations").json()) == 2
    assert client.get("/api/investigations/nonexistent").status_code == 404


def test_upload_limit_and_invalid_schema():
    client = TestClient(app)
    assert (
        client.post("/api/import/csv", json={"csv": "x" * 2_000_001}).status_code == 422
    )
    assert (
        client.post("/api/investigations", json={"area": [1, 0, 0, 1]}).status_code
        == 422
    )
    assert client.post("/api/import/csv", content="x" * 8_000_001).status_code == 413
    assert (
        client.post(
            "/api/investigations/import", json={"plan_history": [{}]}
        ).status_code
        == 422
    )


def test_spreadsheet_injection_and_private_observations():
    inv, _ = synthetic_case()
    inv.measurements[0].sensor_id = '=HYPERLINK("bad")'
    inv.measurements[0].flags = ['=HYPERLINK("bad")']
    rows = list(csv.reader(io.StringIO(measurements_csv(inv))))
    assert rows[1][0].startswith("'=")
    assert rows[1][5].startswith("'=")
    from upwind.models import Observation

    inv.observations = [
        Observation(
            latitude=40.123456,
            longitude=-75.123456,
            timestamp="2025-06-12T10:00Z",
            note="<b>Odor</b>",
        )
    ]
    report = evidence_report(inv)
    assert "40.123456" not in report and "40.12" in report
    assert "&lt;b&gt;Odor&lt;/b&gt;" in report


def test_archived_import_metadata_is_validated():
    client = TestClient(app)
    _, record = parse_csv(ImportRequest(csv=HEADER + "A,2025-06-12T10:00Z,0,0,12\n"))
    malformed = record.model_dump()
    malformed["summary"]["issues"] = "not an issue list"
    assert (
        client.post(
            "/api/investigations/import", json={"imports": [malformed]}
        ).status_code
        == 422
    )
    malformed = record.model_dump()
    malformed["sha256"] = "0" * 64
    assert (
        client.post(
            "/api/investigations/import", json={"imports": [malformed]}
        ).status_code
        == 422
    )
