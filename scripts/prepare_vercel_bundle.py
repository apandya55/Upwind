#!/usr/bin/env python3
"""Stage and verify the immutable data bundle for a Vercel API build.

Builds use an existing local ``deployment-data`` directory when present. A
clean Vercel checkout can instead fetch a pre-approved private archive by
setting ``UPWIND_VERCEL_BUNDLE_URL`` and its SHA-256 in
``UPWIND_VERCEL_BUNDLE_SHA256``. The URL must be HTTPS; the optional bearer
token is read from ``VERCEL_OIDC_TOKEN``, ``UPWIND_VERCEL_BUNDLE_TOKEN`` or
``BLOB_READ_WRITE_TOKEN`` and is never printed.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import tarfile
import tempfile
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener
from urllib.parse import urlsplit

from verify_vercel_bundle import MAX_DATA_BYTES, RELEASE_FILES, ROAD_FILES, verify


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = ROOT / "deployment-data"
MAX_DOWNLOAD_BYTES = MAX_DATA_BYTES


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        raise RuntimeError("Vercel data archive redirects are refused")


def _download(url: str, destination: Path, token: str | None) -> str:
    parsed_url = urlsplit(url)
    hostname = (parsed_url.hostname or "").lower()
    if (
        parsed_url.scheme.lower() != "https"
        or parsed_url.username is not None
        or parsed_url.password is not None
        or parsed_url.port not in (None, 443)
        or not hostname.endswith(".private.blob.vercel-storage.com")
    ):
        raise RuntimeError("UPWIND_VERCEL_BUNDLE_URL must be a Vercel private Blob HTTPS URL")
    request = Request(url, headers={"Accept": "application/gzip, application/octet-stream"})
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    digest = hashlib.sha256()
    total = 0
    try:
        with build_opener(_NoRedirect).open(request, timeout=60) as response, destination.open("wb") as output:
            while True:
                block = response.read(1024 * 1024)
                if not block:
                    break
                total += len(block)
                if total > MAX_DOWNLOAD_BYTES:
                    raise RuntimeError(f"Vercel data archive exceeds {MAX_DOWNLOAD_BYTES} bytes")
                digest.update(block)
                output.write(block)
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"Unable to retrieve Vercel data archive: {exc}") from exc
    return digest.hexdigest()


def _safe_extract(archive_path: Path, destination: Path) -> None:
    with tarfile.open(archive_path, mode="r:*") as archive:
        members = archive.getmembers()
        expected = {f"release/{name}" for name in RELEASE_FILES} | {f"osm_roads/raw/{name}" for name in ROAD_FILES}
        actual = [member.name for member in members]
        if len(actual) != len(set(actual)) or set(actual) != expected:
            raise RuntimeError("Vercel data archive has missing, duplicate, or unexpected files")
        if sum(member.size for member in members) > MAX_DATA_BYTES:
            raise RuntimeError(f"Vercel data archive expands beyond {MAX_DATA_BYTES} bytes")
        for member in members:
            target = (destination / member.name).resolve()
            if target != destination.resolve() and destination.resolve() not in target.parents:
                raise RuntimeError(f"Vercel data archive contains an unsafe path: {member.name}")
            if member.issym() or member.islnk() or member.isdev() or not member.isfile():
                raise RuntimeError(f"Vercel data archive contains unsupported member: {member.name}")
        archive.extractall(destination, filter="data")


def stage(data_root: Path, *, bundle_url: str | None, expected_sha256: str | None, token: str | None) -> dict[str, object]:
    data_root = data_root.expanduser().resolve()
    if (data_root / "release" / "manifest.json").is_file():
        result = verify(data_root)
        result["source"] = "local"
        return result
    if not bundle_url:
        raise RuntimeError(
            f"Missing production data bundle at {data_root}. Set UPWIND_VERCEL_BUNDLE_URL and "
            "UPWIND_VERCEL_BUNDLE_SHA256 for a clean Vercel build."
        )
    if not expected_sha256 or len(expected_sha256) != 64 or any(char not in "0123456789abcdef" for char in expected_sha256.lower()):
        raise RuntimeError("UPWIND_VERCEL_BUNDLE_SHA256 must be a 64-character SHA-256 digest")

    with tempfile.TemporaryDirectory(prefix="upwind-vercel-bundle-") as temporary:
        temporary_root = Path(temporary)
        archive_path = temporary_root / "bundle.tar.gz"
        actual_sha256 = _download(bundle_url, archive_path, token)
        if actual_sha256 != expected_sha256.lower():
            raise RuntimeError("Vercel data archive SHA-256 does not match UPWIND_VERCEL_BUNDLE_SHA256")
        extracted = temporary_root / "extracted"
        extracted.mkdir()
        _safe_extract(archive_path, extracted)
        verify(extracted)
        data_root.parent.mkdir(parents=True, exist_ok=True)
        staged = data_root.with_name(f".{data_root.name}.staged")
        shutil.rmtree(staged, ignore_errors=True)
        shutil.copytree(extracted, staged)
        try:
            data_root.mkdir(parents=True, exist_ok=True)
            for child in staged.iterdir():
                target = data_root / child.name
                if target.exists():
                    shutil.rmtree(target) if target.is_dir() else target.unlink()
                shutil.move(str(child), str(target))
        finally:
            shutil.rmtree(staged, ignore_errors=True)
    result = verify(data_root)
    result["source"] = "https"
    result["archive_sha256"] = actual_sha256
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    args = parser.parse_args()
    result = stage(
        args.data_root,
        bundle_url=os.environ.get("UPWIND_VERCEL_BUNDLE_URL"),
        expected_sha256=os.environ.get("UPWIND_VERCEL_BUNDLE_SHA256"),
        token=(
            os.environ.get("VERCEL_OIDC_TOKEN")
            or os.environ.get("UPWIND_VERCEL_BUNDLE_TOKEN")
            or os.environ.get("BLOB_READ_WRITE_TOKEN")
        ),
    )
    print(result)


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, tarfile.TarError) as exc:
        raise SystemExit(f"ERROR: {exc}") from exc
