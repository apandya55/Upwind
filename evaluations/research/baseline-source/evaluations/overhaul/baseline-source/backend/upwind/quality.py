"""Deterministic quality selection, separate from lossless raw import storage."""

from collections import defaultdict
import numpy as np


def measurement_quality(inv):
    groups = defaultdict(list)
    excluded = 0
    for m in inv.measurements:
        if (
            m.pm25_ug_m3 < 0
            or m.pm25_ug_m3 > 500
            or {"negative", "extreme_review"}.intersection(m.flags)
        ):
            excluded += 1
        else:
            groups[m.sensor_id, m.timestamp].append(m)
    usable, conflicts, duplicates = [], [], 0
    for key, rows in sorted(groups.items()):
        signatures = {
            (r.pm25_ug_m3, r.latitude, r.longitude, r.uncertainty_ug_m3, r.origin)
            for r in rows
        }
        if len(signatures) > 1:
            conflicts.append(
                {"sensor_id": key[0], "timestamp": key[1], "rows": len(rows)}
            )
            excluded += len(rows)
        else:
            usable.append(rows[0])
            duplicates += len(rows) - 1
    return usable, {
        "input_rows": len(inv.measurements),
        "usable_unique_rows": len(usable),
        "excluded_rows": excluded,
        "identical_duplicates": duplicates,
        "conflicting_keys": conflicts,
    }


def balanced_rows(rows, limit=40):
    groups = defaultdict(list)
    for row in rows:
        groups[row.sensor_id].append(row)
    if len(groups) > limit:
        raise ValueError(
            f"Reconstruction supports at most {limit} distinct sensors per window; split the investigation"
        )
    if len(rows) <= limit:
        return sorted(
            rows, key=lambda m: (m.sensor_id, m.timestamp, m.latitude, m.longitude)
        )
    # Round-robin quantile quotas retain every sensor, independent of input order.
    keys = sorted(groups)
    quotas = {k: 1 for k in keys}
    left = limit - len(keys)
    while left:
        changed = False
        for k in keys:
            if quotas[k] < len(groups[k]) and left:
                quotas[k] += 1
                left -= 1
                changed = True
        if not changed:
            break
    selected = []
    for k in keys:
        ordered = sorted(groups[k], key=lambda m: m.timestamp)
        selected.extend(
            ordered[i] for i in np.linspace(0, len(ordered) - 1, quotas[k], dtype=int)
        )
    return selected
