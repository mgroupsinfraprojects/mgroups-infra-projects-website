from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Any
from uuid import uuid4

from app.audit_trail.event_logger import AuditTrailLogger
from app.core.executive_dashboard import build_fix_first_dashboard
from app.core.models import InvoiceRow
from app.core.review_queue_engine import ReviewQueueItem, build_review_queue, summarize_review_queue
from app.storage.audit_session_repo import AuditSessionRepository
from app.storage.database import Database
from app.workflow.workflow_state import WorkflowStage, WorkflowState


@dataclass(frozen=True)
class WorkflowRunResult:
    state: WorkflowState
    review_queue: list[ReviewQueueItem]
    dashboard: dict[str, Any]
    export_blocked: bool


class AuditWorkflowController:
    """Single orchestration boundary used by the UI.

    UI code should call this controller after parsing/audit completion instead of
    recomputing severity, dashboard totals, or export readiness in widgets.
    """

    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db = Database(db_path) if db_path else None
        self.sessions = AuditSessionRepository(self.db) if self.db else None
        self.audit_trail = AuditTrailLogger(self.db) if self.db else None
        if self.db:
            self.db.initialize()

    def start_session(self, *, company_id: str = "LOCAL", gstin: str = "", financial_year: str = "", period: str = "") -> WorkflowState:
        state = WorkflowState(
            session_id=str(uuid4()),
            company_id=company_id,
            gstin=gstin,
            financial_year=financial_year,
            period=period,
        )
        if self.sessions:
            self.sessions.create_session(state)
        if self.audit_trail:
            self.audit_trail.record(state.session_id, "SYSTEM", "SESSION_CREATED", {"company_id": company_id, "gstin": gstin})
        return state

    def classify_review(self, state: WorkflowState, rows: Iterable[InvoiceRow], *, actor: str = "SYSTEM") -> WorkflowRunResult:
        row_list = list(rows)
        state.transition_to(WorkflowStage.AUDITED, row_count=len(row_list))
        queue = build_review_queue(row_list, include_non_blocking=True)
        summary = summarize_review_queue(queue)
        dashboard = build_fix_first_dashboard(row_list)
        state.transition_to(
            WorkflowStage.DASHBOARD_READY,
            mandatory_review_count=summary.mandatory_count,
            advisory_review_count=summary.advisory_count,
            export_blocked=summary.export_blocked,
        )
        if self.sessions:
            self.sessions.update_session_state(state)
        if self.audit_trail:
            self.audit_trail.record(
                state.session_id,
                actor,
                "REVIEW_QUEUE_CLASSIFIED",
                {
                    "row_count": len(row_list),
                    "mandatory_review_count": summary.mandatory_count,
                    "advisory_review_count": summary.advisory_count,
                    "export_blocked": summary.export_blocked,
                },
            )
        return WorkflowRunResult(state=state, review_queue=queue, dashboard=dashboard, export_blocked=summary.export_blocked)
