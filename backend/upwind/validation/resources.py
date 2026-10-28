"""Run each scale boundary in a fresh, timed, memory-limited subprocess."""

import json, sys, time, resource
from pathlib import Path
from datetime import datetime, timedelta, timezone
import numpy as np
from ..models import (
    Investigation,
    Site,
    Point,
    Measurement,
    Weather,
    Assumptions,
    Settings,
)
from ..engine import analyze
from .cases import point, scalar_plume


def scale_case(size):
    rows, met, sites = [], [], []
    sensors = min(40, max(3, size // 250))
    coords = [(100 + (i % 5) * 60, -300 + (i // 5) * 80) for i in range(sensors)]
    for i, p in enumerate(coords):
        sites.append(
            Site(id=f"M{i}", name=f"Synthetic monitor {i}", kind="sensor", **point(p))
        )
    for i in range(100 - sensors):
        sites.append(
            Site(
                id=f"C{i:02}",
                name=f"Synthetic candidate {i}",
                allowed=True,
                power=True,
                access=True,
                cost=100,
                **point((500 + (i % 10) * 30, -400 + (i // 10) * 100)),
            )
        )
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    for i in range(size):
        stamp = (start + timedelta(seconds=i * 0.3)).isoformat()
        sensor = i % sensors
        p = coords[sensor]
        rows.append(
            Measurement(
                sensor_id=f"M{sensor}",
                timestamp=stamp,
                pm25_ug_m3=10 + scalar_plume(p, (-400, 0), 5000, 2.3, 270),
                origin="synthetic",
                **point(p),
            )
        )
        met.append(
            Weather(
                timestamp=stamp,
                wind_speed_m_s=2.3,
                wind_from_deg=270,
                origin="synthetic",
                provenance="Synthetic scale fixture",
                **point((200, 0)),
            )
        )
    grid = [
        Point(**point((x, y)))
        for x in [-500, -450, -400, -350, -300]
        for y in [-200, -100, 0, 100, 200]
    ]
    return Investigation(
        name=f"SYNTHETIC scale {size}",
        synthetic=True,
        sites=sites,
        measurements=rows,
        weather=met,
        source_locations=grid,
        assumptions=Assumptions(steady=True, open_terrain=True, local_weather=True),
        settings=Settings(budget=1000, equipment_limit=8),
    )


def main():
    size = int(sys.argv[1])
    # Address-space ceiling is deliberately separate from reported actual RSS.
    ceiling = 2 * 1024**3
    resource.setrlimit(resource.RLIMIT_AS, (ceiling, ceiling))
    before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    started = time.perf_counter()
    inv = scale_case(size)
    result = analyze(inv)
    hwm = next(
        (
            float(line.split()[1]) / 1024
            for line in (
                Path("/proc/self/status").read_text().splitlines()
                if Path("/proc/self/status").exists()
                else []
            )
            if line.startswith("VmHWM:")
        ),
        None,
    )
    print(
        json.dumps(
            {
                "proc_peak_rss_mib": hwm,
                "size": size,
                "measurements": len(inv.measurements),
                "weather_rows": len(inv.weather),
                "sites": len(inv.sites),
                "source_locations": len(inv.source_locations),
                "status": result["status"],
                "scenario_count": result.get("scenario_count"),
                "rows_used": result.get("rows_used"),
                "wall_ms": round((time.perf_counter() - started) * 1000, 2),
                "peak_rss_mib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
                / 1024,
                "incremental_peak_mib": (
                    resource.getrusage(resource.RUSAGE_SELF).ru_maxrss - before
                )
                / 1024,
                "address_space_ceiling_mib": 2048,
                "finite": all(np.isfinite(p["score"]) for p in result["plans"]),
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
