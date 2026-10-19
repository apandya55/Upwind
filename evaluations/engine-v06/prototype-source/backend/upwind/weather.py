"""Bounded vectorized local weather matching and full-window capability checks."""

from datetime import datetime
import numpy as np
from .numerics import projector


def micros(value):
    d = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return (
        d.toordinal() * 86400 + d.hour * 3600 + d.minute * 60 + d.second
    ) * 1_000_000 + d.microsecond


def matched_weather(inv, rows, tr=None):
    if not rows:
        raise ValueError("No usable measurements")
    primary = [w for w in inv.weather if w.role == "primary"]
    if not primary:
        raise ValueError(
            "Local meteorology is missing. Import wind data or use spatial coverage planning."
        )
    times = np.array([micros(m.timestamp) for m in rows], dtype=np.int64)
    if times.max() - times.min() > 3_600_000_000:
        raise ValueError(
            "Select a single steady period of at most one hour for reconstruction."
        )
    tr = tr or projector(rows[0].latitude, rows[0].longitude)
    # Canonical order and conflict detection make ties independent of CSV order.
    unique = {}
    for w in primary:
        key = (w.timestamp, w.latitude, w.longitude)
        if key in unique and any(
            getattr(w, f) != getattr(unique[key], f)
            for f in ("wind_speed_m_s", "wind_from_deg", "source_id", "upstream_id")
        ):
            raise ValueError("Conflicting duplicate meteorology records")
        unique[key] = w
    met = sorted(
        unique.values(),
        key=lambda w: (
            w.timestamp,
            w.latitude,
            w.longitude,
            w.wind_speed_m_s,
            w.wind_from_deg,
        ),
    )
    wt = np.array([micros(w.timestamp) for w in met], dtype=np.int64)
    wx, wy = tr.transform([w.longitude for w in met], [w.latitude for w in met])
    rx, ry = tr.transform([m.longitude for m in rows], [m.latitude for m in rows])
    wx, wy, rx, ry = map(np.asarray, (wx, wy, rx, ry))
    chosen = []
    local = np.zeros(len(met), dtype=bool)
    for start in range(0, len(rows), 128):
        xx, yy = rx[start : start + 128, None], ry[start : start + 128, None]
        distance = np.hypot(xx - wx[None, :], yy - wy[None, :])
        dt = np.abs(times[start : start + 128, None] - wt[None, :])
        nearby = distance <= 3000
        local |= nearby.any(axis=0)
        valid = nearby & (dt <= 1_800_000_000)
        if not valid.any(axis=1).all():
            raise ValueError(
                "No weather within 30 minutes and 3 km of every retained measurement."
            )
        rank = np.where(valid, dt, np.iinfo(np.int64).max)
        minimum = rank.min(axis=1)
        index = np.argmin(
            np.where(valid & (dt == minimum[:, None]), distance, np.inf), axis=1
        )
        chosen.extend(index.tolist())
    # Validate *all* relevant local in-window wind, including unmatched records.
    relevant = local & (wt >= times.min()) & (wt <= times.max())
    relevant[chosen] = True
    indices = np.flatnonzero(relevant)
    directions = np.array([met[i].wind_from_deg for i in indices])
    speeds = np.array([met[i].wind_speed_m_s for i in indices])
    mean = (
        float(np.rad2deg(np.angle(np.mean(np.exp(1j * np.deg2rad(directions)))))) % 360
    )
    spread = float(np.max(np.abs((directions - mean + 180) % 360 - 180)))
    if speeds.min() < 0.8 or speeds.max() > 8:
        raise ValueError(
            "Calm (<0.8 m/s) or strong (>8 m/s) winds are unsupported by this approximation."
        )
    if spread > 25 or speeds.max() / speeds.min() > 2:
        raise ValueError(
            "Weather is too variable for a steady plume (direction deviation >25° or speed ratio >2)."
        )
    return [met[i] for i in chosen], mean, float(np.median(speeds))
