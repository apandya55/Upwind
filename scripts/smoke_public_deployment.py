#!/usr/bin/env python3
"""Smoke-test a deployed Explorer/API pair without third-party dependencies."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass
class Result:
    status: int
    headers: dict[str, str]
    body: bytes


def request(url: str, *, method: str = "GET", headers: dict[str, str] | None = None) -> Result:
    try:
        with urlopen(Request(url, method=method, headers=headers or {}), timeout=15) as response:
            headers = {key.lower(): value for key, value in response.headers.items()}
            return Result(response.status, headers, response.read())
    except HTTPError as exc:
        headers = {key.lower(): value for key, value in exc.headers.items()}
        return Result(exc.code, headers, exc.read())
    except URLError as exc:
        raise RuntimeError(f"request failed for {url}: {exc.reason}") from exc


def json_body(result: Result, label: str) -> dict:
    try:
        value = json.loads(result.body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"{label} did not return JSON") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"{label} returned a non-object JSON value")
    return value


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", required=True, help="Public Vercel/site origin, including https://")
    parser.add_argument("--api", required=True, help="Public National API origin, including https://")
    parser.add_argument("--origin", help="Allowed browser origin; defaults to --site")
    args = parser.parse_args()
    site = args.site.rstrip("/")
    api = args.api.rstrip("/")
    origin = (args.origin or site).rstrip("/")
    expect(site.startswith("https://"), "--site must use https://")
    expect(api.startswith("https://"), "--api must use https://")

    health = request(f"{api}/api/health")
    expect(health.status == 200, f"/api/health returned {health.status}")
    health_json = json_body(health, "/api/health")
    expect(health_json.get("product") == "national-explorer", "API is not in National Explorer public mode")
    expect(bool(health_json.get("model_version")), "API health omitted model identity")
    expect(bool(health_json.get("protocol_version")), "API health omitted protocol identity")

    ready = request(f"{api}/api/ready")
    expect(ready.status == 200, f"/api/ready returned {ready.status}: {ready.body[:240]!r}")
    expect(json_body(ready, "/api/ready").get("status") == "ready", "API is not ready")

    manifest = request(f"{api}/api/national/manifest")
    expect(manifest.status == 200, f"national manifest returned {manifest.status}")

    preflight = request(
        f"{api}/api/national/manifest",
        method="OPTIONS",
        headers={"Origin": origin, "Access-Control-Request-Method": "GET"},
    )
    expect(preflight.status in {200, 204}, f"allowed CORS preflight returned {preflight.status}")
    expect(
        preflight.headers.get("access-control-allow-origin") == origin,
        "allowed CORS preflight did not return the exact configured origin",
    )

    denied = request(
        f"{api}/api/national/manifest",
        method="OPTIONS",
        headers={"Origin": "https://not-allowed.invalid", "Access-Control-Request-Method": "GET"},
    )
    expect(
        denied.headers.get("access-control-allow-origin") is None,
        "unlisted origin received Access-Control-Allow-Origin",
    )

    for path in ("/api/demo", "/api/analyze", "/api/import/csv", "/api/investigations"):
        result = request(f"{api}{path}")
        expect(result.status == 404, f"publicly forbidden route {path} returned {result.status}")

    for path in ("/", "/methodology", "/about"):
        result = request(f"{site}{path}")
        expect(result.status == 200, f"site route {path} returned {result.status}")
        expect(b"UPWIND" in result.body, f"site route {path} did not return the app shell")

    print("Public deployment smoke test passed: health, readiness, CORS, route boundary, and SPA shell.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
