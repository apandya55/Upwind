"""Focused checks for the read-only National Explorer v3 experiment."""

import zipfile
from io import BytesIO
from pathlib import Path

import numpy as np
import pandas as pd

from scripts.evaluate_national_v3 import (
    _aqs_eligible,
    _predict_prism,
    audit_aqs_year,
    fold_for,
    metrics,
)


def test_v2_fold_identity_is_stable_and_bounded():
    assert fold_for(35.2, -78.7) == fold_for(35.9, -78.1)
    assert 0 <= fold_for(64.8, -147.7) < 5


def test_aqs_filter_keeps_only_declared_target_rows():
    frame = pd.DataFrame(
        [
            {"Parameter Code": 88101, "Pollutant Standard": "PM25 Annual 2024", "Metric Used": "Quarterly Means of Daily Means", "Units of Measure": "Micrograms/cubic meter (LC)", "Completeness Indicator": "Y", "Year": 2024},
            {"Parameter Code": 88101, "Pollutant Standard": "PM25 Annual 2024", "Metric Used": "Daily Mean", "Units of Measure": "Micrograms/cubic meter (LC)", "Completeness Indicator": "Y", "Year": 2024},
            {"Parameter Code": 88502, "Pollutant Standard": "PM25 Annual 2024", "Metric Used": "Quarterly Means of Daily Means", "Units of Measure": "Micrograms/cubic meter (LC)", "Completeness Indicator": "Y", "Year": 2024},
        ]
    )
    assert len(_aqs_eligible(frame, 2024)) == 1


def test_environmental_transform_is_fit_on_training_rows_only():
    train_x = np.array([[35.0, -80.0], [36.0, -81.0], [37.0, -82.0]])
    train_y = np.array([5.0, 7.0, 9.0])
    test_x = np.array([[38.0, -83.0]])
    pred_a = _predict_prism(train_x, train_y, np.array([0.0, 1.0, 2.0]), test_x, np.array([1.0]))
    pred_b = _predict_prism(train_x, train_y, np.array([0.0, 1.0, 2.0]), test_x, np.array([100.0]))
    assert np.isfinite(pred_a).all() and np.isfinite(pred_b).all()
    assert pred_a.shape == (1,)
    assert np.isclose(pred_a[0], 7.0, atol=1e-6)
    assert np.isclose(pred_b[0], 205.0, atol=1e-6)
    assert abs(pred_b[0] - pred_a[0]) > 100.0


def test_metrics_uses_supplied_training_reference():
    got = metrics(np.array([0.0, 10.0]), np.array([1.0, 9.0]), np.array([4.0, 4.0]))
    assert got["r2_vs_training_mean"] == 1 - 2 / 52


def test_aqs_audit_compares_legacy_event_averaging_with_ambient_selection(tmp_path: Path):
    frame = pd.DataFrame(
        [
            {"State Code": 1, "County Code": 1, "Site Num": 1, "Parameter Code": 88101, "POC": 1, "Event Type": "No Events", "Pollutant Standard": "PM25 Annual 1997", "Metric Used": "Quarterly Means of Daily Means", "Units of Measure": "Micrograms/cubic meter (LC)", "Completeness Indicator": "Y", "Year": 2024, "Certification Indicator": "Certified", "Observation Percent": 95, "Arithmetic Mean": 6.0},
            {"State Code": 1, "County Code": 1, "Site Num": 1, "Parameter Code": 88101, "POC": 1, "Event Type": "No Events", "Pollutant Standard": "PM25 Annual 2024", "Metric Used": "Quarterly Means of Daily Means", "Units of Measure": "Micrograms/cubic meter (LC)", "Completeness Indicator": "Y", "Year": 2024, "Certification Indicator": "Certified", "Observation Percent": 95, "Arithmetic Mean": 6.0},
            {"State Code": 1, "County Code": 3, "Site Num": 2, "Parameter Code": 88101, "POC": 1, "Event Type": "Events Excluded", "Pollutant Standard": "PM25 Annual 2024", "Metric Used": "Quarterly Means of Daily Means", "Units of Measure": "Micrograms/cubic meter (LC)", "Completeness Indicator": "Y", "Year": 2024, "Certification Indicator": "Certified", "Observation Percent": 90, "Arithmetic Mean": 5.0},
            {"State Code": 1, "County Code": 3, "Site Num": 2, "Parameter Code": 88101, "POC": 2, "Event Type": "Events Included", "Pollutant Standard": "PM25 Annual 2024", "Metric Used": "Quarterly Means of Daily Means", "Units of Measure": "Micrograms/cubic meter (LC)", "Completeness Indicator": "Y", "Year": 2024, "Certification Indicator": "Requested but not yet concurred", "Observation Percent": 80, "Arithmetic Mean": 7.0},
        ]
    )
    stream = BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("annual.csv", frame.to_csv(index=False))
    path = tmp_path / "aqs.zip"
    path.write_bytes(stream.getvalue())
    audit = audit_aqs_year(path, 2024)
    assert audit["unique_physical_site_years"] == 2
    assert audit["duplicate_poc_event_groups"] == 1
    assert audit["rows_after_newest_standard_poc_event_deduplication"] == 3
    selection = audit["event_selection_audit"]
    assert selection["legacy_sites_falling_back_to_event_rows"] == 1
    assert selection["legacy_fallback_sites_with_multiple_event_treatments_averaged"] == 1
    assert selection["ambient_policy_selected_poc_rows"] == 2
    assert selection["ambient_policy_event_treatment_counts"] == {
        "Events Included": 1,
        "No Events": 1,
    }
    assert selection["pocs_with_only_event_excluded_summaries"] == 1
    assert selection["site_years_with_changed_mean_vs_legacy"] == 1
