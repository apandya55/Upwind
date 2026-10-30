#!/usr/bin/env python3
"""Create a deterministic archive containing the public Vercel data bundle.

The archive contains only the files required by the read-only National API.
It is intended for an approved private artifact store, not for committing
upstream data to the source repository.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import tarfile
from pathlib import Path

from verify_vercel_bundle import RELEASE_FILES, ROAD_FILES, verify


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = ROOT / "deployment-data"
DEFAULT_OUTPUT = ROOT / ".local" / "vercel-data-bundle.tar.gz"


def _files(data_root: Path, roads_root: Path) -> list[tuple[Path, str]]:
    return [
        *((data_root / "release" / name, f"release/{name}") for name in RELEASE_FILES),
        *((roads_root / name, f"osm_roads/raw/{name}") for name in ROAD_FILES),
    ]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def package(data_root: Path, output: Path, *, roads_root: Path | None = None, allow_synthetic: bool = False) -> dict[str, object]:
    data_root = data_root.expanduser().resolve()
    roads_root = (roads_root or data_root / "osm_roads" / "raw").expanduser().resolve()
    verification = verify(data_root, roads_root=roads_root, allow_synthetic=allow_synthetic)
    members = _files(data_root, roads_root)
    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    # Fixed tar metadata and gzip timestamp make the artifact reproducible.
    with output.open("wb") as destination:
        with gzip.GzipFile(filename="", fileobj=destination, mode="wb", mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT) as archive:
                for source, member_name in members:
                    info = tarfile.TarInfo(member_name)
                    payload = source.read_bytes()
                    info.size = len(payload)
                    info.mode = 0o644
                    info.uid = info.gid = 0
                    info.uname = info.gname = ""
                    info.mtime = 0
                    archive.addfile(info, io.BytesIO(payload))

    digest = _sha256(output)
    result = {
        "archive": str(output),
        "sha256": digest,
        "archive_bytes": output.stat().st_size,
        "required_bytes": verification["required_bytes"],
        "release": verification["release"],
        "members": [name for _, name in members],
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--roads-dir", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--allow-synthetic", action="store_true", help="Permit the isolated test fixture; never use for production artifacts")
    args = parser.parse_args()
    package(args.data_root, args.output, roads_root=args.roads_dir, allow_synthetic=args.allow_synthetic)


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, tarfile.TarError) as exc:
        raise SystemExit(f"ERROR: {exc}") from exc
