"""Illustrative synthetic campaign only; not a benchmark or field dataset."""

from datetime import datetime, timedelta, timezone
import numpy as np
from .models import (
    Investigation,
    Point,
    Site,
    Measurement,
    Weather,
    Settings,
    Assumptions,
    StudyWindow,
)
from .numerics import projector, plume


def synthetic_campaign(seed=42):
    rng = np.random.default_rng(seed)
    tr = projector(0, 0)

    def point(xy):
        lon, lat = tr.transform(*xy, direction="INVERSE")
        return {"latitude": lat, "longitude": lon}

    sensors = [(40, -120), (40, 0), (40, 120), (260, -90), (260, 90), (600, 0)]
    candidates = [
        (x, y) for x in (20.0, 150.0, 330.0, 560.0) for y in (-110.0, 0.0, 110.0)
    ]
    sites = [
        Site(
            id=f"M{i:02}", name=f"Synthetic monitor {i + 1}", kind="sensor", **point(p)
        )
        for i, p in enumerate(sensors)
    ]
    sites += [
        Site(
            id=f"C{i:02}",
            name=f"Synthetic permissible site {i + 1}",
            allowed=True,
            power=True,
            access=True,
            cost=100.0,
            **point(p),
        )
        for i, p in enumerate(candidates)
    ]
    rows = []
    weather = []
    windows = []
    start = datetime(2026, 6, 2, 9, tzinfo=timezone.utc)
    bias = rng.normal(0, 0.7, len(sensors))
    for w, angle in enumerate((235.0, 260.0, 285.0, 310.0)):
        first = start + timedelta(hours=2 * w)
        last = first + timedelta(minutes=15)
        windows.append(
            StudyWindow(
                id=f"period-{w + 1}", start=first.isoformat(), end=last.isoformat()
            )
        )
        for t in range(4):
            stamp = (first + timedelta(minutes=5 * t)).isoformat()
            weather.append(
                Weather(
                    timestamp=stamp,
                    wind_speed_m_s=2.3,
                    wind_from_deg=angle,
                    origin="synthetic",
                    provenance="Simulated observed wind, not a forecast",
                    **point((150, 0)),
                )
            )
            for j, p in enumerate(sensors):
                value = (
                    12
                    + w * 0.5
                    + float(plume([p], [-265, 30], 24000, 2.3, angle)[0])
                    + bias[j]
                    + rng.normal(0, 1)
                )
                rows.append(
                    Measurement(
                        sensor_id=f"M{j:02}",
                        timestamp=stamp,
                        pm25_ug_m3=max(0.0, value),
                        uncertainty_ug_m3=1.0,
                        origin="synthetic",
                        **point(p),
                    )
                )
    return Investigation(
        name="SYNTHETIC campaign: four independently steady wind periods",
        synthetic=True,
        sites=sites,
        source_locations=[
            Point(**point((x, y)))
            for x in (-450.0, -265.0, -80.0)
            for y in (-220.0, 0.0, 220.0)
        ],
        measurements=rows,
        weather=weather,
        study_windows=windows,
        assumptions=Assumptions(
            steady=True,
            open_terrain=True,
            local_weather=True,
            constant_release_across_windows=True,
            note="Synthetic constant release and fixed source under individually steady winds; not urban PM2.5 validation.",
        ),
        settings=Settings(
            objective="prediction_variance",
            budget=250.0,
            equipment_limit=2,
            noise_ug_m3=1.2,
            met_direction_sd_deg=3.0,
            met_speed_fraction=0.05,
            met_uncertainty_provenance="Synthetic met metadata only; no field calibration",
        ),
        area=[-0.012, -0.008, 0.012, 0.009],
    )
