"""Deterministic quality selection, separate from lossless raw import storage."""

from collections import defaultdict
import hashlib
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


def _selection_key(row):
    """Canonical tie order; selection never depends on the import row order."""
    return (
        row.sensor_id,
        row.timestamp,
        row.latitude,
        row.longitude,
        row.pm25_ug_m3,
        -1 if row.uncertainty_ug_m3 is None else row.uncertainty_ug_m3,
        row.origin,
        -1 if row.humidity_percent is None else row.humidity_percent,
        float("-inf") if row.temperature_c is None else row.temperature_c,
        tuple(sorted(row.flags)),
    )


def select_rows(rows, limit=128, seed=0, *, group_key=None):
    """Select quality-screened observations reproducibly without hiding rare peaks.

    Keep every row if the input fits the limit. Otherwise assign one place to
    each sensor, then distribute remaining places in sensor-ID round-robin
    order until the limit is reached, skipping exhausted sensors. Within each
    sensor select, in priority order, the largest absolute departure from that
    sensor's median concentration, first timestamp, last timestamp, minimum
    concentration and maximum concentration. Repeated anchors consume only one
    place. When a quota cannot hold every anchor, the earlier priorities win;
    retaining all anchors is not possible for every sensor at small limits.

    Divide the remaining time-ordered rows into as many equal-count temporal
    strata as there are unfilled places and draw one row from each stratum.
    Each sensor's PCG64 generator is seeded by the declared seed and SHA256 of
    its ID, avoiding Python's process-randomized hash. Return canonical order.
    Thus input permutation changes neither selected rows nor their order, and
    changing the seed affects only the remaining stratified choices. The caller
    must first deduplicate/quarantine sensor-time conflicts with
    ``measurement_quality``; no raw observations are removed from storage.

    This is an explicit bounded approximation, not an unbiased random sample.
    An extreme concentration is an anchor, not proof of an emissions event.
    """
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        raise ValueError("Selection limit must be a positive integer")
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed < 2**32:
        raise ValueError("Selection seed must be an integer between 0 and 2^32-1")
    groups = defaultdict(list)
    for row in rows:
        groups[row.sensor_id if group_key is None else group_key(row)].append(row)
    if len(groups) > limit:
        raise ValueError(
            f"Inference limit {limit} cannot retain all {len(groups)} {'distinct sensors' if group_key is None else 'sensor/window groups'}; "
            "increase the inference limit or split the investigation"
        )
    if len(rows) <= limit:
        return sorted(rows, key=_selection_key)

    keys = sorted(groups)
    quotas = {key: 1 for key in keys}
    left = limit - len(keys)
    while left:
        for key in keys:
            if quotas[key] < len(groups[key]) and left:
                quotas[key] += 1
                left -= 1

    selected = []
    for key in keys:
        ordered = sorted(groups[key], key=_selection_key)
        quota = quotas[key]
        if quota == len(ordered):
            selected.extend(ordered)
            continue
        values = np.asarray([row.pm25_ug_m3 for row in ordered])
        anchors = (
            int(np.argmax(np.abs(values - np.median(values)))),
            0,
            len(ordered) - 1,
            int(np.argmin(values)),
            int(np.argmax(values)),
        )
        chosen = set()
        for index in anchors:
            if len(chosen) == quota:
                break
            chosen.add(index)
        remaining_places = quota - len(chosen)
        if remaining_places:
            remaining = np.asarray(
                [index for index in range(len(ordered)) if index not in chosen]
            )
            digest = hashlib.sha256(key.encode("utf-8")).digest()
            words = np.frombuffer(digest, dtype="<u4").tolist()
            rng = np.random.Generator(
                np.random.PCG64(np.random.SeedSequence([seed, *words]))
            )
            for stratum in np.array_split(remaining, remaining_places):
                chosen.add(int(stratum[rng.integers(len(stratum))]))
        selected.extend(ordered[index] for index in sorted(chosen))
    return sorted(selected, key=_selection_key)
