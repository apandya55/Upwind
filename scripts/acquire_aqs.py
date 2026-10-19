"""Validate and retain an EPA hourly88101 archive without source attribution.

Actual EPA access remains blocked here. Contract tests use constructed archives;
no measured-data compatibility or field accuracy is implied. Existing destinations
are never overwritten; use a new --out for each acquisition.
"""

import argparse
import csv
from datetime import date
import hashlib
import io
from itertools import islice
import json
import os
from pathlib import Path
import re
import tempfile
import urllib.request
import zipfile

import numpy as np
import pandas as pd

ADAPTER_VERSION = "aqs-intake-1.0.0"
CSV_CHUNK_ROWS = 100_000
MAX_ARCHIVE_BYTES = 1_500_000_000
MAX_CSV_BYTES = 8_000_000_000
REQUIRED = {
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
    "Parameter Code",
    "Sample Duration",
    "Datum",
}


def sha256(path):
    with Path(path).open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def validate_selection(state, start, end):
    if not re.fullmatch(r"[0-9]{1,2}", state) or int(state) == 0:
        raise ValueError("State must be a nonzero one/two-digit AQS code")
    try:
        if any(
            not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", s) for s in (start, end)
        ):
            raise ValueError()
        begin, finish = date.fromisoformat(start), date.fromisoformat(end)
    except ValueError as exc:
        raise ValueError("Dates must be valid YYYY-MM-DD calendar dates") from exc
    if begin > finish:
        raise ValueError("Start date must not follow end date")
    return state.zfill(2)


def require_new(path):
    # lexists also protects broken symlinks; link() enforces this at publication.
    if os.path.lexists(path):
        raise FileExistsError(f"Destination already exists; choose a new path: {path}")


def publish_new(staged, destination):
    # Same-filesystem exclusive hard link: complete bytes or no new destination.
    # Unlike replace(), it cannot destroy a file created by another converter.
    os.link(staged, destination)


def _identifiers(series, width, label):
    if not series.str.fullmatch(r"[0-9]{1," + str(width) + "}").all():
        raise ValueError(f"Invalid {label}: expected up to {width} decimal digits")
    if (series.astype(int) == 0).any():
        raise ValueError(f"Invalid {label}: zero is not a station identifier")
    return series.str.zfill(width)


def csv_chunks(member, header):
    # Validate width before constructing a frame: pandas can otherwise interpret
    # an extra field as an index or fill a short record with invented blanks.
    reader = csv.reader(
        io.TextIOWrapper(member, encoding="utf-8-sig", newline=""), strict=True
    )
    if next(reader, None) != header:
        raise ValueError("CSV header changed while reading")
    while rows := list(islice(reader, CSV_CHUNK_ROWS)):
        if any(len(row) != len(header) for row in rows):
            raise ValueError("CSV record width does not match the header")
        yield pd.DataFrame(rows, columns=header)


def convert(archive: Path, output: Path, state: str, start: str, end: str, url: str):
    state = validate_selection(state, start, end)
    archive, output = Path(archive), Path(output)
    sidecar = output.with_suffix(".provenance.json")
    if (
        output.resolve() == archive.resolve()
        or sidecar.resolve() == archive.resolve()
        or sidecar == output
    ):
        raise ValueError("Archive, CSV and provenance require distinct paths")
    require_new(output)
    require_new(sidecar)
    if archive.stat().st_size > MAX_ARCHIVE_BYTES:
        raise ValueError("Archive exceeds1.5GB intake limit")
    original_hash = sha256(archive)
    output.parent.mkdir(parents=True, exist_ok=True)
    total, negative, extreme, qualified = 0, 0, 0, 0
    with tempfile.TemporaryDirectory(
        prefix=".aqs-intake-", dir=output.parent
    ) as directory:
        staged = Path(directory) / "observations.csv"
        staged_meta = Path(directory) / "provenance.json"
        with zipfile.ZipFile(archive) as source:
            names = [n for n in source.namelist() if n.lower().endswith(".csv")]
            if len(names) != 1:
                raise ValueError("Expected a single official hourly AQS CSV in archive")
            info = source.getinfo(names[0])
            if info.file_size > MAX_CSV_BYTES:
                raise ValueError("Uncompressed archive exceeds8GB intake limit")
            with source.open(names[0]) as member:
                header_bytes = member.readline(131_073)
            if len(header_bytes) > 131_072:
                raise ValueError("CSV header exceeds128KiB")
            header = next(
                csv.reader(io.StringIO(header_bytes.decode("utf-8-sig")), strict=True),
                [],
            )
            if len(header) != len(set(header)) or any(not name for name in header):
                raise ValueError("CSV headers must be unique and nonempty")
            if missing := REQUIRED - set(header):
                raise ValueError(f"Incompatible AQS schema: {sorted(missing)}")
            with source.open(names[0]) as member:
                for chunk in csv_chunks(member, header):
                    if not chunk["State Code"].str.fullmatch(r"[0-9]{1,2}").all():
                        raise ValueError("Invalid State Code in archive")
                    part = chunk[chunk["State Code"].str.zfill(2) == state].copy()
                    if part.empty:
                        continue
                    if (
                        not part["Date GMT"]
                        .str.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
                        .all()
                    ):
                        raise ValueError("Invalid Date GMT in requested state")
                    pd.to_datetime(part["Date GMT"], format="%Y-%m-%d", errors="raise")
                    part = part[
                        (part["Date GMT"] >= start) & (part["Date GMT"] <= end)
                    ].copy()
                    if part.empty:
                        continue
                    if (
                        not part["Units of Measure"]
                        .eq("Micrograms/cubic meter (LC)")
                        .all()
                    ):
                        raise ValueError(
                            "Unsupported AQS units: only local-conditions µg/m³ accepted; no implicit conversion"
                        )
                    for field, expected in [
                        ("Parameter Code", "88101"),
                        ("Sample Duration", "1 HOUR"),
                        ("Datum", "WGS84"),
                    ]:
                        if not part[field].eq(expected).all():
                            raise ValueError(
                                f"Unsupported {field}: requires {expected}; no implicit transformation"
                            )
                    if (
                        not part["Time GMT"]
                        .str.fullmatch(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]")
                        .all()
                    ):
                        raise ValueError("Invalid Time GMT: expected24-hour HH:MM")
                    times = pd.to_datetime(
                        part["Date GMT"] + "T" + part["Time GMT"] + ":00Z",
                        format="%Y-%m-%dT%H:%M:%SZ",
                        utc=True,
                        errors="raise",
                    )
                    numeric = part[
                        ["Latitude", "Longitude", "Sample Measurement"]
                    ].apply(pd.to_numeric, errors="raise")
                    if not np.isfinite(numeric.to_numpy()).all():
                        raise ValueError(
                            "Coordinates and concentrations must be finite"
                        )
                    if (
                        not numeric["Latitude"].between(-85, 85).all()
                        or not numeric["Longitude"].between(-180, 180).all()
                    ):
                        raise ValueError(
                            "Coordinates outside the supported WGS84 range"
                        )
                    county = _identifiers(part["County Code"], 3, "County Code")
                    site = _identifiers(part["Site Num"], 4, "Site Num")
                    poc = _identifiers(part["POC"], 2, "POC").str.lstrip("0")
                    qualifiers = (
                        part["Qualifier"]
                        if "Qualifier" in part
                        else pd.Series("", index=part.index)
                    )
                    result = pd.DataFrame(
                        {
                            "sensor_id": state
                            + "-"
                            + county
                            + "-"
                            + site
                            + "-POC"
                            + poc,
                            "timestamp": times.dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                            "latitude": numeric["Latitude"],
                            "longitude": numeric["Longitude"],
                            "pm25_ug_m3": numeric["Sample Measurement"],
                            "origin": "user_import",
                            "source_url": url,
                            "source_units": part["Units of Measure"],
                            "aqs_qualifier": qualifiers,
                            "source_datum": part["Datum"],
                            "source_parameter_code": part["Parameter Code"],
                            "source_sample_duration": part["Sample Duration"],
                        }
                    )
                    # Preserve declared method/instrument distinctions for review.
                    for field in [
                        "Method Code",
                        "Method Name",
                        "Uncertainty",
                        "Date Local",
                        "Time Local",
                    ]:
                        if field in part:
                            result["aqs_" + field.lower().replace(" ", "_")] = part[
                                field
                            ]
                    result.to_csv(staged, index=False, mode="a", header=total == 0)
                    total += len(result)
                    negative += int((numeric["Sample Measurement"] < 0).sum())
                    extreme += int((numeric["Sample Measurement"] > 500).sum())
                    qualified += int(qualifiers.ne("").sum())
        if not total:
            raise ValueError(
                "No rows in requested state/date range; no synthetic fallback"
            )
        if sha256(archive) != original_hash:
            raise ValueError("Archive changed during conversion; no output published")
        metadata = {
            "adapter_version": ADAPTER_VERSION,
            "adapter_sha256": sha256(Path(__file__)),
            "source_url": url,
            "archive_sha256": original_hash,
            "archive_member": names[0],
            "archive_member_bytes": info.file_size,
            "output_csv_sha256": sha256(staged),
            "rows": total,
            "state": state,
            "start": start,
            "end": end,
            "quality_review_counts": {
                "negative": negative,
                "above_500_ug_m3": extreme,
                "qualified": qualified,
            },
            "transformations": [
                "Filtered requested state and inclusive UTC date range",
                "Built instrument ID from state/county/site/POC",
                "Combined Date GMT and Time GMT as UTC; no invented timestamps",
                "Required88101,1 HOUR, WGS84 and local-conditionµg/m³; no unit or datum conversion",
                "Preserved negative/extreme readings and qualifiers for review; no calibration, smoothing or imputation",
            ],
            "evidence": "Archive intake only. Provenance URL is a caller claim, not verified EPA authenticity. No source truth or weather supplied; not a field-localization or accuracy evaluation.",
            "publication": "Both files must exist and the CSV hash must match this sidecar. Existing destinations are never overwritten.",
        }
        staged_meta.write_text(json.dumps(metadata, indent=2) + "\n")
        # Sidecar reserves this basename. CSV appears only after all checks pass.
        publish_new(staged_meta, sidecar)
        try:
            publish_new(staged, output)
        except BaseException:
            # Remove only our own sidecar, never a concurrently replaced file.
            if sidecar.exists() and os.path.samefile(staged_meta, sidecar):
                sidecar.unlink()
            raise
    return metadata


def download(url, archive):
    archive = Path(archive)
    require_new(archive)
    archive.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=".aqs-download-", dir=archive.parent
    ) as directory:
        staged = Path(directory) / "archive.zip"
        with (
            urllib.request.urlopen(url, timeout=30) as response,
            staged.open("wb") as out,
        ):
            size = 0
            while data := response.read(1024 * 1024):
                size += len(data)
                if size > MAX_ARCHIVE_BYTES:
                    raise ValueError(
                        "Download exceeds1.5GB; obtain a bounded subset independently"
                    )
                out.write(data)
        with zipfile.ZipFile(staged) as source:
            if sum(info.file_size for info in source.infolist()) > MAX_CSV_BYTES:
                raise ValueError("Downloaded archive exceeds8GB uncompressed limit")
            if source.testzip() is not None:
                raise ValueError("Downloaded archive failed CRC verification")
        publish_new(staged, archive)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, default=2024, choices=range(2000, 2027))
    parser.add_argument("--state", default="37")
    parser.add_argument("--start", default="2024-06-01")
    parser.add_argument("--end", default="2024-06-01")
    parser.add_argument("--archive", type=Path)
    parser.add_argument(
        "--download",
        action="store_true",
        help="Explicit potentially large official download; TLS verification retained",
    )
    parser.add_argument("--out", type=Path, default=Path(".local/aqs-pm25.csv"))
    args = parser.parse_args()
    validate_selection(args.state, args.start, args.end)
    if any(date.fromisoformat(s).year != args.year for s in (args.start, args.end)):
        parser.error("--start/--end must match the requested --year archive")
    require_new(args.out)
    require_new(args.out.with_suffix(".provenance.json"))
    url = f"https://aqs.epa.gov/aqsweb/airdata/hourly_88101_{args.year}.zip"
    archive = args.archive or Path(f".local/hourly_88101_{args.year}.zip")
    if args.download:
        download(url, archive)
    if not archive.exists():
        parser.error(
            "Provide --archive or explicitly use --download. No data generated."
        )
    print(
        json.dumps(
            convert(archive, args.out, args.state, args.start, args.end, url), indent=2
        )
    )


if __name__ == "__main__":
    main()
