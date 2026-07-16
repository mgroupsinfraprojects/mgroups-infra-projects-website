from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def calculate_event_hash(previous_hash: str, session_id: str, actor: str, action: str, payload_json: str, created_at: str) -> str:
    raw = "|".join([previous_hash, session_id, actor, action, payload_json, created_at])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
