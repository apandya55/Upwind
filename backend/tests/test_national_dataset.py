"""Focused checks for national monitor source selection."""

import zipfile
import json
from pathlib import Path

from scripts import build_national_dataset as dataset

process_aqs = dataset.process_aqs


def _aqs_row(site: int, poc: int, event: str, value: float) -> dict:
    return {
        "State Code": 37,
        "County Code": 183,
        "Site Num": site,
        "Parameter Code": 88101,
        "POC": poc,
        "Latitude": 35.8,
        "Longitude": -78.6,
        "Pollutant Standard": "PM25 Annual 2024",
        "Metric Used": "Quarterly Means of Daily Means",
        "Year": 2024,
        "Units of Measure": "Micrograms/cubic meter (LC)",
        "Event Type": event,
        "Observation Percent": 95,
        "Completeness Indicator": "Y",
        "Certification Indicator": "Certified",
        "Arithmetic Mean": value,
    }


def test_aqs_uses_one_ambient_event_summary_per_poc(tmp_path: Path):
    rows = [
        _aqs_row(1, 1, "Events Included", 8.0),
        _aqs_row(1, 1, "Events Excluded", 2.0),
        _aqs_row(1, 1, "Concurred Events Excluded", 3.0),
        _aqs_row(1, 2, "No Events", 4.0),
        # POC 3 has only policy-adjusted values and must not replace observed
        # ambient concentration with an event-excluded annual summary.
        _aqs_row(1, 3, "Concurred Events Excluded", 1.0),
    ]
    archive_path = tmp_path / "aqs.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        import pandas as pd

        archive.writestr("annual.csv", pd.DataFrame(rows).to_csv(index=False))

    records, audit = process_aqs({2024: archive_path})

    assert len(records) == 1
    site = records[0]
    assert site["pm25_ug_m3"] == 6.0
    assert site["poc_count"] == 2
    assert site["poc_ids"] == ["1", "2"]
    assert site["event_treatment"] == "Mixed selected treatments by POC"
    assert site["poc_event_treatments"] == [
        {
            "poc_id": "1",
            "event_treatment": "Events Included",
            "certification": "Certified",
            "observation_percent": 95.0,
            "pollutant_standard": "PM25 Annual 2024",
            "arithmetic_mean_ug_m3": 8.0,
            "source_row_number": 2,
        },
        {
            "poc_id": "2",
            "event_treatment": "No Events",
            "certification": "Certified",
            "observation_percent": 95.0,
            "pollutant_standard": "PM25 Annual 2024",
            "arithmetic_mean_ug_m3": 4.0,
            "source_row_number": 5,
        },
    ]
    assert site["source_provenance"]["archive_name"] == "aqs.zip"
    assert site["source_provenance"]["csv_member"] == "annual.csv"
    assert len(site["source_provenance"]["archive_sha256"]) == 64
    assert site["source_provenance"]["selected_source_rows"] == [2, 5]
    observation = site["canonical_observation"]
    assert observation["schema"] == "upwind-canonical-observation-1"
    assert observation["provider"] == "U.S. EPA Air Quality System (AQS)"
    assert observation["provider_observation_type"] == "annual monitor summary"
    assert observation["station"]["provider_station_id"] == site["id"]
    assert observation["observation_period"] == {
        "start": "2024-01-01", "end_exclusive": "2025-01-01",
        "timezone": "UTC", "resolution": "annual",
    }
    assert observation["measurement"]["value"] == site["pm25_ug_m3"]
    assert observation["measurement"]["units"] == "µg/m³"
    assert observation["quality"]["poc_treatments"] == site["poc_event_treatments"]
    assert observation["provenance"] == site["source_provenance"]
    assert audit["2024"]["event_treatment_selection"]["selected_poc_rows_by_treatment"] == {
        "Events Included": 1,
        "No Events": 1,
    }
    assert audit["2024"]["event_treatment_selection"]["pocs_with_only_event_excluded_summaries"] == 1


def test_aqs_withholds_site_when_all_pocs_only_have_excluded_event_summaries(tmp_path: Path):
    archive_path = tmp_path / "aqs.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        import pandas as pd

        archive.writestr(
            "annual.csv",
            pd.DataFrame([_aqs_row(2, 1, "Events Excluded", 5.0)]).to_csv(index=False),
        )

    records, audit = process_aqs({2024: archive_path})

    assert records == []
    assert audit["2024"]["event_treatment_selection"]["pocs_with_only_event_excluded_summaries"] == 1
    assert audit["2024"]["event_treatment_selection"]["site_years_without_ambient_poc"] == 1


def test_aqs_source_row_lineage_tracks_original_csv_rows_after_selection(tmp_path: Path):
    rows = [
        _aqs_row(3, 1, "Events Excluded", 1.0),
        _aqs_row(3, 1, "Events Included", 8.0),
        _aqs_row(3, 2, "No Events", 6.0),
    ]
    archive_path = tmp_path / "annual_conc_by_monitor_2024.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        import pandas as pd

        archive.writestr("annual.csv", pd.DataFrame(rows).to_csv(index=False))

    records, _ = process_aqs({2024: archive_path})

    selected = records[0]
    assert selected["poc_event_treatments"][0]["source_row_number"] == 3
    assert selected["poc_event_treatments"][1]["source_row_number"] == 4
    assert selected["source_provenance"]["selected_source_rows"] == [3, 4]


def test_initial_national_manifest_uses_current_explorer_release_id(monkeypatch, tmp_path: Path):
    def fake_download(_url, target, *, archive=False):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"test source")
        return "a" * 64

    monkeypatch.setattr(dataset, "download", fake_download)
    monkeypatch.setattr(
        dataset,
        "process_aqs",
        lambda _aqs: ([{"id": "test-monitor", "year": 2024, "latitude": 35.8, "longitude": -78.6}],
                     {"2024": {"unique_spatial_site_years": 100}}),
    )
    monkeypatch.setattr(
        dataset,
        "process_places",
        lambda *_args: ([{"latitude": 35.9, "longitude": -78.7}], {}),
    )
    raw_dir, release_dir = tmp_path / "raw", tmp_path / "release"
    monkeypatch.setattr(
        "sys.argv",
        ["build_national_dataset.py", "--start-year", "2024", "--end-year", "2024",
         "--no-nei", "--raw-dir", str(raw_dir), "--release-dir", str(release_dir)],
    )

    dataset.main()

    manifest = json.loads((release_dir / "manifest.json").read_text())
    assert manifest["release"] == "upwind-national-explorer-0.3.0"
    assert manifest["status"] == "data_built_model_pending"
