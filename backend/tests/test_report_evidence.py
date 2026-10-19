"""Presentation contracts; these do not assert scientific calibration."""

from upwind.fixtures import synthetic_case
from upwind.report import evidence_report


def evidence_result():
    return {
        "status": "ok",
        "model_version": "presentation-contract-fixture",
        "input_hash": "0" * 64,
        "warnings": [],
        "plans": [],
        "sources": [{"id": "S1", "weight": 1.0}],
        "source_probability": 0.4,
        "evidence_status": "ambiguous",
        "source_region90": {
            "level": 0.9,
            "meaning": "Conditional single-source quadrature mass",
            "area_m2": 1200.0,
            "domain_area_m2": 2000.0,
            "resolution_m": 20.0,
            "cells": [
                {
                    "polygon": [{"latitude": 1.23456789, "longitude": 2.34567891}],
                    "weight": 1.0,
                }
            ],
            "support": "Rectangle spanned by domain anchors",
        },
        "rows_loaded": 100,
        "rows_excluded": 5,
        "rows_input": 95,
        "rows_used": 40,
        "selection": {"method": "explicit test selection", "limit": 40, "seed": 7},
        "diagnostics": {
            "held_out_sensor": [],
            "predictive_warning": False,
            "method": "No held-out check available",
        },
    }


def test_report_distinguishes_counts_model_support_and_geographic_meaning():
    inv, _ = synthetic_case()
    inv.result = evidence_result()
    report = evidence_report(inv)
    assert "Source not identified" in report
    assert "0.4000" in report and "0.6000" in report
    assert "100 loaded; 5 excluded; 95 usable; 40 fitted" in report
    assert "nearest-anchor partition weight" in report
    assert "not probability at the marker" in report
    assert "not independently measured geographic coverage" in report
    assert "1.23456789" not in report and "2.34567891" not in report
    assert "No held-out sensor predictive check available" in report


def test_unavailable_sensor_checks_are_escaped_and_not_treated_as_validation():
    inv, _ = synthetic_case()
    inv.result = evidence_result()
    inv.result["diagnostics"]["held_out_sensor"] = [
        {
            "sensor_id": "<script>sensor</script>",
            "rows": 10,
            "unavailable": "<b>unsupported geometry</b>",
            "flagged": False,
        }
    ]
    report = evidence_report(inv)
    assert "No held-out sensor predictive check available" in report
    assert "Check unavailable" in report
    assert "&lt;script&gt;sensor&lt;/script&gt;" in report
    assert "&lt;b&gt;unsupported geometry&lt;/b&gt;" in report
    assert "<script>sensor</script>" not in report


def test_legacy_report_keeps_discrete_weight_meaning():
    inv, _ = synthetic_case()
    inv.result = {
        "status": "ok",
        "warnings": [],
        "plans": [],
        "sources": [{"id": "S1", "weight": 1.0}],
        "rows_used": 40,
    }
    report = evidence_report(inv)
    assert "archived discrete-location conditional model weight" in report
    assert "Separate loaded/excluded counts" in report
    assert "Conditional single-source model weight:" not in report


def test_coverage_only_report_handles_unavailable_reconstruction():
    inv, _ = synthetic_case()
    inv.result = evidence_result()
    inv.result.update(
        {
            "source_probability": None,
            "source_region90": None,
            "diagnostics": None,
            "sources": [],
            "rows_used": 0,
        }
    )
    report = evidence_report(inv)
    assert "No held-out sensor predictive check available" in report
    assert "40 fitted" not in report
