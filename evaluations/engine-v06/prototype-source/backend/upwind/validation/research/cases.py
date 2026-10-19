"""Independent evaluator state and explicit measurement interventions."""

from datetime import datetime, timedelta, timezone
import math
import numpy as np
from scipy.special import gamma
from pyproj import CRS, Transformer
from ...models import (
    Investigation,
    Measurement,
    Weather,
    Site,
    Point,
    Settings,
    Assumptions,
    StudyWindow,
)
from ..cases import scalar_plume
from ..overhaul import make_world as previous_world

SPLITS = {
    "development": range(710000, 710012),
    "calibration": range(810000, 810024),
    "final": range(910000, 910040),
}
FAMILIES = (
    "single_window_original",
    "informative_campaign",
    "same_wind_repetition",
    "weak_campaign",
    "background_campaign",
    "two_sources_campaign",
    "changing_release_campaign",
    "biased_met_campaign",
    "correlated_campaign",
    "boundary_campaign",
    "independent_transport",
    "unsupported_campaign",
)
LAYOUTS = {
    "development": [(40, -120), (40, 0), (40, 120), (260, -90), (260, 90), (600, 0)],
    "calibration": [
        (60, -180),
        (80, 60),
        (240, -30),
        (300, 180),
        (500, -150),
        (750, 100),
    ],
    "final": [(50, -200), (95, 110), (180, -15), (360, 210), (510, -120), (780, 65)],
}
BOUNDS = (-450.0, -220.0, -80.0, 220.0)


def transform(split):
    lat, lon = {
        "development": (35.0, -80.0),
        "calibration": (48.0, 10.0),
        "final": (43.0, -92.0),
    }[split]
    local = CRS.from_proj4(
        f"+proj=aeqd +lat_0={lat} +lon_0={lon} +datum=WGS84 +units=m"
    )
    return Transformer.from_crs(local, "EPSG:4326", always_xy=True)


def point(xy, split):
    lon, lat = transform(split).transform(*xy)
    return {"latitude": float(lat), "longitude": float(lon)}


def diffusion_transport(
    points, source, q, speed, direction, height=5.0, receptor_height=2.0
):
    """Steady advection/transverse-diffusion solution, reflected ground.

    K_y=1.3m²/s, K_z=.6m²/s; finite initial widths2m/1m. Gaussian
    transverse densities integrate to Q/u. Widths are sqrt(2 K x/u + s0²),
    independently different from production's empirical near-linear growth.
    """
    points = np.asarray(points, dtype=float)
    delta = points - np.asarray(source)
    theta = math.radians(direction)
    x = -delta[:, 0] * math.sin(theta) - delta[:, 1] * math.cos(theta)
    y = delta[:, 0] * math.cos(theta) - delta[:, 1] * math.sin(theta)
    sy = np.sqrt(4 + 2 * 1.3 * np.maximum(x, 0) / speed)
    sz = np.sqrt(1 + 2 * 0.6 * np.maximum(x, 0) / speed)
    cross = np.exp(-y * y / (2 * sy * sy)) / (math.sqrt(2 * math.pi) * sy)
    vertical = (
        np.exp(-((receptor_height - height) ** 2) / (2 * sz * sz))
        + np.exp(-((receptor_height + height) ** 2) / (2 * sz * sz))
    ) / (math.sqrt(2 * math.pi) * sz)
    return np.where(x > 0, q / speed * cross * vertical, 0.0)


def stretched_transport(points, source, q, speed, direction, height=5.0):
    """Independent generalized-normal lateral distribution with finite intercepts."""
    delta = np.asarray(points) - np.asarray(source)
    theta = math.radians(direction)
    down = -delta[:, 0] * math.sin(theta) - delta[:, 1] * math.cos(theta)
    cross = delta[:, 0] * math.cos(theta) - delta[:, 1] * math.sin(theta)
    x = np.maximum(down, 0)
    sy = (6 + 0.10 * x) / (1 + x / 700) ** 0.18
    sz = (3 + 0.065 * x) / (1 + x / 600) ** 0.1
    exponent = 2.1
    lateral = (
        exponent
        * np.exp(-(abs(cross / sy) ** exponent))
        / (2 * sy * gamma(1 / exponent))
    )
    vertical = (
        np.exp(-((2 - height) ** 2) / (2 * sz * sz))
        + np.exp(-((2 + height) ** 2) / (2 * sz * sz))
    ) / (math.sqrt(2 * math.pi) * sz)
    return np.where(down > 0, q / speed * lateral * vertical, 0.0)


def forward(points, source, q, speed, direction, mechanism):
    if mechanism == "diffusion":
        return diffusion_transport(points, source, q, speed, direction)
    if mechanism == "stretched":
        return stretched_transport(points, source, q, speed, direction)
    return np.array([scalar_plume(p, source, q, speed, direction) for p in points])


def world(family, seed, split):
    if family == "single_window_original":
        inv, old = previous_world(
            "strong_signal", seed, "final" if split == "final" else split
        )
        return inv, {
            "previous": old,
            "family": family,
            "seed": seed,
            "split": split,
            "source_xy": old["source_xy"],
            "source_present": True,
            "mechanism": "previous-stretched",
        }
    rng = np.random.default_rng(seed)
    source = rng.uniform([-450, -220], [-80, 220])
    q = float(rng.uniform(18000, 36000))
    if family == "weak_campaign":
        q = float(rng.uniform(150, 450))
    if family == "background_campaign":
        q = 0.0
    if family == "boundary_campaign":
        edge = int(rng.integers(4))
        source[edge % 2] = [
            -450 + rng.uniform(0.5, 5),
            -220 + rng.uniform(0.5, 5),
            -80 - rng.uniform(0.5, 5),
            220 - rng.uniform(0.5, 5),
        ][edge]
    secondary = rng.uniform([-450, -220], [-80, 220])
    for _ in range(20):
        if np.linalg.norm(secondary - source) >= 100:
            break
        secondary = rng.uniform([-450, -220], [-80, 220])
    q2 = q * 0.8 if family == "two_sources_campaign" else 0.0
    coords = np.array(LAYOUTS[split], float) + rng.uniform(-8, 8, (6, 2))
    candidates = np.array(
        [(x, y) for x in (20.0, 150.0, 330.0, 560.0) for y in (-110.0, 0.0, 110.0)]
    )
    # Independent reading targets at the declared permissible receptor coordinates.
    # Their instrument errors differ from selected candidate instruments.
    target_xy = candidates.copy()
    angles = np.array(
        {
            "development": [235, 260, 285, 310],
            "calibration": [225, 255, 290, 320],
            "final": [220, 250, 280, 315],
        }[split],
        float,
    )
    angles += rng.uniform(-3, 3)
    if family == "same_wind_repetition":
        angles[:] = angles[1]
    met_error = float(rng.normal(0, 2)) + (25 if family == "biased_met_campaign" else 0)
    speed = float(rng.uniform(1.8, 3.4))
    speed_bias = float(rng.normal(0, 0.03))
    mechanism = (
        "diffusion"
        if family == "independent_transport"
        else ("stretched" if split == "calibration" else "neutral")
    )
    background = rng.normal(12, 2, 4)
    multipliers = (
        np.array([0.25, 2.0, 0.4, 1.6])
        if family == "changing_release_campaign"
        else np.ones(4)
    )
    start = datetime(2026, 6, 2, 9, tzinfo=timezone.utc)
    windows = []
    stamps = []
    rows = []
    weather = []
    epochs = np.repeat(np.arange(4), 24)
    initial_xy = np.tile(coords, (16, 1))
    initial_times = np.array(
        [w * 7200 + t * 300 for w in range(4) for t in range(4) for _ in range(6)]
    )
    all_xy = np.concatenate((initial_xy, candidates, target_xy))
    all_times = np.r_[initial_times, np.full(24, 6 * 3600 + 900)]
    dist = np.linalg.norm(all_xy[:, None] - all_xy[None], axis=-1)
    amp = 3.0 if family == "correlated_campaign" else 0.7
    length = 500.0 if family == "correlated_campaign" else 180.0
    temporal = 1200.0 if family == "correlated_campaign" else 600.0
    field = rng.multivariate_normal(
        np.zeros(len(all_xy)),
        amp**2
        * np.exp(-dist / length - abs(all_times[:, None] - all_times[None]) / temporal)
        + np.eye(len(all_xy)) * 1e-10,
    )
    bias = np.r_[np.tile(rng.normal(0, 0.7, 6), 16), rng.normal(0, 0.7, 24)]
    sigma = rng.uniform(0.8, 1.5, len(all_xy))
    latent = []
    inc = []
    for j, (xy, w) in enumerate(zip(initial_xy, epochs)):
        value = float(
            forward([xy], source, q * multipliers[w], speed, angles[w], mechanism)[0]
            + forward([xy], secondary, q2, speed, angles[w], mechanism)[0]
        )
        latent.append(background[w] + value)
        inc.append(value)
    future_inc = forward(
        np.concatenate((candidates, target_xy)),
        source,
        q * multipliers[-1],
        speed,
        angles[-1],
        mechanism,
    ) + forward(
        np.concatenate((candidates, target_xy)),
        secondary,
        q2,
        speed,
        angles[-1],
        mechanism,
    )
    means = np.r_[latent, background[-1] + future_inc]
    latent = means + field + bias
    initial = np.maximum(0, latent[:96] + rng.normal(0, sigma[:96]))
    for w in range(4):
        ws = start + timedelta(hours=2 * w)
        we = ws + timedelta(minutes=15)
        windows.append(
            StudyWindow(id=f"period-{w + 1}", start=ws.isoformat(), end=we.isoformat())
        )
        for epoch in range(4):
            stamp = (ws + timedelta(minutes=5 * epoch)).isoformat()
            stamps.append(stamp)
            for sensor, xy in enumerate(coords):
                j = w * 24 + epoch * 6 + sensor
                rows.append(
                    Measurement(
                        sensor_id=f"M{sensor:02}",
                        timestamp=stamp,
                        pm25_ug_m3=float(initial[j]),
                        uncertainty_ug_m3=float(sigma[j]),
                        origin="synthetic",
                        **point(xy, split),
                    )
                )
            weather.append(
                Weather(
                    timestamp=stamp,
                    wind_speed_m_s=0.2
                    if family == "unsupported_campaign" and w == 2
                    else speed * (1 + speed_bias),
                    wind_from_deg=float((angles[w] + met_error) % 360),
                    origin="synthetic",
                    provenance="Simulated observed met instrument; coherent campaign calibration error",
                    **point((150, 0), split),
                )
            )
    sites = [
        Site(id=f"M{i:02}", name=f"Monitor {i + 1}", kind="sensor", **point(xy, split))
        for i, xy in enumerate(coords)
    ]
    sites += [
        Site(
            id=f"C{i:02}",
            name=f"Permissible receptor {i + 1}",
            allowed=True,
            power=True,
            access=True,
            cost=float([90, 110, 120, 100][i % 4]),
            **point(xy, split),
        )
        for i, xy in enumerate(candidates)
    ]
    corners = [point((-800, -800), split), point((1300, 800), split)]
    inv = Investigation(
        name="Synthetic multi-period investigation",
        synthetic=True,
        area=[
            corners[0]["longitude"],
            corners[0]["latitude"],
            corners[1]["longitude"],
            corners[1]["latitude"],
        ],
        sites=sites,
        measurements=rows,
        weather=weather,
        study_windows=windows,
        source_locations=[
            Point(**point((x, y), split))
            for x in (-450.0, -265.0, -80.0)
            for y in (-220.0, 0.0, 220.0)
        ],
        assumptions=Assumptions(
            steady=True,
            open_terrain=True,
            local_weather=True,
            constant_release_across_windows=True,
            note="Simulated, separately steady periods; source conditions are assumptions, not field verification.",
        ),
        settings=Settings(
            budget=250.0,
            equipment_limit=2,
            seed=17,
            noise_ug_m3=1.2,
            met_direction_sd_deg=3.0,
            met_speed_fraction=0.05,
            met_uncertainty_provenance="Simulated instrument standard direction uncertainty 3 degrees and speed scenario fraction5%; not field calibration",
        ),
    )
    state = {
        "family": family,
        "seed": seed,
        "split": split,
        "source_xy": source.tolist(),
        "source_present": q > 0,
        "strength": q,
        "secondary_xy": secondary.tolist(),
        "secondary_strength": q2,
        "true_angles": angles.tolist(),
        "speed": speed,
        "background": background.tolist(),
        "mechanism": mechanism,
        "source_multipliers": multipliers.tolist(),
        "monitor_xy": coords.tolist(),
        "candidate_xy": candidates.tolist(),
        "target_xy": target_xy.tolist(),
        "future_latent": latent[96:].tolist(),
        "future_sigma": sigma[96:].tolist(),
        "future_noise_seed": seed + 2000000,
        "last_timestamp": stamps[-1],
        "true_max_initial_increment_ug_m3": float(np.max(inc)),
        "true_rms_initial_increment_ug_m3": float(np.sqrt(np.mean(np.array(inc) ** 2))),
    }
    return inv, state


def reveal(state):
    if "previous" in state:
        from ..overhaul import reveal_future

        state["previous"] = reveal_future(state["previous"])
        return
    rng = np.random.default_rng(state["future_noise_seed"])
    values = np.maximum(
        0, np.array(state["future_latent"]) + rng.normal(0, state["future_sigma"])
    )
    state["candidate_outcomes"] = values[:12].tolist()
    state["target_outcomes"] = values[12:].tolist()
