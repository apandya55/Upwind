"""Isolated concurrency, rollback and adversarial API/data checks."""

from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import os, tempfile, time
from fastapi.testclient import TestClient
from ..api import app
from ..models import ImportRequest
from ..importers import parse_csv
from ..fixtures import synthetic_case


def api_battery():
    previous = os.environ.get("UPWIND_DATA_DIR")
    try:
        with tempfile.TemporaryDirectory(prefix="upwind-stress-") as temp:
            os.environ["UPWIND_DATA_DIR"] = temp
            with TestClient(app, raise_server_exceptions=False) as client:
                inv, _ = synthetic_case()
                payload = inv.model_dump()

                def request(i):
                    value = payload | {"id": "", "name": f"Synthetic concurrency {i}"}
                    response = client.post("/api/investigations", json=value)
                    return response.status_code, response.json()

                started = time.perf_counter()
                with ThreadPoolExecutor(max_workers=32) as pool:
                    writes = list(pool.map(request, range(64)))
                statuses = Counter(code for code, _ in writes)
                saved = client.get("/api/investigations").json()
                ids = [body["id"] for code, body in writes if code == 200]
                success = len(saved) == len(ids) == len(set(ids)) and set(statuses) <= {
                    200,
                    429,
                }
                malformed = []
                for body in [
                    {"area": [1, 0, 0, 1]},
                    {"settings": {"budget": -1}},
                    {"measurements": [{"sensor_id": "A"}]},
                    {"plan_history": [{}]},
                ]:
                    malformed.append(
                        client.post("/api/investigations", json=body).status_code
                    )
                over = client.post(
                    "/api/import/csv", content="x" * 8_000_001
                ).status_code
                after = client.get("/api/investigations").json()
                intact = after == saved
                recovered = client.post("/api/investigations", json=payload).status_code
                errors = []
                fuzzed = 0
                for i in range(500):
                    # Deterministic mix of missing, non-finite, invalid timestamp,
                    # quote, width and formula-containing original values.
                    values = ["", "NaN", "inf", "-1", "0", "12", "500", "501"][i % 8]
                    stamp = [
                        "2025-01-01T00:00Z",
                        "bad",
                        "2025-11-02T01:30",
                        "2025-01-01T00:00+05:30",
                    ][(i // 8) % 4]
                    latitude = ["0", "85", "91", "NaN"][(i // 32) % 4]
                    data = f"A,{stamp},{latitude},0,{values}"
                    mode = (i // 128) % 4
                    if mode == 1:
                        data += ",extra"
                    elif mode == 2:
                        data = data.rsplit(",", 1)[0]
                    elif mode == 3:
                        data = '"' + data
                    raw = (
                        "sensor_id,timestamp,latitude,longitude,pm25_ug_m3\n"
                        + data
                        + "\n"
                    )
                    try:
                        rows, record = parse_csv(
                            ImportRequest(csv=raw, timezone="America/New_York")
                        )
                        assert (
                            record.raw_csv == raw
                            and record.summary["accepted"] + record.summary["invalid"]
                            == 1
                        )
                    except ValueError:
                        pass
                    except Exception as e:
                        errors.append(
                            {
                                "index": i,
                                "exception": type(e).__name__,
                                "message": str(e),
                            }
                        )
                    fuzzed += 1
                return {
                    "concurrent_requests": 64,
                    "workers": 32,
                    "response_statuses": dict(statuses),
                    "acknowledged_writes": len(ids),
                    "stored_before_bad_requests": len(saved),
                    "all_acknowledged_writes_preserved": success,
                    "malformed_statuses": malformed,
                    "oversized_status": over,
                    "no_partial_bad_writes": intact,
                    "request_after_overload": recovered,
                    "fuzzed_csv_cases": fuzzed,
                    "unexpected_csv_errors": errors,
                    "wall_ms": round((time.perf_counter() - started) * 1000, 2),
                    "passed": success
                    and all(s == 422 for s in malformed)
                    and over == 413
                    and intact
                    and recovered == 200
                    and not errors,
                }
    finally:
        if previous is None:
            os.environ.pop("UPWIND_DATA_DIR", None)
        else:
            os.environ["UPWIND_DATA_DIR"] = previous
