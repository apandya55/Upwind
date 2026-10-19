"""Development sensitivity, independent profile and finite resource probes."""

import argparse
import copy
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time
import numpy as np
from ..inference import fit, CONFIG
from ..identifiability import whiten_profile
from .weather_bias import world, write, hashes, ROOT
from .research.run import source_metrics


def profiles(f, inv):
    c = f["profile_context"]
    t = c["times"]
    ids = c["sensor_ids"]
    xy = np.column_stack(
        f["projection"].transform(
            [r.longitude for r in f["rows"]], [r.latitude for r in f["rows"]]
        )
    )
    d = np.linalg.norm(xy[:, None] - xy[None], axis=-1)
    C = (
        np.diag(c["sigma"] ** 2)
        + CONFIG["instrument_bias_sd_ug_m3"] ** 2 * (ids[:, None] == ids[None])
        + inv.settings.noise_ug_m3**2
        * np.exp(
            -d / CONFIG["spatial_scale_m"]
            - abs(t[:, None] - t[None]) / CONFIG["temporal_scale_s"]
        )
    )
    labels = c["window_ids"]
    bg = c["bg_times"]
    nuisance = np.column_stack(
        [
            column
            for w in sorted(set(labels))
            for column in ((labels == w).astype(float), (labels == w) * bg / 3600)
        ]
    )
    prof = whiten_profile(c["observed"], c["signatures"], C, nuisance)
    conf = c["configs"]
    rows = []
    best = float(np.min(prof["loss"]))
    for angle in sorted(set(conf[:, 1])):
        indices = np.flatnonzero(conf[:, 1] == angle)
        k = int(indices[np.argmin(prof["loss"][indices])])
        cell = c["source_cell_indices"][k]
        rows.append(
            dict(
                offset_deg=float(angle),
                best_loss=float(prof["loss"][k]),
                delta_loss=float(prof["loss"][k] - best),
                effective_strength_ug_s=float(prof["strength"][k]),
                cell_center_xy_m=f["source_xy"][cell].tolist(),
            )
        )
    return dict(
        nuisance_rank=prof["nuisance_rank"],
        residual_dimensions=prof["residual_dimensions"],
        background_loss=prof["background_loss"],
        by_angle=rows,
        meaning="Independent GLS profile with common background/trend nuisance and unrestricted positive effective strength; delta loss is not calibrated coverage.",
    )


def sensitivity(out):
    out.mkdir(parents=True, exist_ok=False)
    write(
        out / "metadata.json",
        dict(
            source_hashes=hashes(),
            role="development-only sensitivity, no acceptance selection from final",
        ),
    )
    rows = []
    for geometry, kept in [
        ("all_six", range(6)),
        ("near_four", range(4)),
        ("far_four", range(2, 6)),
    ]:
        split = "development"
        seed = 1010001
        inv, state = world("direction_unknown", seed, split)
        inv.measurements = [m for m in inv.measurements if int(m.sensor_id[1:]) in kept]
        for diversity in ("four_winds", "same_wind"):
            case = inv.model_copy(deep=True)
            if diversity == "same_wind":
                # Re-simulate all plume increments under one wind, retain identical noise.
                from .research.cases import forward

                for r in case.measurements:
                    w = next(
                        i
                        for i, v in enumerate(case.study_windows)
                        if v.start <= r.timestamp <= v.end
                    )
                    xy = state["monitor_xy"][int(r.sensor_id[1:])]
                    old = forward(
                        [xy],
                        state["source_xy"],
                        state["strength"],
                        state["speed"],
                        state["true_angles"][w],
                        state["mechanism"],
                    )[0]
                    new = forward(
                        [xy],
                        state["source_xy"],
                        state["strength"],
                        state["speed"],
                        state["true_angles"][0],
                        state["mechanism"],
                    )[0]
                    r.pm25_ug_m3 = max(0.0, float(r.pm25_ug_m3 - old + new))
                for w in case.weather:
                    w.wind_from_deg = float(
                        (state["true_angles"][0] + state["station_direction_bias_deg"])
                        % 360
                    )
            base = fit(case, diagnostics=False)
            write(out / f"profile-{geometry}-{diversity}.json", profiles(base, case))
            for mode in (
                "base",
                "prior15",
                "prior30",
                "angle1",
                "shift_minus5",
                "shift_plus5",
                "grid10",
                "oracle",
            ):
                study = case.model_copy(deep=True)
                kwargs = {}
                original = copy.deepcopy(CONFIG)
                if mode == "prior15":
                    kwargs["weather_bias_sd"] = 15.0
                if mode == "prior30":
                    kwargs["weather_bias_sd"] = 30.0
                if mode == "angle1":
                    kwargs["weather_step_deg"] = 1.0
                if mode.startswith("shift_"):
                    for w in study.weather:
                        w.wind_from_deg = (
                            w.wind_from_deg + (-5 if mode == "shift_minus5" else 5)
                        ) % 360
                if mode == "grid10":
                    CONFIG["cell_target_m"] = 10.0
                if mode == "oracle":
                    study.settings.met_speed_fraction = 0.0
                    for j, w in enumerate(study.weather):
                        w.wind_speed_m_s = state["speed"]
                        w.wind_from_deg = state["true_angles"][
                            0 if diversity == "same_wind" else j // 4
                        ]
                    kwargs["wind_uncertainty"] = False
                try:
                    start = time.perf_counter()
                    f = (
                        base
                        if mode == "base"
                        else fit(study, diagnostics=False, **kwargs)
                    )
                    row = dict(
                        geometry=geometry,
                        diversity=diversity,
                        mode=mode,
                        **source_metrics(f, state),
                        meteorology=f["meteorology"],
                        seconds=time.perf_counter() - start,
                    )
                    rows.append(row)
                    with (out / "sensitivity.jsonl").open("a") as fp:
                        fp.write(json.dumps(row, allow_nan=False) + "\n")
                finally:
                    CONFIG.clear()
                    CONFIG.update(original)
            print(geometry, diversity, flush=True)
    write(
        out / "completion.json", dict(records=len(rows), source_hashes_after=hashes())
    )


def resource_child(limit, campaign, characterized):
    # The old shape generator is preserved verbatim; execute only its child
    # function under the current package, then optionally add noisy comparisons.
    from .resources import scale_case
    from .cases import point, scalar_plume
    from ..models import Point, StudyWindow
    from ..engine import analyze
    from datetime import datetime, timedelta, timezone

    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
    start = time.perf_counter()
    inv = scale_case(10000)
    monitors = [(800 + (i % 5) * 100, -500 + (i // 5) * 140) for i in range(40)]
    candidates = [(1500 + (j % 10) * 50, -400 + (j // 10) * 160) for j in range(60)]
    for s in inv.sites:
        p = monitors[int(s.id[1:])] if s.kind == "sensor" else candidates[int(s.id[1:])]
        c = point(p)
        s.latitude = c["latitude"]
        s.longitude = c["longitude"]
    for i, row in enumerate(inv.measurements):
        p = monitors[int(row.sensor_id[1:])]
        c = point(p)
        row.latitude = c["latitude"]
        row.longitude = c["longitude"]
        if campaign:
            w = (i // 40) % 6
            epoch = i // 240
            stamp = (
                datetime(2025, 1, 1, tzinfo=timezone.utc)
                + timedelta(hours=2 * w, seconds=epoch * 0.3)
            ).isoformat()
            row.timestamp = stamp
            inv.weather[i].timestamp = stamp
            inv.weather[i].wind_from_deg = 235 + 15 * w
        row.pm25_ug_m3 = 10 + scalar_plume(
            p, (-400, 0), 5000, 2.3, inv.weather[i].wind_from_deg
        )
    c = point((1000, 0))
    for row in inv.weather:
        row.latitude = c["latitude"]
        row.longitude = c["longitude"]
        row.source_id = "A"
        row.upstream_id = "A"
    if characterized:
        refs = [
            w.model_copy(
                update=dict(
                    role="reference",
                    source_id="B",
                    upstream_id="B",
                    wind_from_deg=(w.wind_from_deg + 1) % 360,
                    direction_systematic_sd_deg=2.0,
                    speed_systematic_fraction=0.03,
                    direction_random_sd_deg=1.0,
                    comparison_provenance="Synthetic reference, systematic offset1deg, not field validation",
                )
            )
            for w in inv.weather[::500]
        ]
        # Preserve the public total-weather-row cap while supplying20 references.
        inv.weather = inv.weather[: -len(refs)] + refs
        inv.settings.met_direction_sd_deg = 3.0
        inv.settings.met_speed_fraction = 0.05
    inv.source_locations = [
        Point(**point((x, y)))
        for x in (-600, -300, 0, 300, 600)
        for y in (-600, -300, 0, 300, 600)
    ]
    inv.settings.inference_limit = limit
    inv.settings.objective = "prediction_variance"
    if campaign:
        start_time = datetime(2025, 1, 1, tzinfo=timezone.utc)
        inv.study_windows = [
            StudyWindow(
                id=f"period-{w}",
                start=(start_time + timedelta(hours=2 * w)).isoformat(),
                end=(start_time + timedelta(hours=2 * w, minutes=1)).isoformat(),
            )
            for w in range(6)
        ]
        inv.assumptions.constant_release_across_windows = True
    result = analyze(inv)
    return dict(
        status="finished",
        analysis_status=result["status"],
        reason=result.get("reason"),
        rows_loaded=len(inv.measurements),
        weather=len(inv.weather),
        sites=len(inv.sites),
        anchors=len(inv.source_locations),
        rows_fitted=result.get("rows_used"),
        components=result.get("scenario_count"),
        finite_scores=all(np.isfinite(p["score"]) for p in result["plans"]),
        seconds=time.perf_counter() - start,
        peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
    )


def resources(out):
    out.mkdir(exist_ok=False, parents=True)
    write(
        out / "metadata.json",
        dict(
            source_hashes=hashes(), timeout_seconds=60, address_space_ceiling_mib=2048
        ),
    )
    rows = []
    for campaign, limit, characterized in [
        (False, 128, False),
        (False, 512, False),
        (True, 128, False),
        (True, 512, False),
        (True, 512, True),
    ]:
        command = (
            [
                sys.executable,
                "-m",
                "upwind.validation.weather_aux",
                "resource-child",
                "--limit",
                str(limit),
            ]
            + (["--campaign"] if campaign else [])
            + (["--characterized"] if characterized else [])
        )
        try:
            p = subprocess.run(
                command,
                cwd=ROOT,
                env={**os.environ, "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1"},
                capture_output=True,
                text=True,
                timeout=60,
            )
            r = (
                json.loads(p.stdout)
                if p.returncode == 0
                else dict(
                    status="child_failure",
                    exit_code=p.returncode,
                    stderr=p.stderr[-5000:],
                )
            )
        except subprocess.TimeoutExpired:
            r = dict(status="timeout", timeout_seconds=60)
        r.update(campaign=campaign, limit=limit, characterized=characterized)
        rows.append(r)
        write(out / "results.json", rows)
        print(json.dumps(r), flush=True)
    write(out / "completion.json", dict(source_hashes_after=hashes()))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["sensitivity", "resources", "resource-child"])
    p.add_argument("--out", type=Path)
    p.add_argument("--limit", type=int, default=128)
    p.add_argument("--campaign", action="store_true")
    p.add_argument("--characterized", action="store_true")
    a = p.parse_args()
    if a.mode == "resource-child":
        print(
            json.dumps(
                resource_child(a.limit, a.campaign, a.characterized), allow_nan=False
            )
        )
    elif a.mode == "resources":
        resources(a.out)
    else:
        sensitivity(a.out)


if __name__ == "__main__":
    main()
