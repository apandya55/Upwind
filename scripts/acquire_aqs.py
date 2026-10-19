"""EPA AQS hourly PM2.5 adapter; no source attribution. Original archive retained.

Acquisition is unverified here: aqs.epa.gov CONNECT was denied with HTTP 403.
Run with --archive for an independently acquired official hourly_88101 CSV zip.
Never substitutes generated readings when acquisition fails.
"""

import argparse
import hashlib
import json
from pathlib import Path
import urllib.request
import zipfile
import pandas as pd


def convert(archive: Path, output: Path, state: str, start: str, end: str, url: str):
    output.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    output.unlink(missing_ok=True)
    with zipfile.ZipFile(archive) as z:
        names = [n for n in z.namelist() if n.endswith(".csv")]
        if len(names) != 1:
            raise ValueError("Expected a single official hourly AQS CSV in archive")
        if z.getinfo(names[0]).file_size > 8_000_000_000:
            raise ValueError("Uncompressed archive exceeds 8 GB safety limit")
        with z.open(names[0]) as f:
            for chunk in pd.read_csv(
                f,
                chunksize=100000,
                dtype={
                    "State Code": str,
                    "County Code": str,
                    "Site Num": str,
                    "POC": str,
                },
            ):
                required = [
                    "Date GMT",
                    "Time GMT",
                    "Sample Measurement",
                    "Units of Measure",
                    "State Code",
                    "County Code",
                    "Site Num",
                    "POC",
                    "Latitude",
                    "Longitude",
                ]
                missing = set(required) - set(chunk.columns)
                if missing:
                    raise ValueError(f"Incompatible AQS schema: {sorted(missing)}")
                part = chunk[
                    (chunk["State Code"].str.zfill(2) == state.zfill(2))
                    & (chunk["Date GMT"] >= start)
                    & (chunk["Date GMT"] <= end)
                ].copy()
                if part.empty:
                    continue
                if not part["Units of Measure"].eq("Micrograms/cubic meter (LC)").all():
                    raise ValueError(
                        "Unsupported AQS units: only local-conditions µg/m³ accepted; no implicit conversion"
                    )
                result = pd.DataFrame(
                    {
                        "sensor_id": part["State Code"].str.zfill(2)
                        + "-"
                        + part["County Code"].str.zfill(3)
                        + "-"
                        + part["Site Num"].str.zfill(4)
                        + "-POC"
                        + part["POC"],
                        "timestamp": part["Date GMT"] + "T" + part["Time GMT"] + ":00Z",
                        "latitude": part["Latitude"],
                        "longitude": part["Longitude"],
                        "pm25_ug_m3": part["Sample Measurement"],
                        "source_url": url,
                        "source_units": part["Units of Measure"],
                        "aqs_qualifier": part.get("Qualifier", ""),
                    }
                )
                result.to_csv(output, index=False, mode="a", header=total == 0)
                total += len(result)
    if not total:
        raise ValueError("No rows in requested state/date range; no synthetic fallback")
    digest = hashlib.file_digest(archive.open("rb"), "sha256").hexdigest()
    metadata = {
        "source_url": url,
        "archive_sha256": digest,
        "rows": total,
        "state": state,
        "start": start,
        "end": end,
        "transformations": [
            "Filtered requested state and UTC date range",
            "Built instrument ID from state/county/site/POC",
            "Combined Date GMT and Time GMT as UTC; no invented timestamps",
            "No calibration, smoothing, imputation or rescaling",
        ],
        "evidence": "Actual external data only if acquisition and conversion succeed. Use for exploration and spatial design; known sources not supplied. AQS qualifiers require review.",
    }
    output.with_suffix(".provenance.json").write_text(
        json.dumps(metadata, indent=2) + "\n"
    )
    return metadata


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--year", type=int, default=2024, choices=range(2000, 2027))
    p.add_argument("--state", default="37")
    p.add_argument("--start", default="2024-06-01")
    p.add_argument("--end", default="2024-06-01")
    p.add_argument("--archive", type=Path)
    p.add_argument(
        "--download",
        action="store_true",
        help="Download potentially large official archive; TLS verification retained",
    )
    p.add_argument("--out", type=Path, default=Path(".local/aqs-pm25.csv"))
    args = p.parse_args()
    url = f"https://aqs.epa.gov/aqsweb/airdata/hourly_88101_{args.year}.zip"
    archive = args.archive or Path(f".local/hourly_88101_{args.year}.zip")
    if args.download:
        archive.parent.mkdir(parents=True, exist_ok=True)
        temporary = archive.with_suffix(".download")
        try:
            with (
                urllib.request.urlopen(url, timeout=60) as res,
                temporary.open("wb") as out,
            ):
                size = 0
                while data := res.read(1024 * 1024):
                    size += len(data)
                    if size > 1_500_000_000:
                        raise ValueError(
                            "Download exceeds 1.5 GB; obtain a bounded subset independently"
                        )
                    out.write(data)
            temporary.replace(archive)
        finally:
            temporary.unlink(missing_ok=True)
    if not archive.exists():
        p.error("Provide --archive or explicitly use --download. No data generated.")
    try:
        print(
            json.dumps(
                convert(archive, args.out, args.state, args.start, args.end, url),
                indent=2,
            )
        )
    except Exception:
        args.out.unlink(missing_ok=True)
        raise


if __name__ == "__main__":
    main()
