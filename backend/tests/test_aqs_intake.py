"""Constructed schema and fault tests only; no measured EPA archive is bundled."""

import concurrent.futures
import csv
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import zipfile

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/acquire_aqs.py"


@pytest.fixture
def adapter():
    spec = importlib.util.spec_from_file_location("aqs_intake", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def observation(**changes):
    row = {
        "State Code": "37",
        "County Code": "183",
        "Site Num": "0014",
        "POC": "1",
        "Date GMT": "2024-06-01",
        "Time GMT": "12:00",
        "Latitude": "35.7",
        "Longitude": "-78.6",
        "Sample Measurement": "10",
        "Units of Measure": "Micrograms/cubic meter (LC)",
        "Parameter Code": "88101",
        "Sample Duration": "1 HOUR",
        "Datum": "WGS84",
        "Qualifier": "",
        "Method Code": "170",
        "Method Name": "declared instrument",
        "Uncertainty": "1.5",
        "Date Local": "2024-06-01",
        "Time Local": "08:00",
    }
    row.update(changes)
    return row


def archive_at(path, rows):
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("hourly_88101_2024.csv", stream.getvalue())
    return path


def convert(adapter, archive, output, **kwargs):
    return adapter.convert(
        archive,
        output,
        kwargs.get("state", "37"),
        kwargs.get("start", "2024-06-01"),
        kwargs.get("end", "2024-06-01"),
        "https://aqs.epa.gov/constructed-contract-only",
    )


def test_measured_intake_preserves_values_metadata_and_quality(adapter, tmp_path):
    rows = [
        observation(),
        observation(
            **{"Time GMT": "13:00", "Sample Measurement": "-3", "Qualifier": "QA"}
        ),
        observation(**{"Time GMT": "14:00", "Sample Measurement": "501"}),
    ]
    archive = archive_at(tmp_path / "contract.zip", rows)
    before = archive.read_bytes()
    output = tmp_path / "out.csv"
    metadata = convert(adapter, archive, output)
    records = list(csv.DictReader(io.StringIO(output.read_text())))
    assert [float(r["pm25_ug_m3"]) for r in records] == [10, -3, 501]
    assert records[0]["timestamp"] == "2024-06-01T12:00:00Z"
    assert records[0]["sensor_id"] == "37-183-0014-POC1"
    assert records[1]["aqs_qualifier"] == "QA"
    assert records[0]["aqs_method_code"] == "170"
    assert records[0]["aqs_uncertainty"] == "1.5"
    assert all(r["origin"] == "user_import" for r in records)
    assert (
        metadata["output_csv_sha256"] == hashlib.sha256(output.read_bytes()).hexdigest()
    )
    assert metadata["archive_sha256"] == hashlib.sha256(before).hexdigest()
    assert archive.read_bytes() == before
    assert metadata["quality_review_counts"] == {
        "negative": 1,
        "above_500_ug_m3": 1,
        "qualified": 1,
    }
    assert json.loads(output.with_suffix(".provenance.json").read_text()) == metadata


@pytest.mark.parametrize(
    "field,value",
    [
        ("Date GMT", "2024-02-30"),
        ("Date GMT", "2024-6-01"),
        ("Time GMT", "24:00"),
        ("Latitude", "NaN"),
        ("Latitude", "86"),
        ("Longitude", "181"),
        ("Sample Measurement", "inf"),
        ("Sample Measurement", ""),
        ("County Code", "18.3"),
        ("Site Num", "0"),
        ("POC", "1.0"),
        ("Parameter Code", "88502"),
        ("Sample Duration", "24 HOUR"),
        ("Datum", "NAD83"),
        ("Units of Measure", "Parts per billion"),
    ],
)
def test_invalid_or_incompatible_rows_publish_nothing(adapter, tmp_path, field, value):
    archive = archive_at(tmp_path / "contract.zip", [observation(**{field: value})])
    output = tmp_path / "out.csv"
    with pytest.raises(ValueError):
        convert(adapter, archive, output)
    assert not output.exists() and not output.with_suffix(".provenance.json").exists()
    assert not list(tmp_path.glob(".aqs-intake-*"))


def test_late_chunk_failure_is_not_a_partial_export(adapter, tmp_path, monkeypatch):
    monkeypatch.setattr(adapter, "CSV_CHUNK_ROWS", 1)
    archive = archive_at(
        tmp_path / "contract.zip", [observation(), observation(**{"Datum": "NAD83"})]
    )
    output = tmp_path / "out.csv"
    with pytest.raises(ValueError, match="Datum"):
        convert(adapter, archive, output)
    assert not output.exists() and not output.with_suffix(".provenance.json").exists()
    assert not list(tmp_path.glob(".aqs-intake-*"))


@pytest.mark.parametrize("existing", ["csv", "provenance", "broken-symlink"])
def test_existing_destination_survives_even_bad_archive(adapter, tmp_path, existing):
    archive = tmp_path / "bad.zip"
    archive.write_bytes(b"invalid archive")
    output = tmp_path / "out.csv"
    protected = (
        output if existing != "provenance" else output.with_suffix(".provenance.json")
    )
    if existing == "broken-symlink":
        protected.symlink_to(tmp_path / "absent")
    else:
        protected.write_bytes(b"previous good data")
    with pytest.raises(FileExistsError):
        convert(adapter, archive, output)
    assert (
        protected.is_symlink()
        if existing == "broken-symlink"
        else protected.read_bytes() == b"previous good data"
    )


def test_concurrent_converters_publish_one_consistent_pair(adapter, tmp_path):
    archives = [
        archive_at(
            tmp_path / f"contract{i}.zip",
            [observation(**{"Sample Measurement": str(i + 10)})],
        )
        for i in range(2)
    ]
    output = tmp_path / "out.csv"

    def run(archive):
        try:
            return convert(adapter, archive, output)
        except FileExistsError:
            return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, archives))
    assert sum(r is not None for r in results) == 1
    metadata = json.loads(output.with_suffix(".provenance.json").read_text())
    assert (
        metadata["output_csv_sha256"] == hashlib.sha256(output.read_bytes()).hexdigest()
    )
    assert metadata == next(r for r in results if r is not None)
    assert not list(tmp_path.glob(".aqs-intake-*"))


def test_publication_error_rolls_back_only_new_provenance(
    adapter, tmp_path, monkeypatch
):
    archive = archive_at(tmp_path / "contract.zip", [observation()])
    output = tmp_path / "out.csv"
    original = adapter.publish_new

    def fail_csv(source, destination):
        if destination == output:
            raise OSError("simulated storage failure")
        return original(source, destination)

    monkeypatch.setattr(adapter, "publish_new", fail_csv)
    with pytest.raises(OSError, match="storage failure"):
        convert(adapter, archive, output)
    assert not output.exists() and not output.with_suffix(".provenance.json").exists()


@pytest.mark.parametrize(
    "selection", [{"start": "2024-06-02"}, {"state": "37.0"}, {"end": "2024-02-30"}]
)
def test_invalid_selection_is_refused_without_files(adapter, tmp_path, selection):
    archive = archive_at(tmp_path / "contract.zip", [observation()])
    with pytest.raises(ValueError):
        convert(adapter, archive, tmp_path / "out.csv", **selection)
    assert not (tmp_path / "out.csv").exists()


def test_selection_inclusive_utc_and_no_row_invention(adapter, tmp_path):
    archive = archive_at(
        tmp_path / "contract.zip",
        [
            observation(),
            observation(**{"State Code": "36"}),
            observation(**{"Date GMT": "2024-06-02"}),
        ],
    )
    output = tmp_path / "out.csv"
    assert convert(adapter, archive, output)["rows"] == 1
    with pytest.raises(ValueError, match="No rows"):
        convert(adapter, archive, tmp_path / "empty.csv", state="01")
    assert not (tmp_path / "empty.csv").exists()


def test_duplicate_headers_and_multiple_members_are_refused(adapter, tmp_path):
    for index, (name, text) in enumerate(
        [("sample.csv", "State Code,State Code\n37,37\n"), ("second.csv", "x\n1\n")]
    ):
        archive = tmp_path / f"bad{index}.zip"
        with zipfile.ZipFile(archive, "w") as source:
            source.writestr(name, text)
            if index:
                source.writestr("first.csv", "x\n2\n")
        with pytest.raises(ValueError):
            convert(adapter, archive, tmp_path / f"out{index}.csv")


def test_cli_failure_preserves_existing_csv_and_sidecar(tmp_path):
    output = tmp_path / "existing.csv"
    sidecar = output.with_suffix(".provenance.json")
    output.write_bytes(b"good observations")
    sidecar.write_bytes(b"good provenance")
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--archive",
            str(tmp_path / "missing.zip"),
            "--out",
            str(output),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert output.read_bytes() == b"good observations"
    assert sidecar.read_bytes() == b"good provenance"


@pytest.mark.parametrize("extra", [True, False])
def test_record_width_is_not_silently_repaired(adapter, tmp_path, extra):
    archive = archive_at(tmp_path / "contract.zip", [observation()])
    with zipfile.ZipFile(archive) as source:
        lines = source.read(source.namelist()[0]).decode().splitlines()
    row = next(csv.reader([lines[1]]))
    if extra:
        row.append("unexpected")
    else:
        row.pop()
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow(next(csv.reader([lines[0]])))
    writer.writerow(row)
    with zipfile.ZipFile(archive, "w") as source:
        source.writestr("sample.csv", stream.getvalue())
    with pytest.raises(ValueError, match="width"):
        convert(adapter, archive, tmp_path / "out.csv")
    assert not (tmp_path / "out.csv").exists()


def test_archive_change_during_conversion_publishes_nothing(
    adapter, tmp_path, monkeypatch
):
    archive = archive_at(tmp_path / "contract.zip", [observation()])
    original = adapter.sha256
    calls = []

    def changed(path):
        if path == archive:
            calls.append(path)
            if len(calls) == 2:
                return "different archive"
        return original(path)

    monkeypatch.setattr(adapter, "sha256", changed)
    with pytest.raises(ValueError, match="changed during"):
        convert(adapter, archive, tmp_path / "out.csv")
    assert not (tmp_path / "out.csv").exists()


@pytest.mark.parametrize("mode", ["valid", "invalid_zip", "too_large", "interrupted"])
def test_download_is_bounded_and_publishes_only_complete_zip(
    adapter, tmp_path, monkeypatch, mode
):
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as source:
        source.writestr("sample.csv", "constructed download only")
    data = payload.getvalue() if mode != "invalid_zip" else b"not a zip"

    class Response(io.BytesIO):
        def read(self, size=-1):
            if mode == "interrupted":
                raise OSError("connection lost")
            return super().read(size)

    monkeypatch.setattr(
        adapter.urllib.request, "urlopen", lambda *args, **kwargs: Response(data)
    )
    if mode == "too_large":
        monkeypatch.setattr(adapter, "MAX_ARCHIVE_BYTES", 4)
    archive = tmp_path / "archive.zip"
    if mode == "valid":
        adapter.download("https://aqs.epa.gov/constructed-only", archive)
        assert archive.read_bytes() == data
    else:
        with pytest.raises((ValueError, zipfile.BadZipFile, OSError)):
            adapter.download("https://aqs.epa.gov/constructed-only", archive)
        assert not archive.exists()
    assert not list(tmp_path.glob(".aqs-download-*"))


def test_download_preserves_preexisting_archive_without_network(
    adapter, tmp_path, monkeypatch
):
    archive = tmp_path / "archive.zip"
    archive.write_bytes(b"previous archive")

    def forbidden(*args, **kwargs):
        pytest.fail("Existing archive must be refused before downloading")

    monkeypatch.setattr(adapter.urllib.request, "urlopen", forbidden)
    with pytest.raises(FileExistsError):
        adapter.download("https://aqs.epa.gov/constructed-only", archive)
    assert archive.read_bytes() == b"previous archive"
