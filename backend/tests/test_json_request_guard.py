"""Regression checks for request-boundary failures found during severe stress."""

import json

from fastapi.testclient import TestClient
import pytest

from upwind.api import app
from upwind.fixtures import synthetic_case


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("UPWIND_DATA_DIR", str(tmp_path))
    with TestClient(app, raise_server_exceptions=False) as value:
        yield value


@pytest.mark.parametrize("depth", [70, 1200])
def test_deep_json_is_rejected_without_storage_or_broken_admission(client, depth):
    body = '{"archived_results":[{"metadata":' + "[" * depth + "0" + "]" * depth + "}]}"
    response = client.post(
        "/api/investigations",
        content=body,
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422
    assert client.get("/api/investigations").json() == []
    inv, _ = synthetic_case()
    assert client.post("/api/investigations", json=inv.model_dump()).status_code == 200


@pytest.mark.parametrize("token", ["NaN", "Infinity", "-Infinity", "1e999"])
@pytest.mark.parametrize("container", ["result", "archive"])
def test_nonfinite_json_is_not_silently_rewritten_as_null(client, token, container):
    if container == "result":
        raw = '{"result":{"model_version":"old","nested":{"score":' + token + "}}}"
    else:
        raw = '{"archived_results":[{"nested":{"score":' + token + "}}]}"
    assert (
        client.post(
            "/api/investigations",
            content=raw,
            headers={"Content-Type": "application/json"},
        ).status_code
        == 422
    )
    assert client.get("/api/investigations").json() == []


def test_quoted_nan_and_brackets_are_valid_text_and_round_trip(client):
    inv, _ = synthetic_case()
    inv.concern = "[" * 100 + "NaN Infinity -Infinity 1e999 are text here" + "]" * 100
    saved = client.post("/api/investigations", json=inv.model_dump())
    assert saved.status_code == 200
    loaded = client.get("/api/investigations/" + saved.json()["id"]).json()
    assert loaded["concern"] == inv.concern
    assert loaded["measurements"] == saved.json()["measurements"]


def test_nan_in_raw_csv_remains_an_invalid_retained_row(client):
    raw = "sensor_id,timestamp,latitude,longitude,pm25_ug_m3\nA,2026-01-01T00:00Z,0,0,NaN\n"
    response = client.post("/api/import/csv", json={"csv": raw})
    assert response.status_code == 200
    assert response.json()["record"]["raw_csv"] == raw
    assert response.json()["record"]["summary"]["invalid"] == 1


def test_valid_archived_metadata_near_depth_bound_is_preserved(client):
    value = 1.25
    for _ in range(58):
        value = [value]
    raw = {"archived_results": [{"metadata": value}]}
    response = client.post(
        "/api/investigations",
        content=json.dumps(raw),
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 200
    loaded = client.get("/api/investigations/" + response.json()["id"]).json()
    assert loaded["archived_results"] == raw["archived_results"]
