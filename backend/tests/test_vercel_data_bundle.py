from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import tarfile
import tomllib
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from create_test_release import create as create_test_release  # noqa: E402
from package_vercel_bundle import package  # noqa: E402
import prepare_vercel_bundle  # noqa: E402


def test_bundle_archive_is_deterministic_and_contains_only_runtime_data(tmp_path: Path) -> None:
    data_root = tmp_path / "fixture"
    roads_root = data_root / "context" / "osm_roads" / "raw"
    create_test_release(data_root)

    first = package(data_root, tmp_path / "first.tar.gz", roads_root=roads_root, allow_synthetic=True)
    second = package(data_root, tmp_path / "second.tar.gz", roads_root=roads_root, allow_synthetic=True)

    assert first["sha256"] == second["sha256"]
    assert first["members"] == second["members"]
    with tarfile.open(tmp_path / "first.tar.gz", "r:gz") as archive:
        assert len(archive.getmembers()) == 9
        assert all(member.isfile() for member in archive.getmembers())
        assert "release/manifest.json" in archive.getnames()
        assert "osm_roads/raw/durham.osm" in archive.getnames()


def test_remote_stage_checks_archive_digest_and_refuses_synthetic_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    data_root = tmp_path / "deployment-data"
    fixture_root = tmp_path / "fixture"
    roads_root = fixture_root / "context" / "osm_roads" / "raw"
    create_test_release(fixture_root)
    archive_path = tmp_path / "bundle.tar.gz"
    package(fixture_root, archive_path, roads_root=roads_root, allow_synthetic=True)
    archive_sha256 = hashlib.sha256(archive_path.read_bytes()).hexdigest()

    def copy_archive(url: str, destination: Path, token: str | None) -> str:
        assert url == "https://store-id.private.blob.vercel-storage.com/bundle.tar.gz"
        assert token == "test-token"
        destination.write_bytes(archive_path.read_bytes())
        return archive_sha256

    monkeypatch.setattr(prepare_vercel_bundle, "_download", copy_archive)
    with pytest.raises(RuntimeError, match="SHA-256"):
        prepare_vercel_bundle.stage(
            data_root,
            bundle_url="https://store-id.private.blob.vercel-storage.com/bundle.tar.gz",
            expected_sha256="0" * 64,
            token="test-token",
        )
    assert not data_root.exists()

    with pytest.raises(RuntimeError, match="Synthetic test fixture"):
        prepare_vercel_bundle.stage(
            data_root,
            bundle_url="https://store-id.private.blob.vercel-storage.com/bundle.tar.gz",
            expected_sha256=archive_sha256,
            token="test-token",
        )
    assert not data_root.exists()


def test_tar_extraction_rejects_unexpected_and_traversal_members(tmp_path: Path) -> None:
    archive_path = tmp_path / "unsafe.tar.gz"
    with tarfile.open(archive_path, "w:gz") as archive:
        member = tarfile.TarInfo("../../outside.txt")
        member.size = 0
        archive.addfile(member)

    with pytest.raises(RuntimeError, match="missing, duplicate, or unexpected"):
        prepare_vercel_bundle._safe_extract(archive_path, tmp_path / "extract")


def test_vercel_entrypoint_forces_public_mode_and_packaged_paths() -> None:
    environment = os.environ.copy()
    environment["UPWIND_PUBLIC_READONLY"] = "0"
    environment["UPWIND_CORS_ORIGINS"] = "https://explorer.example"
    environment.pop("UPWIND_NATIONAL_RELEASE_DIR", None)
    environment.pop("UPWIND_OSM_ROADS_DIR", None)
    environment["PYTHONPATH"] = str(ROOT / "backend")
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            "import os, sys; from fastapi.testclient import TestClient; from api.index import app; assert os.environ['UPWIND_PUBLIC_READONLY'] == '1'; assert os.environ['UPWIND_NATIONAL_RELEASE_DIR'].endswith('/deployment-data/release'); assert os.environ['UPWIND_OSM_ROADS_DIR'].endswith('/deployment-data/osm_roads/raw'); assert 'upwind.engine' not in sys.modules; c=TestClient(app); p=c.options('/api/health',headers={'Origin':'https://explorer.example','Access-Control-Request-Method':'GET'}); d=c.options('/api/health',headers={'Origin':'https://attacker.example','Access-Control-Request-Method':'GET'}); assert p.status_code == 200 and p.headers.get('access-control-allow-origin') == 'https://explorer.example'; assert d.status_code == 404 and 'access-control-allow-origin' not in d.headers",
        ],
        cwd=ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0


def test_vercel_selects_fastapi_framework_entrypoint_for_all_routes() -> None:
    with (ROOT / "pyproject.toml").open("rb") as source:
        config = tomllib.load(source)

    assert config["tool"]["vercel"]["entrypoint"] == "api.index:app"


def test_vercel_entrypoint_keeps_full_api_route_paths(tmp_path: Path) -> None:
    data_root = tmp_path / "deployment-data"
    create_test_release(data_root)
    environment = os.environ.copy()
    environment["UPWIND_PUBLIC_READONLY"] = "0"
    environment["UPWIND_NATIONAL_RELEASE_DIR"] = str(data_root / "release")
    environment["UPWIND_OSM_ROADS_DIR"] = str(data_root / "context" / "osm_roads" / "raw")
    environment["PYTHONPATH"] = str(ROOT / "backend")
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from fastapi.testclient import TestClient; "
                "from api.index import app; "
                "client = TestClient(app); "
                "places = client.get('/api/national/places', params={'q': 'Durham'}); "
                "assert places.status_code == 200, places.text; "
                "assert places.json()['items'][0]['name'] == 'Durham city'; "
                "assert client.get('/api/demo').status_code == 404"
            ),
        ],
        cwd=ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0


def test_bundle_verifier_rejects_roads_outside_data_root(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    roads_root = tmp_path / "roads"
    create_test_release(data_root)
    with pytest.raises(RuntimeError, match="inside the Vercel data root"):
        from verify_vercel_bundle import verify

        verify(data_root, roads_root=roads_root)


@pytest.mark.parametrize(
    "url",
    (
        "http://store-id.private.blob.vercel-storage.com/bundle.tar.gz",
        "https://attacker.example/bundle.tar.gz",
        "https://user:pass@store-id.private.blob.vercel-storage.com/bundle.tar.gz",
    ),
)
def test_blob_download_refuses_non_private_or_credentialed_urls(url: str, tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="Vercel private Blob HTTPS URL"):
        prepare_vercel_bundle._download(url, tmp_path / "bundle.tar.gz", "secret")
