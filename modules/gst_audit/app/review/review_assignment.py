from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from .review_status import ReviewStatus


@dataclass(frozen=True)
class ReviewAssignment:
    session_id: str
    row_id: int
    assigned_to: str
    assigned_by: str
    status: ReviewStatus = ReviewStatus.ASSIGNED
    assigned_at: str = datetime.now(timezone.utc).isoformat()

    def validate(self) -> None:
        if not self.assigned_to or not self.assigned_by:
            raise ValueError("Reviewer assignment requires assigned_to and assigned_by")
