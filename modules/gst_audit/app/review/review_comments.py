from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class ReviewComment:
    session_id: str
    row_id: int
    actor: str
    comment: str
    created_at: str = datetime.now(timezone.utc).isoformat()

    def validate(self) -> None:
        if len(self.comment.strip()) < 3:
            raise ValueError("Review comment is too short")
