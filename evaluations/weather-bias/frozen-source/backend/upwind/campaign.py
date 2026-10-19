"""Explicit, non-overlapping, individually steady observation windows.

No automatic splitting of unsupported variable weather and no future weather
substitution. Regional backgrounds vary by window; instrument bias persists.
"""

from datetime import datetime
import numpy as np
from .weather import matched_weather


def assignment(inv, timestamps):
    windows = sorted(inv.study_windows, key=lambda w: w.start)
    values = np.array([datetime.fromisoformat(t).timestamp() for t in timestamps])
    if not windows:
        return np.zeros(len(values), dtype=int), None
    indices = np.full(len(values), -1, dtype=int)
    centered = np.zeros(len(values))
    for i, w in enumerate(windows):
        start, end = (datetime.fromisoformat(t).timestamp() for t in (w.start, w.end))
        inside = (values >= start) & (values <= end)
        indices[inside] = i
        centered[inside] = values[inside] - (start + end) / 2
    if np.any(indices < 0):
        raise ValueError(
            "Every usable reading or predictive timestamp must belong to an explicit campaign window"
        )
    return indices, centered


def observed_weather(inv, rows, projection, *, require_sensors=True):
    if not inv.study_windows:
        return matched_weather(inv, rows, projection)
    if not inv.assumptions.constant_release_across_windows:
        raise ValueError(
            "Confirm a fixed source location and constant release across campaign windows; varying release is outside this shared-strength model"
        )
    labels, _ = assignment(inv, [r.timestamp for r in rows])
    windows = sorted(inv.study_windows, key=lambda w: w.start)
    matched = [None] * len(rows)
    last_wind, last_speed = None, None
    for i, w in enumerate(windows):
        indices = np.flatnonzero(labels == i)
        if not len(indices):
            continue  # Defined but unobserved windows retain their prior background.
        period = inv.model_copy(
            update={
                "weather": [m for m in inv.weather if w.start <= m.timestamp <= w.end]
            }
        )
        selected = [rows[j] for j in indices]
        if require_sensors and len({r.sensor_id for r in selected}) < 2:
            raise ValueError(
                "Each observed campaign window requires at least two usable sensors"
            )
        weather, last_wind, last_speed = matched_weather(period, selected, projection)
        for j, m in zip(indices, weather):
            matched[j] = m
    return matched, last_wind, last_speed
