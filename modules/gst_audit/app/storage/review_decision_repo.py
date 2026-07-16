from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.storage.database import Database


@dataclass(frozen=True)
class ReviewDecision:
    session_id: str
    row_id: int
    decision: str
    actor: str
    reason: str
    old_value: str = ""
    new_value: str = ""
    evidence_ref: str = ""
    created_at: str = ""


class ReviewDecisionRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def save(self, decision: ReviewDecision) -> int:
        if not decision.reason.strip():
            raise ValueError("Review decision reason is required for audit evidence")
        created_at = decision.created_at or datetime.now(timezone.utc).isoformat()
        with self.db.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO review_decisions(session_id, row_id, decision, actor, reason, created_at, old_value, new_value, evidence_ref)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (decision.session_id, decision.row_id, decision.decision, decision.actor, decision.reason, created_at, decision.old_value, decision.new_value, decision.evidence_ref),
            )
            conn.commit()
            return int(cur.lastrowid)

    def list_for_session(self, session_id: str) -> list[dict[str, Any]]:
        with self.db.connect() as conn:
            rows = conn.execute("SELECT * FROM review_decisions WHERE session_id=? ORDER BY id", (session_id,)).fetchall()
        return [dict(row) for row in rows]
