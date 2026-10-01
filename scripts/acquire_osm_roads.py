#!/usr/bin/env python3
"""Acquire the two documented, bounded OSM road extracts used by Local Investigation."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.parse import urlencode
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
ENDPOINT = "https://api.openstreetmap.org/api/0.6/map"
PLACES = {
    "durham": {"label": "Durham", "latitude": 35.977928, "longitude": -78.898109},
    "charlotte": {"label": "Charlotte", "latitude": 35.209045, "longitude": -80.830990},
}


def acquire(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for key, place in PLACES.items():
        lat, lon = place["latitude"], place["longitude"]
        bounds = {"south": lat - .006, "west": lon - .0075, "north": lat + .006, "east": lon + .0075}
        query = urlencode({"bbox": f"{bounds['west']},{bounds['south']},{bounds['east']},{bounds['north']}"})
        data_path = output_dir / f"{key}.osm"
        temporary = data_path.with_suffix(".osm.partial")
        command = ["curl", "--fail", "--location", "--silent", "--show-error", "--connect-timeout", "20",
                   "--max-time", "180", "--retry", "2", "--max-filesize", "40000000",
                   "--user-agent", "UPWIND/1.0 data acquisition (https://github.com/apandya55/Upwind)",
                   f"{ENDPOINT}?{query}", "--output", str(temporary), "--write-out", "%{http_code}"]
        response = subprocess.run(command, check=True, capture_output=True, text=True)
        if response.stdout.strip() != "200":
            temporary.unlink(missing_ok=True)
            raise RuntimeError(f"OSM API returned HTTP {response.stdout.strip()} for {place['label']}")
        payload = temporary.read_bytes()
        root = ElementTree.fromstring(payload)
        if root.tag != "osm" or root.find("bounds") is None:
            raise RuntimeError(f"OSM response for {place['label']} was not a bounded OSM XML extract")
        temporary.replace(data_path)
        metadata = {
            "city": place["label"], "center_wgs84": {"latitude": lat, "longitude": lon},
            "extract_bounds_wgs84": bounds,
            "retrieved_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "source": "OpenStreetMap contributors", "endpoint": ENDPOINT,
            "license": "Open Database License (ODbL) 1.0",
            "attribution": "© OpenStreetMap contributors",
            "query_bbox_order": "west,south,east,north",
            "highway_classes_used": ["motorway", "trunk", "primary", "secondary"],
            "analysis_radius_km": 0.65, "sha256": hashlib.sha256(payload).hexdigest(),
        }
        (output_dir / f"{key}.metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
        print(f"{place['label']}: {len(payload)} bytes sha256={metadata['sha256']}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "deployment-data" / "osm_roads" / "raw")
    acquire(parser.parse_args().output_dir)


if __name__ == "__main__":
    main()
