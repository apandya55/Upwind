"""Check fresh stress controls/truth separation; no test calls inference."""

import importlib.util
import json
from pathlib import Path

import pytest

from upwind.validation import weather_bias as wb

SPEC = importlib.util.spec_from_file_location(
    "severe_stress", Path(__file__).resolve().parents[2] / "scripts/severe_stress.py"
)
HARNESS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HARNESS)


def test_generation_is_reproducible_and_restores_existing_tables():
    old_layout = json.dumps(wb.LAYOUTS)
    old_angles = json.dumps(wb.ANGLES)
    first, truth = HARNESS.case("characterized_nominal", 6101000)
    second, again = HARNESS.case("characterized_nominal", 6101000)
    other, other_truth = HARNESS.case("characterized_nominal", 6101001)
    assert first.model_dump() == second.model_dump() and truth == again
    assert truth["monitor_xy"] != other_truth["monitor_xy"]
    assert first.model_dump() != other.model_dump()
    assert json.dumps(wb.LAYOUTS) == old_layout and json.dumps(wb.ANGLES) == old_angles
    assert first.synthetic and all(m.origin == "synthetic" for m in first.measurements)
    assert "private_evaluator_truth" not in first.model_dump()


def test_sensor_mutations_preserve_truth_and_unaffected_records():
    base, truth = HARNESS.case("characterized_nominal", 6101000)
    dropped, dropped_truth = HARNESS.case("sensor_dropout", 6101000)
    assert {m.sensor_id for m in dropped.measurements} == {"M01", "M03", "M05"}
    assert len(dropped.measurements) == 48
    assert dropped_truth["source_xy"] == truth["source_xy"]
    biased, changed_truth = HARNESS.case("sensor_bias", 6101000)
    bias = changed_truth["mutation"]["additive_bias_ug_m3"]
    for left, right in zip(base.measurements, biased.measurements):
        assert right.pm25_ug_m3 - left.pm25_ug_m3 == pytest.approx(
            bias if left.sensor_id == "M00" else 0
        )
    assert changed_truth["source_xy"] == truth["source_xy"]


def test_shared_bias_is_shared_but_lineage_test_does_not_fake_independence():
    base, _ = HARNESS.case("characterized_nominal", 6101000)
    hidden, truth = HARNESS.case("shared_reference_bias", 6101000)
    for first, second in zip(base.weather, hidden.weather):
        assert (second.wind_from_deg - first.wind_from_deg) % 360 == pytest.approx(
            truth["mutation"]["hidden_common_bias_deg"]
        )
    related, _ = HARNESS.case("shared_lineage", 6101000)
    assert {w.upstream_id for w in related.weather} == {"instrument-A"}


def test_extreme_rows_remain_raw_and_flagged():
    inv, _ = HARNESS.case("extreme_readings", 6101000)
    rows = [m for m in inv.measurements if m.sensor_id == "M00"]
    assert len(rows) == 16
    assert all(m.pm25_ug_m3 == 650 and "extreme_review" in m.flags for m in rows)
    assert all(m.origin == "synthetic" for m in rows)


def test_fixed_outside_domain_is_not_chosen_using_truth():
    first, a = HARNESS.case("source_outside_domain", 6101000)
    second, b = HARNESS.case("source_outside_domain", 6101001)
    assert first.source_locations == second.source_locations
    assert a["source_xy"][0] > -500 and b["source_xy"][0] > -500
    assert a["mutation"]["declared_source_rectangle_xy_m"] == [-680, -220, -500, 220]


def test_fresh_seeds_and_declared_denominators():
    assert len(HARNESS.SEEDS) == 48 and len(HARNESS.FAMILIES) == 20
    assert all(seed not in wb.SPLITS["final"] for seed in HARNESS.SEEDS)
    assert (
        sum(len(HARNESS.SEEDS[i::4]) for i in range(4)) * len(HARNESS.FAMILIES) == 960
    )
    with pytest.raises(ValueError):
        HARNESS.case("invented-condition", 6101000)
