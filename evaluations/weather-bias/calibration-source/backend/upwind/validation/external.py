"""Inspect upstream measured data without inventing missing spatial metadata."""

import csv, hashlib, io, subprocess
from pathlib import Path
import pandas as pd
from ..models import ImportRequest
from ..importers import parse_csv

OPENAIR_REVISION = "c2970d8c5addf68497bddaae13230167e7387651"


def external_check(root=Path(".local/stress/external/openair")):
    import pyreadr

    if not root.exists():
        root.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                "git",
                "clone",
                "--no-checkout",
                "https://github.com/openair-project/openair.git",
                str(root),
            ],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(root), "checkout", "--detach", OPENAIR_REVISION],
            check=True,
            capture_output=True,
        )
    revision = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
    ).strip()
    if revision != OPENAIR_REVISION:
        raise ValueError(
            "External checkout revision differs; preserve it and use a separate pinned checkout"
        )
    archive = root / "data/mydata.rda"
    frame = pyreadr.read_r(str(archive), timezone="UTC")["mydata"]
    pm = pd.to_numeric(frame["pm25"], errors="coerce")
    ws = pd.to_numeric(frame["ws"], errors="coerce")
    wd = pd.to_numeric(frame["wd"], errors="coerce")
    # Coordinates are absent from upstream data. Exercise fail-closed import of
    # all records in bounded batches, keeping blanks instead of fabricated sites.
    accepted, invalid, batches = 0, 0, 0
    dates = frame.date.dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    for start in range(0, len(frame), 10000):
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(
            ["sensor_id", "timestamp", "latitude", "longitude", "pm25_ug_m3"]
        )
        for i in range(start, min(start + 10000, len(frame))):
            writer.writerow(["Marylebone-openair", dates.iloc[i], "", "", pm.iloc[i]])
        rows, record = parse_csv(
            ImportRequest(csv=out.getvalue(), filename=f"openair-unlocated-{start}.csv")
        )
        assert record.raw_csv == out.getvalue()
        accepted += len(rows)
        invalid += record.summary["invalid"]
        batches += 1
    valid_pm = pm[pm.notna()]
    return {
        "status": "inspected; spatial inference unavailable",
        "source": "openair mydata / London Air Quality Archive, Marylebone station",
        "repository": "https://github.com/openair-project/openair",
        "revision": revision,
        "data_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "documentation_sha256": hashlib.sha256(
            (root / "man/mydata.Rd").read_bytes()
        ).hexdigest(),
        "columns": list(frame.columns),
        "rows": len(frame),
        "timezone": "UTC via pyreadr timezone=UTC on R POSIXct",
        "start_utc": str(frame.date.min()),
        "end_utc": str(frame.date.max()),
        "duplicate_timestamps": int(frame.date.duplicated().sum()),
        "pm25_observed_rows": int(pm.notna().sum()),
        "pm25_missing_rows": int(pm.isna().sum()),
        "pm25_min": float(pm.min()),
        "pm25_max": float(pm.max()),
        "pm25_quantiles": {
            str(k): float(v) for k, v in pm.quantile([0.5, 0.9, 0.99]).items()
        },
        "first_valid_pm25_utc": str(frame.loc[pm.notna(), "date"].min()),
        "last_valid_pm25_utc": str(frame.loc[pm.notna(), "date"].max()),
        "wind_missing_rows": int((ws.isna() | wd.isna()).sum()),
        "wind_below_model_speed_rows": int((ws < 0.8).sum()),
        "wind_above_model_speed_rows": int((ws > 8).sum()),
        "north_360_rows": int((wd == 360).sum()),
        "unlocated_import_batches": batches,
        "unlocated_import_accepted": accepted,
        "unlocated_import_rejected": invalid,
        "no_coordinates_invented": True,
        "spatial_blocker": "No latitude/longitude columns or independently acquired station metadata; only one site, urban roadside conditions, no known release coordinates/strength/heights. Not compatible source ground truth.",
        "license": "Upstream package MIT; primary London archive data redistribution terms not verified. Raw dataset remains ignored locally; only metadata/statistics committed.",
        "assertions_passed": accepted == 0 and invalid == len(frame),
    }
