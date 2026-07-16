from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class WorkflowStage(str, Enum):
    CREATED = "CREATED"
    FILES_UPLOADED = "FILES_UPLOADED"
    PARSED = "PARSED"
    AUDITED = "AUDITED"
    REVIEW_CLASSIFIED = "REVIEW_CLASSIFIED"
    DASHBOARD_READY = "DASHBOARD_READY"
    REVIEW_IN_PROGRESS = "REVIEW_IN_PROGRESS"
    EXPORT_READY = "EXPORT_READY"
    CLOSED = "CLOSED"


@dataclass
class WorkflowState:
    session_id: str
    company_id: str = "LOCAL"
    gstin: str = ""
    financial_year: str = ""
    period: str = ""
    stage: WorkflowStage = WorkflowStage.CREATED
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)

    def transition_to(self, stage: WorkflowStage, **metadata: Any) -> "WorkflowState":
        allowed = [item.value for item in WorkflowStage]
        if stage.value not in allowed:
            raise ValueError(f"Unknown workflow stage: {stage}")
        self.stage = stage
        self.updated_at = datetime.now(timezone.utc).isoformat()
        self.metadata.update(metadata)
        return self
