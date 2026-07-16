from __future__ import annotations

import json
from typing import Any

from app.storage.database import Database
from app.workflow.workflow_state import WorkflowState, WorkflowStage


class AuditSessionRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def create_session(self, state: WorkflowState) -> None:
        with self.db.connect() as conn:
            conn.execute(
                """
                INSERT INTO audit_sessions(session_id, company_id, gstin, financial_year, period, stage, updated_at, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (state.session_id, state.company_id, state.gstin, state.financial_year, state.period, state.stage.value, state.updated_at, json.dumps(state.metadata, sort_keys=True)),
            )
            conn.commit()

    def update_session_state(self, state: WorkflowState) -> None:
        with self.db.connect() as conn:
            conn.execute(
                """
                UPDATE audit_sessions SET stage=?, updated_at=?, metadata_json=? WHERE session_id=?
                """,
                (state.stage.value, state.updated_at, json.dumps(state.metadata, sort_keys=True), state.session_id),
            )
            conn.commit()

    def get_session(self, session_id: str) -> WorkflowState | None:
        with self.db.connect() as conn:
            row = conn.execute("SELECT * FROM audit_sessions WHERE session_id=?", (session_id,)).fetchone()
        if not row:
            return None
        return WorkflowState(
            session_id=row["session_id"],
            company_id=row["company_id"],
            gstin=row["gstin"],
            financial_year=row["financial_year"],
            period=row["period"],
            stage=WorkflowStage(row["stage"]),
            updated_at=row["updated_at"],
            metadata=json.loads(row["metadata_json"] or "{}"),
        )

    def list_sessions(self) -> list[dict[str, Any]]:
        with self.db.connect() as conn:
            rows = conn.execute("SELECT * FROM audit_sessions ORDER BY updated_at DESC").fetchall()
        return [dict(row) for row in rows]
