"""Synthetic test case generator and reference fixtures."""

import math
from datetime import datetime, timezone
import numpy as np
from ..models import (
    Investigation,
    Point,
    Site,
    Measurement,
    Weather,
    Assumptions,
    Settings,
)
from ..numerics import projector

CASES = [
    "weak_signal",
    "strong_signal",
    "ambiguous",
    "high_noise",
    "background_shift",
    "changing_background",
    "two_sources",
    "off_grid",
    "direction_bias",
    "speed_bias",
    "clustered",
    "missing_sensor",
    "calm",
    "variable",
    "missing_weather",
    "insufficient_sensors",
]
GRID = [
    (-180, 0),
    (-180, -80),
    (-180, 80),
    (-280, 0),
    (-280, -80),
    (-280, 80),
    (-80, -80),
    (-80, 80),
    (0, 180),
]
CANDIDATES = [
    (-120, 30),
    (-120, -30),
    (-70, 0),
    (10, 0),
    (100, 0),
    (-60, 60),
    (-60, -60),
    (0, 120),
    (180, -100),
    (250, 120),
    (100, 150),
    (-120, 140),
]


def scalar_plume(point, source, q, speed, direction):
    """Plain-math oracle: intentionally does not call the implementation kernel."""
    dx, dy = point[0] - source[0], point[1] - source[1]
    radians = math.radians(direction % 360)
    down = -dx * math.sin(radians) - dy * math.cos(radians)
    across = dx * math.cos(radians) - dy * math.sin(radians)
    if down < 20 or math.hypot(dx, dy) > 3000:
        return 0.0
    lateral = 0.08 * down / math.sqrt(1 + 0.0001 * down)
    vertical = 0.06 * down / math.sqrt(1 + 0.0015 * down)
    return (
        q
        / (2 * math.pi * speed * lateral * vertical)
        * math.exp(-(across**2) / (2 * lateral**2))
        * (
            math.exp(-((2 - 5) ** 2) / (2 * vertical**2))
            + math.exp(-((2 + 5) ** 2) / (2 * vertical**2))
        )
    )


def point(xy):
    lon, lat = projector(0, 0).transform(*xy, direction="INVERSE")
    return {"latitude": lat, "longitude": lon}


def make_case(case, seed, planning=False):
    if case not in CASES:
        raise ValueError(case)
    rng = np.random.default_rng(seed)
    source = GRID[0] if case != "off_grid" else (-210, 40)
    xy = [(-100, 0), (-20, 10), (80, -10), (180, 30)]
    if planning:
        xy = [(-20, -70), (100, 80)]
    if case == "weak_signal":
        xy = (
            [(450, -200), (650, 200), (900, -150), (1100, 300)]
            if not planning
            else [(450, -200), (650, 200)]
        )
    if case == "ambiguous":
        xy = [(-450, -300), (-450, 0), (-450, 300)]
    if case == "clustered":
        xy = [(-80, 5), (-78, 5), (-76, 5), (-74, 5)]
    if case == "missing_sensor":
        xy = xy[:2]
    if case == "insufficient_sensors":
        xy = xy[:1]
    q = 1500.0 if case == "weak_signal" else 12000.0
    bg = 18.0 if case == "background_shift" else 10.0
    speed = 2.3 * 1.15  # 15% speed perturbation for wind sensitivity check
    direction = 310.0 if case == "direction_bias" else 270.0
    if case == "speed_bias":
        speed = 4.6
    noise = 4.0 if case == "high_noise" else 1.0
    times = [
        datetime(2025, 7, 1, 10, t * 5, tzinfo=timezone.utc).isoformat()
        for t in range(3)
    ]
    # Matched observational errors: independent measurement + shared instrument
    # bias + spatially correlated, temporally shared model discrepancy.
    points = np.asarray(xy)
    distance = np.linalg.norm(points[:, None, :] - points[None, :, :], axis=-1)
    spatial = rng.multivariate_normal(np.zeros(len(xy)), np.exp(-distance / 150))
    instrument = rng.normal(0, 1, len(xy))
    readings = []
    for t, stamp in enumerate(times):
        for i, p in enumerate(xy):
            concentration = bg + scalar_plume(p, source, q, speed, direction)
            if case == "two_sources":
                concentration += scalar_plume(p, (-180, 30), 30000.0, speed, 270.0)
            if case == "changing_background":
                concentration += t * 8
            value = concentration + spatial[i] + instrument[i] + rng.normal(0, noise)
            readings.append(
                Measurement(
                    sensor_id=f"M{i}",
                    timestamp=stamp,
                    pm25_ug_m3=max(value, 0),
                    uncertainty_ug_m3=noise,
                    origin="synthetic",
                    **point(p),
                )
            )
    sites = [
        Site(id=f"M{i}", name=f"Synthetic monitor {i}", kind="sensor", **point(p))
        for i, p in enumerate(xy)
    ]
    candidates = (
        [(x + 700, y + 400) for x, y in CANDIDATES]
        if case == "weak_signal" and planning
        else CANDIDATES
    )
    for i, p in enumerate(candidates):
        sites.append(
            Site(
                id=f"C{i:02}",
                name=f"Synthetic permissible candidate {i}",
                allowed=True,
                power=True,
                access=True,
                cost=[100, 110, 120, 90, 100, 140, 130, 180, 160, 150, 140, 170][i],
                **point(p),
            )
        )
    weather = [
        Weather(
            timestamp=t,
            wind_speed_m_s=0.2 if case == "calm" else 2.3,
            wind_from_deg=(230 if j % 2 else 310) if case == "variable" else 270,
            origin="synthetic",
            provenance="Synthetic observed wind; true transport includes declared uncertainty",
            **point((0, 0)),
        )
        for j, t in enumerate(times)
    ]
    if case == "missing_weather":
        weather = []
    inv = Investigation(
        name=f"SYNTHETIC stress {case} {seed}",
        synthetic=True,
        area=[-0.012, -0.008, 0.012, 0.009],
        measurements=readings,
        weather=weather,
        sites=sites,
        source_locations=[Point(**point(p)) for p in GRID],
        assumptions=Assumptions(
            steady=True,
            open_terrain=True,
            local_weather=True,
            note="Constructed evaluation assumptions, not field verification",
        ),
        settings=Settings(noise_ug_m3=1, budget=250, equipment_limit=2, seed=seed),
    )
    truth = {
        "source_xy": source,
        "source_index": 0 if case != "off_grid" else None,
        "strength": q,
        "background": bg,
        "speed": speed,
        "direction": direction,
        "case": case,
        "seed": seed,
        "measurement_noise": noise,
        "candidate_xy": candidates,
        "initial_xy": xy,
        "initial_spatial_error": spatial,
    }
    return inv, truth


def predict_truth(points, truth):
    return np.array(
        [
            truth["background"]
            + scalar_plume(
                p,
                truth["source_xy"],
                truth["strength"],
                truth["speed"],
                truth["direction"],
            )
            for p in points
        ]
    )
