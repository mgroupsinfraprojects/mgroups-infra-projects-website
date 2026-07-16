from __future__ import annotations

from app.audit_trail.event_logger import GENESIS_HASH
from app.audit_trail.hash_chain import calculate_event_hash
from app.storage.database import Database


def verify_audit_trail(db: Database, session_id: str) -> tuple[bool, list[str]]:
    with db.connect() as conn:
        rows = conn.execute("SELECT * FROM audit_events WHERE session_id=? ORDER BY id", (session_id,)).fetchall()
    errors: list[str] = []
    previous = GENESIS_HASH
    for row in rows:
        if row["previous_hash"] != previous:
            errors.append(f"Broken previous hash at event {row['id']}")
        expected = calculate_event_hash(row["previous_hash"], row["session_id"], row["actor"], row["action"], row["payload_json"], row["created_at"])
        if expected != row["event_hash"]:
            errors.append(f"Tampered event hash at event {row['id']}")
        previous = row["event_hash"]
    return (not errors, errors)
