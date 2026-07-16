from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.audit_trail.hash_chain import canonical_json, calculate_event_hash
from app.storage.database import Database

GENESIS_HASH = "0" * 64


class AuditTrailLogger:
    def __init__(self, db: Database) -> None:
        self.db = db
        self.db.initialize()

    def _last_hash(self, session_id: str) -> str:
        with self.db.connect() as conn:
            row = conn.execute("SELECT event_hash FROM audit_events WHERE session_id=? ORDER BY id DESC LIMIT 1", (session_id,)).fetchone()
        return str(row["event_hash"]) if row else GENESIS_HASH

    def record(self, session_id: str, actor: str, action: str, payload: dict[str, Any]) -> str:
        if not action.strip():
            raise ValueError("Audit-trail action is required")
        created_at = datetime.now(timezone.utc).isoformat()
        payload_json = canonical_json(payload)
        previous_hash = self._last_hash(session_id)
        event_hash = calculate_event_hash(previous_hash, session_id, actor, action, payload_json, created_at)
        with self.db.connect() as conn:
            conn.execute(
                """
                INSERT INTO audit_events(session_id, actor, action, payload_json, previous_hash, event_hash, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (session_id, actor, action, payload_json, previous_hash, event_hash, created_at),
            )
            conn.commit()
        return event_hash

    def list_events(self, session_id: str) -> list[dict[str, Any]]:
        with self.db.connect() as conn:
            rows = conn.execute("SELECT * FROM audit_events WHERE session_id=? ORDER BY id", (session_id,)).fetchall()
        return [dict(row) for row in rows]
