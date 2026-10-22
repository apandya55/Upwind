import json
import math
import asyncio
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from .models import Investigation, ImportRequest, migrate_analysis
from .fixtures import synthetic_case
from .engine import analyze, MODEL_VERSION, PROTOCOL_VERSION
from .importers import parse_csv
from . import store
from .report import evidence_report, measurements_csv

app = FastAPI(title="UPWIND", version="0.1.0")
_post_capacity = asyncio.Semaphore(4)


def _finite_json_float(text):
    value = float(text)
    if not math.isfinite(value):
        raise ValueError("JSON numbers must be finite")
    return value


def _reject_json_constant(text):
    raise ValueError("Nonstandard JSON number: " + text)


def _validate_json_body(raw):
    value = json.loads(
        raw, parse_float=_finite_json_float, parse_constant=_reject_json_constant
    )
    pending = [(value, 0)]
    while pending:
        node, depth = pending.pop()
        if depth > 64:
            raise ValueError("JSON nesting exceeds64levels")
        if isinstance(node, dict):
            pending.extend((item, depth + 1) for item in node.values())
        elif isinstance(node, list):
            pending.extend((item, depth + 1) for item in node)


@app.middleware("http")
async def size_limit(request: Request, call_next):
    # Stream limit also covers clients without Content-Length.
    if request.method in {"POST", "PUT"}:
        chunks, size = [], 0
        async for chunk in request.stream():
            size += len(chunk)
            if size > 8_000_000:
                return Response("Request exceeds 8 MB limit", status_code=413)
            chunks.append(chunk)
        request._body = b"".join(chunks)
        try:
            _validate_json_body(request._body)
        except (ValueError, RecursionError) as exc:
            return Response(
                json.dumps({"detail": "Invalid JSON request: " + str(exc)}),
                status_code=422,
                media_type="application/json",
            )
    try:
        return await call_next(request)
    except ValueError as e:
        return Response(
            json.dumps({"detail": str(e)}),
            status_code=422,
            media_type="application/json",
        )


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "version": "0.1.0",
        "model_version": MODEL_VERSION,
        "protocol_version": PROTOCOL_VERSION,
        "evidence": "synthetic evaluations only",
    }


@app.middleware("http")
async def bounded_post_admission(request: Request, call_next):
    # Reject overload before buffering large JSON bodies. One application worker
    # owns this event-loop semaphore; health/reads stay available under load.
    if request.method not in {"POST", "PUT"}:
        return await call_next(request)
    if _post_capacity.locked():
        return Response(
            '{"detail":"Four requests are already processing; retry shortly"}',
            status_code=429,
            media_type="application/json",
            headers={"Retry-After": "1"},
        )
    await _post_capacity.acquire()
    try:
        return await call_next(request)
    finally:
        _post_capacity.release()


@app.get("/api/demo")
def demo():
    inv, _ = synthetic_case()
    return inv


@app.get("/api/demo/campaign")
def campaign_demo():
    from .campaign_fixture import synthetic_campaign

    return synthetic_campaign()


@app.post("/api/analyze")
def analysis(inv: Investigation):
    return analyze(inv)


@app.post("/api/import/csv")
def import_csv(req: ImportRequest):
    try:
        rows, record = parse_csv(req)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    return {"rows": [r.model_dump() for r in rows], "record": record}


@app.get("/api/investigations")
def investigations():
    return store.list_all()


@app.post("/api/investigations")
def save(inv: Investigation):
    migrate_analysis(inv)
    if inv.result is not None:
        inv.result = analyze(inv)
    return store.save(inv)


@app.post("/api/investigations/import")
def import_investigation(inv: Investigation):
    migrate_analysis(inv)
    inv.id = ""
    if inv.result is not None:
        inv.result = analyze(inv)
    return store.save(inv)


def lookup(id):
    try:
        return store.load(id)
    except KeyError:
        raise HTTPException(404, "Investigation not found")


@app.get("/api/investigations/{id}")
def get_investigation(id: str):
    return lookup(id)


@app.get("/api/investigations/{id}/export")
def export(id: str):
    return Response(
        lookup(id).model_dump_json(indent=2),
        media_type="application/json",
        headers={
            "Content-Disposition": 'attachment; filename="upwind-investigation.json"'
        },
    )


@app.get("/api/investigations/{id}/measurements.csv")
def export_csv(id: str):
    return Response(
        measurements_csv(lookup(id)),
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="upwind-measurements.csv"'
        },
    )


@app.get("/api/investigations/{id}/report", response_class=HTMLResponse)
def report(id: str):
    return HTMLResponse(
        evidence_report(lookup(id)),
        headers={
            "Content-Disposition": 'attachment; filename="upwind-evidence.html"',
            "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'",
        },
    )


# Run `npm run build` first for a single-process local production application.
dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if dist.exists():
    app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")
