"""Independent numerical/constraint and isolated data/API stress batteries."""

import argparse
from collections import Counter
import csv
import hashlib
import io
import json
from pathlib import Path
import time

import numpy as np

from upwind.engine import analyze
from upwind.importers import parse_csv
from upwind.models import ImportRequest
from upwind.validation.api_checks import api_battery
from upwind.validation.engineering import (
    numerical_battery,
    make_placement,
    placement_oracle,
)


def planning():
    records, failures, checks = [], [], 0
    for index in range(200):
        large = index >= 100
        seed = 6200000 + index
        inv = make_placement(seed, large)
        result = analyze(inv)
        for plan in result["plans"]:
            selected = [site for site in inv.sites if site.id in plan["site_ids"]]
            good = (
                len(selected) == len(set(plan["site_ids"]))
                and len(selected) <= inv.settings.equipment_limit
                and sum(s.cost for s in selected) <= inv.settings.budget + 1e-8
                and all(
                    s.kind == "candidate"
                    and s.allowed
                    and s.power
                    and s.access
                    and "steady-window" in s.windows
                    for s in selected
                )
            )
            checks += 1
            if not good:
                failures.append({"seed": seed, "check": "constraints", "plan": plan})
        primary = result["plans"][0]["score"]
        if not large:
            expected, _, _ = placement_oracle(inv)
            checks += 1
            if abs(primary - expected) > 2e-6:
                failures.append(
                    {
                        "seed": seed,
                        "check": "independent exhaustive optimum",
                        "actual": primary,
                        "oracle": expected,
                    }
                )
        inv.sites.reverse()
        permuted = analyze(inv)["plans"][0]["score"]
        checks += 1
        if abs(primary - permuted) > 1e-9:
            failures.append(
                {
                    "seed": seed,
                    "check": "site permutation",
                    "actual": primary,
                    "permuted": permuted,
                }
            )
        records.append(
            {
                "seed": seed,
                "large": large,
                "sites": len(inv.sites),
                "plan_count": len(result["plans"]),
                "primary_score": primary,
            }
        )
    return {
        "instances": records,
        "checks": checks,
        "failures": failures,
        "passed": not failures,
    }


def fuzz():
    rng = np.random.default_rng(6300000)
    failures, counts = [], Counter()
    digest = hashlib.sha256()
    for index in range(5000):
        weather = bool(index % 2)
        headers = (
            ["timestamp", "latitude", "longitude", "wind_speed_m_s", "wind_from_deg"]
            if weather
            else ["sensor_id", "timestamp", "latitude", "longitude", "pm25_ug_m3"]
        ) + ["origin"]
        numbers = [
            "",
            "NaN",
            "Infinity",
            "-Infinity",
            "-1",
            "-0",
            "0",
            "0.8",
            "12",
            "500",
            "501",
            "650",
            "1e309",
            "1e-309",
            "é",
            "=1+1",
            "1,2",
        ]
        stamp = str(
            rng.choice(
                [
                    "2026-01-01T00:00Z",
                    "2026-11-01T01:30",
                    "2026-03-08T02:30",
                    "bad",
                    "2026-06-01T12:00+05:30",
                    "2026-02-30T00:00Z",
                ]
            )
        )
        lat = str(rng.choice(["0", "43", "85", "-85", "90", "NaN", "bad"]))
        lon = str(rng.choice(["0", "-92", "180", "181", "inf"]))
        numeric = [str(rng.choice(numbers)), str(rng.choice(numbers))]
        values = (
            [stamp, lat, lon, *numeric, "synthetic"]
            if weather
            else [
                str(rng.choice(["A", "", "=1+1", "M,quoted", "sensor雪"])),
                stamp,
                lat,
                lon,
                numeric[0],
                "synthetic",
            ]
        )
        mode = int(rng.integers(0, 8))
        if mode == 1:
            values += ["extra"]
        elif mode == 2:
            values = values[:-1]
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(headers)
        writer.writerow(values)
        raw = buffer.getvalue()
        if mode == 3:
            raw = raw.rstrip() + '\n"unfinished'
        elif mode == 4:
            raw = raw.replace("\r\n", "\n")
        digest.update(raw.encode())
        try:
            rows, record = parse_csv(
                ImportRequest(
                    csv=raw,
                    kind="weather" if weather else "measurements",
                    timezone="America/New_York",
                    filename="SYNTHETIC fuzz.csv",
                )
            )
            assert record.raw_csv == raw
            assert record.summary["accepted"] == len(rows)
            assert (
                record.summary["accepted"] + record.summary["invalid"]
                == record.summary["total"]
            )
            counts["parsed"] += 1
            counts["accepted_rows"] += len(rows)
            counts["invalid_rows"] += record.summary["invalid"]
        except ValueError:
            counts["explicit_refusal"] += 1
        except Exception as exc:
            failures.append(
                {
                    "index": index,
                    "raw": raw,
                    "kind": "weather" if weather else "measurements",
                    "exception": f"{type(exc).__name__}: {exc}",
                }
            )
    return {
        "seed": 6300000,
        "cases": 5000,
        "input_stream_sha256": digest.hexdigest(),
        "counts": dict(counts),
        "unexpected_failures": failures,
        "passed": not failures,
        "meaning": "Constructed adversarial inputs; schema refusals are expected. No measured observations.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    begun = time.perf_counter()
    for name, function in [
        ("numerical", lambda: numerical_battery(100000)),
        ("placement", planning),
        ("csv-fuzz", fuzz),
        ("api-rounds", lambda: [api_battery() for _ in range(4)]),
    ]:
        started = time.perf_counter()
        result = function()
        (args.out / (name + ".json")).write_text(
            json.dumps(result, indent=2, allow_nan=False) + "\n"
        )
        print(name, round(time.perf_counter() - started, 2), flush=True)
    (args.out / "completion.json").write_text(
        json.dumps(
            {
                "seconds": time.perf_counter() - begun,
                "script_sha256": hashlib.sha256(
                    Path(__file__).read_bytes()
                ).hexdigest(),
            },
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
