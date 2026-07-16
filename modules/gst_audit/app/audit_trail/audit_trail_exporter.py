from __future__ import annotations

import json
from pathlib import Path

from app.audit_trail.event_logger import AuditTrailLogger


def export_audit_trail(logger: AuditTrailLogger, session_id: str, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(logger.list_events(session_id), indent=2, default=str), encoding="utf-8")
    return path
