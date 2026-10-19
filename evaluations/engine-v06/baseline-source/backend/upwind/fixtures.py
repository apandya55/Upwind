"""Simulated data only. Hidden truth is returned separately for evaluation."""

from datetime import datetime, timezone
import csv
import io
import numpy as np
from .models import Investigation, Point, Site, Measurement, Weather, Assumptions
from .engine import plume, projector

CASES = [
    "identifiable",
    "ambiguous",
    "noisy",
    "missing_sensors",
    "background_change",
    "calm",
    "multiple_sources",
    "variable_wind",
]


def synthetic_case(case="identifiable", seed=42):
    if case not in CASES:
        raise ValueError("Unknown synthetic case")
    rng = np.random.default_rng(seed)
    tr = projector(0, 0)

    def point(x, y):
        lon, lat = tr.transform(x, y, direction="INVERSE")
        return dict(latitude=lat, longitude=lon)

    sources = [
        point(x, y)
        for x, y in [
            (-650, 250),
            (-650, -150),
            (-650, 650),
            (-250, 100),
            (-250, -300),
            (-950, 0),
        ]
    ]
    sensors = [(0, 180), (400, 400), (850, -50)]
    if case == "ambiguous":
        sensors = [(0, -600), (400, -700), (850, -650)]
    if case == "missing_sensors":
        sensors = sensors[:1]
    sites = [
        Site(
            id=f"M{i + 1}",
            name=name,
            kind="sensor",
            allowed=True,
            power=True,
            access=True,
            cost=0,
            **point(*xy),
        )
        for i, (name, xy) in enumerate(
            zip(["North monitor", "Garden monitor", "East monitor"], sensors)
        )
    ]
    candidate_xy = [
        (-100, 250),
        (300, 250),
        (700, 250),
        (200, -150),
        (650, -150),
        (0, 650),
        (600, 650),
        (1000, 100),
        (-400, 0),
        (400, -450),
    ]
    for i, xy in enumerate(candidate_xy):
        sites.append(
            Site(
                id=f"C{i + 1}",
                name=[
                    "Footbridge",
                    "Library garden",
                    "East allotments",
                    "Community hall",
                    "South gate",
                    "School field",
                    "North path",
                    "Riverside plot",
                    "West entrance",
                    "Depot boundary",
                ][i],
                cost=[150, 180, 130, 120, 200, 100, 160, 220, 140, 110][i],
                allowed=i != 9,
                power=True,
                access=True,
                **point(*xy),
            )
        )
    readings, weather = [], []
    for t in range(7):
        timestamp = (datetime(2025, 6, 12, 10, t * 5, tzinfo=timezone.utc)).isoformat()
        direction = 270 + (40 * (-1) ** t if case == "variable_wind" else 0)
        speed = 0.2 if case == "calm" else 2.3
        weather.append(
            Weather(
                timestamp=timestamp,
                origin="synthetic",
                wind_speed_m_s=speed,
                wind_from_deg=direction,
                provenance="SYNTHETIC fixed-seed weather; not a forecast",
                **point(200, 150),
            )
        )
        for i, xy in enumerate(sensors):
            # Calm case generated with nominal transport then supplied unsupported met.
            c = 10 + float(plume([xy], [-650, 250], 5000, 2.3, direction)[0])
            if case == "background_change":
                c += t * 3
            if case == "multiple_sources":
                c += float(plume([xy], [-250, -150], 10000, 2.3, direction)[0])
            c += rng.normal(0, 5 if case == "noisy" else 1.5)
            readings.append(
                Measurement(
                    sensor_id=f"M{i + 1}",
                    timestamp=timestamp,
                    origin="synthetic",
                    pm25_ug_m3=max(0, c),
                    **point(*xy),
                )
            )
    inv = Investigation(
        name="Estuary monitoring study",
        concern="SYNTHETIC example: an intermittent particulate increase during a steady westerly wind.",
        objective="Compare permissible sites that help distinguish plausible source locations.",
        synthetic=True,
        area=[-0.012, -0.008, 0.012, 0.009],
        sites=sites,
        measurements=readings,
        weather=weather,
        source_locations=[Point(**p) for p in sources],
        assumptions=Assumptions(
            steady=True,
            open_terrain=True,
            local_weather=True,
            note="Synthetic open-terrain neutral case. All assumptions are constructed, not field verified.",
        ),
        instruments={
            "M1": "Simulated PM2.5 instrument; no calibration applied",
            "M2": "Simulated PM2.5 instrument; no calibration applied",
            "M3": "Simulated PM2.5 instrument; no calibration applied",
        },
    )
    return inv, {
        "source": point(-650, 250),
        "source_index": 0,
        "case": case,
        "seed": seed,
        "strength_ug_s": 5000,
        "background_ug_m3": 10,
    }


def as_csv(rows):
    out = io.StringIO()
    keys = list(rows[0]) if rows else []
    writer = csv.DictWriter(out, fieldnames=keys)
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue()
