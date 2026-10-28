"""Weather bias benchmark runner."""

import argparse
import hashlib
import importlib
import importlib.util
import json
import platform
import resource
import sys
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

from ..models import (
    Investigation,
    Measurement,
    Weather,
    Site,
    Point,
    Settings,
    Assumptions,
    StudyWindow,
)
from ..inference import fit, MODEL_VERSION, CONFIG
from ..engine import analyze, eligible_indices, select_plan
from .research.cases import point, forward, reveal
from .research.run import source_metrics, score_prediction, distribution, wilson

ROOT = Path(__file__).resolve().parents[3]
PROTOCOL = "UW-WEATHER-2026-03"
SPLITS = {
    "development": range(1010000, 1010008),
    "calibration": range(1110000, 1110016),
    "final": range(1210000, 1210032),
}
FAMILIES = (
    "characterized_nominal",
    "unknown_nominal",
    "direction_unknown",
    "direction_characterized",
    "speed_bias",
    "clock_lag",
    "distant_station",
    "spatial_winds",
    "variable_weather",
    "weak",
    "correlated",
    "two_sources",
    "background",
    "independent_transport",
)
LAYOUTS = {
    "development": [
        (35, -175),
        (85, 85),
        (210, -45),
        (325, 150),
        (545, -110),
        (710, 55),
    ],
    "calibration": [
        (70, -140),
        (125, 155),
        (260, -75),
        (405, 35),
        (590, 190),
        (820, -115),
    ],
    "final": [(25, 160), (110, -185), (225, 45), (375, -125), (625, 125), (850, -30)],
}
ANGLES = {
    "development": [230, 258, 292, 318],
    "calibration": [216, 249, 281, 306],
    "final": [211, 242, 287, 326],
}


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def hashes():
    paths = list((ROOT / "backend/upwind").rglob("*.py")) + [
        ROOT / "requirements.lock",
        ROOT / "frontend/package-lock.json",
    ]
    return {
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(paths)
    }


def baseline():
    name = "_upwind_weather_04"
    if name not in sys.modules:
        p = ROOT / "evaluations/weather-bias/baseline-source/backend/upwind"
        spec = importlib.util.spec_from_file_location(
            name, p / "__init__.py", submodule_search_locations=[str(p)]
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return tuple(
        importlib.import_module(name + "." + part)
        for part in ("inference", "models", "engine")
    )


def old_input(inv):
    _, m, _ = baseline()
    d = inv.model_dump()
    d = {k: v for k, v in d.items() if k in m.Investigation.model_fields}
    # 0.4 has no comparison model: preserve the originally observed primary.
    d["weather"] = [
        {k: v for k, v in w.items() if k in m.Weather.model_fields}
        for w in d["weather"]
        if w["role"] == "primary"
    ]
    return m.Investigation.model_validate(d)


def world(family, seed, split):
    rng = np.random.default_rng(seed)
    source = rng.uniform([-450, -220], [-80, 220])
    q = float(rng.uniform(18000, 36000))
    if family == "weak":
        q = float(rng.uniform(150, 450))
    if family == "background":
        q = 0.0
    secondary = rng.uniform([-450, -220], [-80, 220])
    q2 = 0.8 * q if family == "two_sources" else 0.0
    coords = np.array(LAYOUTS[split], float) + rng.uniform(-12, 12, (6, 2))
    candidates = np.array(
        [(x, y) for x in (15.0, 175.0, 365.0, 610.0) for y in (-145.0, 20.0, 165.0)]
    )
    angles = np.array(ANGLES[split], float) + rng.uniform(-4, 4, 4)
    speed = float(rng.uniform(1.8, 3.4))
    bias = float(rng.normal(0, 1.5))
    speed_factor = float(np.exp(rng.normal(0, 0.025)))
    if family in ("direction_unknown", "direction_characterized"):
        interval = {
            "development": (20, 26),
            "calibration": (27, 35),
            "final": (18, 19) if seed % 4 < 2 else (36, 42),
        }[split]
        magnitude = rng.uniform(*interval)
        bias = float(magnitude * (-1 if seed % 2 else 1))
    if family == "speed_bias":
        speed_factor = float(rng.uniform(0.75, 1.35))
    background = rng.normal(12, 2, 4)
    mechanism = (
        "diffusion"
        if family == "independent_transport"
        else ("stretched" if split == "calibration" else "neutral")
    )
    epochs = np.repeat(np.arange(4), 24)
    initial_xy = np.tile(coords, (16, 1))
    times = np.array(
        [w * 7200 + t * 300 for w in range(4) for t in range(4) for _ in range(6)]
    )
    all_xy = np.concatenate((initial_xy, candidates, candidates))
    all_times = np.r_[times, np.full(24, 22500)]
    amp, length, temporal = (
        (3.0, 500.0, 1200.0) if family == "correlated" else (0.7, 180.0, 600.0)
    )
    distances = np.linalg.norm(all_xy[:, None] - all_xy[None], axis=-1)
    cov = (
        amp**2
        * np.exp(
            -distances / length - abs(all_times[:, None] - all_times[None]) / temporal
        )
        + np.eye(120) * 1e-10
    )
    field = np.linalg.cholesky(cov) @ rng.normal(size=120)
    instrument = np.r_[np.tile(rng.normal(0, 0.7, 6), 16), rng.normal(0, 0.7, 24)]
    sigma = rng.uniform(0.8, 1.5, 120)
    # Clock lag changes alignment of a slowly turning wind, not the true source.
    turn = 1.2 if family == "clock_lag" else 0.0
    lag_minutes = (
        float(
            rng.uniform(
                *{"development": (5, 8), "calibration": (8, 11), "final": (11, 15)}[
                    split
                ]
            )
        )
        if family == "clock_lag"
        else 0.0
    )
    spatial = float(rng.uniform(12, 30)) if family == "spatial_winds" else 0.0
    spatial_shape = lambda y: (
        np.clip(y / 200, -1, 1) if split == "development" else np.tanh(y / 120)
    )
    actual_angles = np.array(
        [
            angles[w]
            + turn * ((j % 24) // 6 - 1.5) * 5
            + spatial
            * spatial_shape(xy[1])
            * (1 + (0.3 * np.sin(w) if split == "final" else 0))
            for j, (xy, w) in enumerate(zip(initial_xy, epochs))
        ]
    )
    latent = []
    increments = []
    for xy, w, a in zip(initial_xy, epochs, actual_angles):
        inc = float(
            forward([xy], source, q, speed, a, mechanism)[0]
            + forward([xy], secondary, q2, speed, a, mechanism)[0]
        )
        latent.append(background[w] + inc)
        increments.append(inc)
    future_angles = (
        angles[-1]
        + turn * 7.5
        + spatial
        * spatial_shape(candidates[:, 1])
        * (1 + (0.3 * np.sin(3) if split == "final" else 0))
    )
    future_inc = np.array(
        [
            forward([xy], source, q, speed, a, mechanism)[0]
            + forward([xy], secondary, q2, speed, a, mechanism)[0]
            for xy, a in zip(candidates, future_angles)
        ]
    )
    means = np.r_[latent, background[-1] + future_inc, background[-1] + future_inc]
    values = means + field + instrument
    initial = np.maximum(0, values[:96] + rng.normal(0, sigma[:96]))
    start = datetime(2026, 8, 10, 9, tzinfo=timezone.utc)
    windows = []
    measurements = []
    weather = []
    stamps = []
    for w in range(4):
        ws = start + timedelta(hours=2 * w)
        windows.append(
            StudyWindow(
                id=f"period-{w + 1}",
                start=ws.isoformat(),
                end=(ws + timedelta(minutes=15)).isoformat(),
            )
        )
        for t in range(4):
            stamp = (ws + timedelta(minutes=t * 5)).isoformat()
            stamps.append(stamp)
            for i, xy in enumerate(coords):
                j = w * 24 + t * 6 + i
                measurements.append(
                    Measurement(
                        sensor_id=f"M{i:02}",
                        timestamp=stamp,
                        pm25_ug_m3=float(initial[j]),
                        uncertainty_ug_m3=float(sigma[j]),
                        origin="synthetic",
                        **point(xy, split),
                    )
                )
            observed = angles[w] + turn * (t - 1.5) * 5 + bias
            if split == "final" and family in (
                "direction_unknown",
                "direction_characterized",
            ):
                observed += [-2.0, 1.0, 0.0, 3.0][w]
            if family == "variable_weather" and w == 1 and t == 2:
                observed += 85
            weather.append(
                Weather(
                    timestamp=(ws + timedelta(minutes=t * 5 + lag_minutes)).isoformat(),
                    wind_speed_m_s=speed * speed_factor,
                    wind_from_deg=float(observed % 360),
                    origin="synthetic",
                    source_id="station-A",
                    upstream_id="instrument-A",
                    provenance="Synthetic station measurement; evaluator withholds calibration truth",
                    **point(
                        (4100, 0) if family == "distant_station" else (150, 0), split
                    ),
                )
            )
    if family in (
        "characterized_nominal",
        "direction_characterized",
        "independent_transport",
    ):
        systematic = float(rng.normal(0, 2))
        speed_systematic = float(rng.normal(0, 0.03))
        for j, p in enumerate(list(weather)):
            a = angles[j // 4] + systematic + rng.normal(0, 1)
            weather.append(
                p.model_copy(
                    update=dict(
                        role="reference",
                        source_id="reference-B",
                        upstream_id="instrument-B",
                        wind_from_deg=float(a % 360),
                        wind_speed_m_s=float(
                            speed * np.exp(speed_systematic + rng.normal(0, 0.02))
                        ),
                        direction_systematic_sd_deg=2.0,
                        speed_systematic_fraction=0.03,
                        direction_random_sd_deg=1.0,
                        comparison_provenance="Simulated independent paired instrument with shared 2deg/3% systematic error; not field evidence",
                    )
                )
            )
    sites = [
        Site(id=f"M{i:02}", name=f"Monitor{i}", kind="sensor", **point(xy, split))
        for i, xy in enumerate(coords)
    ]
    sites += [
        Site(
            id=f"C{i:02}",
            name=f"Candidate{i}",
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
        name="Synthetic weather-bias holdout",
        synthetic=True,
        area=[
            corners[0]["longitude"],
            corners[0]["latitude"],
            corners[1]["longitude"],
            corners[1]["latitude"],
        ],
        measurements=measurements,
        weather=weather,
        study_windows=windows,
        sites=sites,
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
            note="Synthetic assumptions, not verification",
        ),
        settings=Settings(
            budget=250,
            equipment_limit=2,
            seed=17,
            noise_ug_m3=1.2,
            met_direction_sd_deg=3.0,
            met_speed_fraction=0.05,
            met_uncertainty_provenance="Short-period declared uncertainty; persistent station accuracy unknown",
        ),
    )
    state = dict(
        family=family,
        seed=seed,
        split=split,
        source_xy=source.tolist(),
        source_present=q > 0,
        strength=q,
        secondary_xy=secondary.tolist(),
        secondary_strength=q2,
        true_angles=angles.tolist(),
        actual_initial_angles=actual_angles.tolist(),
        speed=speed,
        station_direction_bias_deg=bias,
        station_speed_factor=speed_factor,
        clock_lag_minutes=lag_minutes,
        spatial_direction_amplitude_deg=spatial,
        background=background.tolist(),
        mechanism=mechanism,
        monitor_xy=coords.tolist(),
        candidate_xy=candidates.tolist(),
        target_xy=candidates.tolist(),
        future_latent=values[96:].tolist(),
        future_sigma=sigma[96:].tolist(),
        future_noise_seed=seed + 3000000,
        last_timestamp=stamps[-1],
        true_max_initial_increment_ug_m3=max(increments),
    )
    return inv, state


def accepted(row):
    return bool(
        row["source_probability"] >= 0.9
        and row["region90_area_fraction"] < 0.5
        and not row["warning"]
        and not row.get("weather_warning", False)
    )


def evaluate(inv, state, old=False):
    t = time.perf_counter()
    row = dict(
        family=state["family"],
        seed=state["seed"],
        model="baseline-0.4.0" if old else MODEL_VERSION,
    )
    try:
        f = (
            baseline()[0].fit(old_input(inv), diagnostics=True)
            if old
            else fit(inv, diagnostics=True)
        )
        row.update(
            status="fitted",
            **source_metrics(f, state),
            warning=bool(f["diagnostics"]["predictive_warning"]),
            weather_warning=False if old else f["meteorology"]["weather_warning"],
            diagnostics=f["diagnostics"],
            rows_used=f["rows_used"],
        )
        if not old:
            row["meteorology"] = f["meteorology"]
        row["accepted"] = accepted(row)
    except ValueError as e:
        row.update(status="refused", reason=str(e))
    except Exception as e:
        row.update(status="crash", reason=f"{type(e).__name__}: {e}")
    row["wall_ms"] = 1000 * (time.perf_counter() - t)
    row["process_peak_rss_mib"] = (
        resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    )
    return row


def plans(inv):
    locked = []
    for name, objective in [
        ("prediction_risk", "prediction_variance"),
        ("information", "scenario_information"),
    ]:
        study = inv.model_copy(deep=True)
        study.settings.objective = objective
        result = analyze(study)
        locked.append((name, result["plans"][0]["site_ids"] if result["plans"] else []))
        if name == "prediction_risk":
            for method, prefix in [("spread", "Spatial"), ("wind", "Wind")]:
                p = next(
                    (p for p in result["plans"] if p["method"].startswith(prefix)), None
                )
                locked.append((method, p["site_ids"] if p else []))
    prior = baseline()[2].analyze(old_input(inv))
    locked.append(
        (
            "baseline_0.4_planner",
            prior["plans"][0]["site_ids"] if prior["plans"] else [],
        )
    )
    supported = fit(inv, diagnostics=False)["candidate_supported"]
    eligible = [i for i in eligible_indices(inv) if supported[i]]
    for seed in range(8000, 8010):
        ids = select_plan(
            inv, "random", lambda s: 0, eligible, np.random.default_rng(seed)
        )
        locked.append((f"random-{seed}", [inv.sites[i].id for i in ids]))
    return locked


def followup(inv, state):
    locked = plans(inv)
    lock = hashlib.sha256(json.dumps(locked, sort_keys=True).encode()).hexdigest()
    reveal(state)  # All policies locked before outcomes are realized.
    targets = [
        Measurement(
            sensor_id=f"target-{i}",
            timestamp=state["last_timestamp"],
            pm25_ug_m3=float(value),
            uncertainty_ug_m3=float(s),
            origin="synthetic",
            **point(xy, state["split"]),
        )
        for i, (xy, value, s) in enumerate(
            zip(
                state["target_xy"], state["target_outcomes"], state["future_sigma"][12:]
            )
        )
    ]
    rows = []
    for method, ids in locked:
        updated = inv.model_copy(deep=True)
        cost = 0.0
        for id in ids:
            site = next(s for s in inv.sites if s.id == id)
            j = int(id[1:])
            cost += site.cost
            updated.measurements.append(
                Measurement(
                    sensor_id="followup-" + id,
                    timestamp=state["last_timestamp"],
                    pm25_ug_m3=state["candidate_outcomes"][j],
                    uncertainty_ug_m3=state["future_sigma"][j],
                    origin="synthetic",
                    latitude=site.latitude,
                    longitude=site.longitude,
                )
            )
        assert cost <= 250 and len(ids) <= 2
        row = dict(
            family=state["family"],
            seed=state["seed"],
            method=method,
            site_ids=ids,
            cost=cost,
            equipment=len(ids),
            locked_plan_sha256=lock,
        )
        try:
            f = fit(updated, diagnostics=False)
            # Primary inference is identical for all planners; baseline selects only.
            row.update(
                status="fitted",
                **source_metrics(f, state),
                prediction=score_prediction(f, targets, state["target_outcomes"]),
            )
        except Exception as e:
            row.update(status="crash", reason=f"{type(e).__name__}: {e}")
        rows.append(row)
    return rows


def summary(science, planning):
    conditions = []
    for family in dict.fromkeys(r["family"] for r in science):
        for model in ("baseline-0.4.0", MODEL_VERSION):
            rows = [r for r in science if r["family"] == family and r["model"] == model]
            if not rows:
                continue
            fitted = [r for r in rows if r["status"] == "fitted"]
            yes = [r for r in fitted if r["accepted"]]
            no = [r for r in fitted if not r["accepted"]]
            wrong = sum(r["source_present"] and not r["region90_covered"] for r in yes)
            d = dict(
                family=family,
                model=model,
                generated=len(rows),
                statuses=dict(Counter(r["status"] for r in rows)),
                accepted_count=len(yes),
                abstained=len(no),
                accepted_wrong=wrong,
                wrong_given_accepted=dict(
                    count=wrong, n=len(yes), wilson95=wilson(wrong, len(yes))
                ),
                wrong_per_generated=dict(
                    count=wrong, n=len(rows), wilson95=wilson(wrong, len(rows))
                ),
            )
            d["acceptance_rate"] = dict(
                count=len(yes), n=len(rows), wilson95=wilson(len(yes), len(rows))
            )
            d["abstention_rate"] = dict(
                count=len(no), n=len(rows), wilson95=wilson(len(no), len(rows))
            )
            d["unwarned_wrong_regions"] = sum(
                r["source_present"]
                and not r["region90_covered"]
                and not r["warning"]
                and not r.get("weather_warning", False)
                for r in fitted
            )
            for label, group in [("all", fitted), ("accepted", yes), ("rejected", no)]:
                d[label] = {
                    key: distribution([r.get(key) for r in group])
                    for key in (
                        "map_error_m",
                        "mean_error_m",
                        "prior_centroid_error_m",
                        "region90_area_fraction",
                        "region90_area_m2",
                        "region90_mass",
                        "source_probability",
                        "source_brier",
                        "wall_ms",
                    )
                }
                for key in (
                    "region90_covered",
                    "warning",
                    "weather_warning",
                    "source_miss",
                    "false_source_alarm",
                ):
                    eligible = [
                        r
                        for r in group
                        if r.get(key) is not None
                        and (key != "source_miss" or r["source_present"])
                        and (key != "false_source_alarm" or not r["source_present"])
                    ]
                    n = len(eligible)
                    k = sum(bool(r[key]) for r in eligible)
                    d[label][key] = dict(count=k, n=n, wilson95=wilson(k, n))
            conditions.append(d)
    paired = []
    rng = np.random.default_rng(90311)
    for family in dict.fromkeys(r["family"] for r in planning):
        for method in (
            "prediction_risk",
            "information",
            "baseline_0.4_planner",
            "spread",
            "wind",
        ):
            rows = [
                r
                for r in planning
                if r["family"] == family
                and r["method"] == method
                and r["status"] == "fitted"
            ]
            delta = []
            localization = []
            for row in rows:
                random = [
                    r
                    for r in planning
                    if r["family"] == family
                    and r["seed"] == row["seed"]
                    and r["method"].startswith("random-")
                    and r["status"] == "fitted"
                ]
                if len(random) != 10:
                    continue
                delta.append(
                    float(
                        np.mean([r["prediction"]["rmse_ug_m3"] for r in random])
                        - row["prediction"]["rmse_ug_m3"]
                    )
                )
                localization.append(
                    float(
                        np.mean([r["map_error_m"] for r in random]) - row["map_error_m"]
                    )
                )
            if delta:
                boot = np.mean(
                    rng.choice(delta, size=(5000, len(delta)), replace=True), axis=1
                )
                paired.append(
                    dict(
                        family=family,
                        method=method,
                        n=len(delta),
                        rmse_advantage=distribution(delta),
                        paired_bootstrap95=np.quantile(boot, [0.025, 0.975]).tolist(),
                        losses=sum(x < 0 for x in delta),
                        largest_loss=max(0.0, -min(delta)),
                        map_advantage=distribution(localization),
                    )
                )
    return dict(protocol=PROTOCOL, conditions=conditions, planning=paired)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--split", choices=SPLITS, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--limit", type=int)
    p.add_argument("--offset", type=int, default=0)
    p.add_argument("--stride", type=int, default=1)
    p.add_argument("--families", nargs="+", choices=FAMILIES)
    p.add_argument("--planning", action="store_true")
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    seeds = list(SPLITS[args.split])[args.offset :: args.stride]
    seeds = seeds[: args.limit] if args.limit else seeds
    before = hashes()
    write(
        args.out / "metadata.json",
        dict(
            protocol=PROTOCOL,
            model=MODEL_VERSION,
            split=args.split,
            seeds=seeds,
            families=args.families or FAMILIES,
            config=CONFIG,
            python=platform.python_version(),
            source_hashes_before=before,
        ),
    )
    science = []
    planning = []
    started = time.perf_counter()
    for seed in seeds:
        for family in args.families or FAMILIES:
            inv, state = world(family, seed, args.split)
            write(
                args.out / f"input-{family}-{seed}.json",
                dict(investigation=inv.model_dump(), private_truth=state),
            )
            for old in (True, False):
                row = evaluate(inv, state, old)
                science.append(row)
                with (args.out / "science.jsonl").open("a") as f:
                    f.write(json.dumps(row, allow_nan=False) + "\n")
            if (
                args.planning
                and seed < list(SPLITS[args.split])[0] + 8
                and family
                in ("unknown_nominal", "direction_unknown", "direction_characterized")
            ):
                try:
                    new = followup(inv, state)
                except Exception as e:
                    new = [
                        dict(
                            family=family,
                            seed=seed,
                            status="crash",
                            reason=f"{type(e).__name__}: {e}",
                            method="plan_generation",
                        )
                    ]
                planning.extend(new)
                with (args.out / "planning.jsonl").open("a") as f:
                    for row in new:
                        f.write(json.dumps(row, allow_nan=False) + "\n")
            print(
                f"{args.split} {seed} {family}: {science[-1]['status']} accepted={science[-1].get('accepted')}",
                flush=True,
            )
    write(args.out / "summary.json", summary(science, planning))
    after = hashes()
    write(
        args.out / "completion.json",
        dict(
            seconds=time.perf_counter() - started,
            science=len(science),
            followups=len(planning),
            source_hashes_after=after,
            source_unchanged=before == after,
            process_peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            / 1024,
        ),
    )


if __name__ == "__main__":
    main()
