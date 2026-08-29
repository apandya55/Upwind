import os
from pathlib import Path
import sqlite3
import uuid
from datetime import datetime, timezone
from .models import Investigation, migrate_analysis


def data_dir():
    root = Path(os.environ.get("UPWIND_DATA_DIR", ".local"))
    root.mkdir(parents=True, exist_ok=True)
    return root


def connection():
    db = sqlite3.connect(data_dir() / "upwind.sqlite3", timeout=20)
    db.execute(
        "CREATE TABLE IF NOT EXISTS investigations (id TEXT PRIMARY KEY, name TEXT NOT NULL, updated TEXT NOT NULL, payload TEXT NOT NULL)"
    )
    return db


def save(inv):
    inv = inv.model_copy(deep=True)
    if not inv.id:
        inv.id = uuid.uuid4().hex
    with connection() as db:
        db.execute(
            "INSERT INTO investigations VALUES (?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,updated=excluded.updated,payload=excluded.payload",
            (
                inv.id,
                inv.name,
                datetime.now(timezone.utc).isoformat(),
                inv.model_dump_json(),
            ),
        )
    return inv


def list_all():
    with connection() as db:
        return [
            dict(id=r[0], name=r[1], updated=r[2])
            for r in db.execute(
                "SELECT id,name,updated FROM investigations ORDER BY updated DESC"
            )
        ]


def load(id):
    with connection() as db:
        row = db.execute(
            "SELECT payload FROM investigations WHERE id=?", (id,)
        ).fetchone()
    if row is None:
        raise KeyError(id)
    return migrate_analysis(Investigation.model_validate_json(row[0]))
