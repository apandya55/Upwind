from datetime import datetime, timedelta, timezone

import numpy as np
import pytest

from upwind.models import Measurement, Settings
from upwind.quality import select_rows


def observations(sensor, count, *, pulse=None):
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return [
        Measurement(
            sensor_id=sensor,
            timestamp=(start + timedelta(seconds=index)).isoformat(),
            latitude=40,
            longitude=-75,
            pm25_ug_m3=400 if index == pulse else 10 + (index % 7) / 10,
        )
        for index in range(count)
    ]


def identities(rows):
    return [(row.sensor_id, row.timestamp) for row in rows]


def test_all_usable_rows_retained_when_within_limit():
    rows = observations("A", 12) + observations("B", 14)
    selected = select_rows(list(reversed(rows)), limit=40, seed=173)
    assert identities(selected) == sorted(identities(rows))
    assert len(selected) == len(rows)
    assert select_rows([], limit=40) == []


def test_selection_retains_interior_rare_pulse_and_temporal_extremes():
    # Rank-quantile sampling at 40 rows would miss this brief interior pulse.
    rows = observations("A", 1000, pulse=437)
    selected = select_rows(rows, limit=40, seed=19)
    ids = identities(selected)
    assert set(identities([rows[437], rows[0], rows[-1]])).issubset(ids)
    assert min(row.pm25_ug_m3 for row in selected) == min(
        row.pm25_ug_m3 for row in rows
    )
    assert max(row.pm25_ug_m3 for row in selected) == 400
    assert len(ids) == len(set(ids)) == 40


def test_selection_is_permutation_invariant_and_seed_controls_remaining_choices():
    rows = observations("A", 300, pulse=137) + observations("B", 280, pulse=241)
    chosen = select_rows(rows, limit=80, seed=981)
    shuffled = list(rows)
    np.random.default_rng(741).shuffle(shuffled)
    assert identities(chosen) == identities(select_rows(shuffled, limit=80, seed=981))
    assert identities(chosen) != identities(select_rows(rows, limit=80, seed=982))
    for selected in [chosen, select_rows(rows, limit=80, seed=982)]:
        assert len(identities(selected)) == len(set(identities(selected))) == 80
        assert {row.sensor_id for row in selected} == {"A", "B"}
        assert sum(row.pm25_ug_m3 == 400 for row in selected) == 2


def test_balanced_quotas_keep_sparse_sensors_and_no_sensor_over_quota():
    rows = (
        observations("A", 500)
        + observations("B", 1)
        + observations("C", 2)
        + observations("D", 500)
    )
    selected = select_rows(rows, limit=40)
    counts = {
        sensor: sum(row.sensor_id == sensor for row in selected)
        for sensor in ["A", "B", "C", "D"]
    }
    assert counts == {"A": 19, "B": 1, "C": 2, "D": 18}
    assert len(identities(selected)) == len(set(identities(selected))) == 40


def test_minimum_sensor_quota_keeps_rare_departure_when_only_one_fits():
    rows = [
        row
        for sensor in range(40)
        for row in observations(f"S{sensor:02}", 9, pulse=4)
    ]
    selected = select_rows(rows, limit=40)
    assert len({row.sensor_id for row in selected}) == 40
    assert all(row.pm25_ug_m3 == 400 for row in selected)
    with pytest.raises(ValueError, match="cannot retain all 40 distinct sensors"):
        select_rows(rows, limit=39)


@pytest.mark.parametrize("limit", [0, -1, 40.0, True])
def test_invalid_selection_limits_refused(limit):
    with pytest.raises(ValueError, match="positive integer"):
        select_rows([], limit=limit)


@pytest.mark.parametrize("seed", [-1, 2**32, 1.5, True])
def test_invalid_selection_seeds_refused(seed):
    with pytest.raises(ValueError, match="Selection seed"):
        select_rows([], seed=seed)


def test_settings_expose_bounded_inference_and_independent_selection_seed():
    defaults = Settings()
    assert defaults.inference_limit == 128
    assert defaults.selection_seed == 0
    assert Settings(inference_limit=512, selection_seed=2**32 - 1).seed == 42
    for value in [39, 513, True, 128.0]:
        with pytest.raises(ValueError):
            Settings(inference_limit=value)
    for value in [-1, 2**32, True, "3"]:
        with pytest.raises(ValueError):
            Settings(selection_seed=value)
