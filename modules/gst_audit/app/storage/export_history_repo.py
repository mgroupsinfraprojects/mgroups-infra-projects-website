from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.storage.database import Database


def file_sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


class ExportHistoryRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def record_export(self, session_id: str, export_path: str | Path, actor: str) -> int:
        path = Path(export_path)
        digest = file_sha256(path) if path.exists() else "MISSING_FILE"
        with self.db.connect() as conn:
            cur = conn.execute(
                "INSERT INTO export_history(session_id, export_path, export_sha256, actor, created_at) VALUES (?, ?, ?, ?, ?)",
                (session_id, str(path), digest, actor, datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
            return int(cur.lastrowid)

    def list_for_session(self, session_id: str) -> list[dict[str, Any]]:
        with self.db.connect() as conn:
            rows = conn.execute("SELECT * FROM export_history WHERE session_id=? ORDER BY id", (session_id,)).fetchall()
        return [dict(row) for row in rows]
