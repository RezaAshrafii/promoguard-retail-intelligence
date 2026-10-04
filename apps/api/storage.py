"""Transactional local-pilot metadata store; source files remain separate."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class PilotStore:
    def __init__(self, root: Path):
        self.path = root / "pilot.sqlite"

    @contextmanager
    def connection(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path, timeout=30) as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("""CREATE TABLE IF NOT EXISTS records (
                kind TEXT NOT NULL, id TEXT NOT NULL, payload TEXT NOT NULL,
                updated_at TEXT NOT NULL, PRIMARY KEY(kind, id))""")
            yield connection

    def put(self, kind: str, key: str, record: dict[str, Any]) -> None:
        payload = json.dumps(record, ensure_ascii=False, allow_nan=False,
                             default=lambda value: value.isoformat())
        with self.connection() as connection:
            connection.execute(
                "INSERT INTO records VALUES (?, ?, ?, ?) ON CONFLICT(kind,id) "
                "DO UPDATE SET payload=excluded.payload, updated_at=excluded.updated_at",
                (kind, key, payload, datetime.now(UTC).isoformat()),
            )

    def get(self, kind: str, key: str) -> dict[str, Any] | None:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT payload FROM records WHERE kind=? AND id=?", (kind, key)
            ).fetchone()
        return json.loads(row[0]) if row else None

    def list(self, kind: str, limit: int = 100) -> list[dict[str, Any]]:
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT payload FROM records WHERE kind=? ORDER BY updated_at DESC LIMIT ?",
                (kind, limit),
            ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def claim_report(self, key: str) -> dict[str, Any] | None:
        """Only one worker may move a queued report to running."""
        with self.connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT payload FROM records WHERE kind='report' AND id=?", (key,)
            ).fetchone()
            record = json.loads(row[0]) if row else None
            if record is None or record["status"] != "queued":
                return None
            record.update(status="running", progress=20, error=None)
            connection.execute(
                "UPDATE records SET payload=? WHERE kind='report' AND id=?",
                (json.dumps(record, ensure_ascii=False), key),
            )
            return record

    def recover_interrupted(self) -> int:
        """Single-process startup marks unfinished work retryable rather than ready."""
        with self.connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            rows = connection.execute("SELECT id,payload FROM records WHERE kind='report'").fetchall()
            recovered = 0
            for key, payload in rows:
                record = json.loads(payload)
                if record["status"] in {"queued", "running"}:
                    record.update(status="failed", error="تحلیل با راه‌اندازی مجدد سرویس قطع شد؛ تلاش مجدد را بزنید.")
                    connection.execute("UPDATE records SET payload=? WHERE kind='report' AND id=?",
                                       (json.dumps(record, ensure_ascii=False), key))
                    recovered += 1
        return recovered
