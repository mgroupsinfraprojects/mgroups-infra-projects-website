from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Mapping


@dataclass(frozen=True)
class AuditEvent:
    timestamp: str
    actor: str
    role: str
    event: str
    session_id: str
    details: Mapping[str, object]


class AuditEventStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, actor: str, role: str, event: str, session_id: str = "", **details: object) -> AuditEvent:
        item = AuditEvent(
            timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            actor=actor or "system",
            role=role or "system",
            event=event,
            session_id=session_id or "",
            details=details,
        )
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(asdict(item), ensure_ascii=False) + "\n")
        return item

    def recent(self, limit: int = 50) -> List[Mapping[str, object]]:
        if not self.path.exists():
            return []
        lines = self.path.read_text(encoding="utf-8").splitlines()[-limit:]
        output: List[Mapping[str, object]] = []
        for line in lines:
            try:
                output.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return list(reversed(output))

    def export_csv(self, output_path: str | Path) -> Path:
        output = Path(output_path)
        rows = self.recent(100000)
        with output.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=["timestamp", "actor", "role", "event", "session_id", "details"])
            writer.writeheader()
            for row in reversed(rows):
                writer.writerow({
                    "timestamp": row.get("timestamp", ""),
                    "actor": row.get("actor", ""),
                    "role": row.get("role", ""),
                    "event": row.get("event", ""),
                    "session_id": row.get("session_id", ""),
                    "details": json.dumps(row.get("details", {}), ensure_ascii=False),
                })
        return output
