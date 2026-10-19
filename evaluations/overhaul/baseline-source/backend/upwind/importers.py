"""Lossless raw CSV provenance with explicit row-level validation; no calibration."""

import csv
import hashlib
import io
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import numpy as np
from pydantic import ValidationError
from .models import ImportRequest, ImportRecord, Measurement, Weather

MEASUREMENT_FIELDS = ["sensor_id", "timestamp", "latitude", "longitude", "pm25_ug_m3"]
WEATHER_FIELDS = [
    "timestamp",
    "latitude",
    "longitude",
    "wind_speed_m_s",
    "wind_from_deg",
]


def utc_timestamp(value: str, zone: str) -> str:
    if not value:
        raise ValueError("Missing timestamp")
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        if not zone:
            raise ValueError("Naive timestamp requires a timezone choice")
        tz = ZoneInfo(zone)
        a, b = dt.replace(tzinfo=tz, fold=0), dt.replace(tzinfo=tz, fold=1)
        if a.utcoffset() != b.utcoffset():
            raise ValueError(
                "Ambiguous/nonexistent daylight-saving time; use an explicit UTC offset"
            )
        if a.astimezone(timezone.utc).astimezone(tz).replace(tzinfo=None) != dt:
            raise ValueError("Nonexistent local time; use an explicit UTC offset")
        dt = a
    return dt.astimezone(timezone.utc).isoformat()


def _parse_csv(req: ImportRequest) -> tuple[list, ImportRecord]:
    if req.kind == "measurements" and req.units != "ug/m3":
        raise ValueError(
            "Measurement unit must be ug/m3. Convert explicitly before importing; original remains your responsibility."
        )
    if req.kind == "weather" and req.units != "m/s,degrees-from-north":
        raise ValueError("Weather units must be m/s,degrees-from-north")
    if req.timezone:
        try:
            ZoneInfo(req.timezone)
        except ZoneInfoNotFoundError as e:
            raise ValueError("Unknown IANA timezone") from e
    reader = csv.DictReader(io.StringIO(req.csv.lstrip("\ufeff")), strict=True)
    if reader.fieldnames and len(set(reader.fieldnames)) != len(reader.fieldnames):
        raise ValueError("Duplicate CSV header names are ambiguous")
    required = MEASUREMENT_FIELDS if req.kind == "measurements" else WEATHER_FIELDS
    selected = [req.mapping.get(f, f) for f in required]
    if len(set(selected)) != len(selected):
        raise ValueError("Each required field must map to a different CSV column")
    missing = [
        f for f in required if req.mapping.get(f, f) not in (reader.fieldnames or [])
    ]
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(missing))
    rows, issues, seen, last = [], [], set(), {}
    flagged, count = 0, 0
    for line, raw in enumerate(reader, 2):
        count += 1
        if count > 10000:
            raise ValueError("At most 10,000 rows per import")
        row = {f: raw.get(req.mapping.get(f, f), "") for f in required}
        try:
            if None in raw or any(v is None for v in raw.values()):
                raise ValueError("CSV row width does not match header")
            row["timestamp"] = utc_timestamp(row["timestamp"], req.timezone)
            row["origin"] = raw.get("origin") or raw.get("data_origin") or "user_import"
            for f in required:
                if f not in ("timestamp", "sensor_id"):
                    row[f] = float(row[f])
                    if not np.isfinite(row[f]):
                        raise ValueError(f"{f} must be finite")
            if req.kind == "measurements":
                for f in ["uncertainty_ug_m3", "humidity_percent", "temperature_c"]:
                    val = raw.get(req.mapping.get(f, f))
                    if val not in (None, ""):
                        row[f] = float(val)
                flags = []
                key = (row["sensor_id"], row["timestamp"])
                if key in seen:
                    flags.append("duplicate")
                if (
                    row["sensor_id"] in last
                    and row["timestamp"] < last[row["sensor_id"]]
                ):
                    flags.append("out_of_order")
                if row["pm25_ug_m3"] < 0:
                    flags.append("negative")
                if row["pm25_ug_m3"] > 500:
                    flags.append("extreme_review")
                row["flags"] = flags
                item = Measurement(**row)
                seen.add(key)
                last[row["sensor_id"]] = row["timestamp"]
                flagged += bool(flags)
            else:
                if raw.get("provenance"):
                    row["provenance"] = raw["provenance"]
                item = Weather(**row)
                key = row["timestamp"], row["latitude"], row["longitude"]
                if key in seen:
                    raise ValueError("Duplicate meteorology timestamp and location")
                seen.add(key)
            rows.append(item)
        except (ValueError, TypeError, ValidationError) as e:
            issues.append({"line": line, "error": str(e)[:350]})
    if not count:
        raise ValueError("CSV contains no data rows")
    digest = hashlib.sha256(req.csv.encode()).hexdigest()
    record = ImportRecord(
        id=digest[:16],
        filename=req.filename,
        kind=req.kind,
        sha256=digest,
        raw_csv=req.csv,
        timezone=req.timezone or "explicit offsets",
        column_mapping=req.mapping,
        summary={
            "total": count,
            "accepted": len(rows),
            "invalid": len(issues),
            "flagged": flagged,
            "synthetic_rows": sum(r.origin == "synthetic" for r in rows),
            "issues": issues,
        },
        transformations=[
            "UTF-8 BOM ignored if present",
            "Timestamps normalized to UTC",
            "No smoothing, calibration, or imputation",
            "Invalid rows retained in original CSV; flagged measurement rows retained in table",
        ]
        + (
            [
                "Meteorological direction 360 degrees normalized to equivalent 0 degrees from north"
            ]
            if req.kind == "weather"
            else []
        ),
    )
    return rows, record


def parse_csv(req: ImportRequest) -> tuple[list, ImportRecord]:
    try:
        return _parse_csv(req)
    except csv.Error as e:
        raise ValueError("Malformed CSV: " + str(e)) from e
