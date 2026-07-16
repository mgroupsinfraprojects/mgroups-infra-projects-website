from __future__ import annotations

import base64
import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Iterable, Mapping

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class Role(str, Enum):
    ADMIN = "ADMIN"
    AUDITOR = "AUDITOR"
    REVIEWER = "REVIEWER"
    VIEWER = "VIEWER"


class Permission(str, Enum):
    IMPORT_FILES = "IMPORT_FILES"
    REVIEW_ROWS = "REVIEW_ROWS"
    EXPORT_REPORTS = "EXPORT_REPORTS"
    MANAGE_SETTINGS = "MANAGE_SETTINGS"
    MANAGE_USERS = "MANAGE_USERS"
    VIEW_DASHBOARD = "VIEW_DASHBOARD"


ROLE_PERMISSIONS: Mapping[Role, frozenset[Permission]] = {
    Role.ADMIN: frozenset(Permission),
    Role.AUDITOR: frozenset({
        Permission.IMPORT_FILES,
        Permission.REVIEW_ROWS,
        Permission.EXPORT_REPORTS,
        Permission.MANAGE_SETTINGS,
        Permission.VIEW_DASHBOARD,
    }),
    Role.REVIEWER: frozenset({Permission.REVIEW_ROWS, Permission.EXPORT_REPORTS, Permission.VIEW_DASHBOARD}),
    Role.VIEWER: frozenset({Permission.VIEW_DASHBOARD}),
}


@dataclass(frozen=True)
class AuditSecurityEvent:
    event_type: str
    actor: str
    target: str
    timestamp: str
    payload_hash: str
    previous_hash: str
    event_hash: str


def has_permission(role: Role | str, permission: Permission | str) -> bool:
    role_value = role if isinstance(role, Role) else Role(str(role))
    permission_value = permission if isinstance(permission, Permission) else Permission(str(permission))
    return permission_value in ROLE_PERMISSIONS[role_value]


def sha256_file(path: str | Path, *, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_payload_hash(payload: Mapping[str, object] | Iterable[object] | str) -> str:
    if isinstance(payload, str):
        raw = payload.encode("utf-8")
    else:
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def create_security_event(event_type: str, actor: str, target: str, payload: Mapping[str, object] | Iterable[object] | str, previous_hash: str = "GENESIS") -> AuditSecurityEvent:
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    payload_hash = canonical_payload_hash(payload)
    base = "|".join([event_type, actor, target, timestamp, payload_hash, previous_hash])
    event_hash = hashlib.sha256(base.encode("utf-8")).hexdigest()
    return AuditSecurityEvent(
        event_type=event_type,
        actor=actor,
        target=target,
        timestamp=timestamp,
        payload_hash=payload_hash,
        previous_hash=previous_hash,
        event_hash=event_hash,
    )


def _derive_fernet_key(password: str, salt: bytes, *, iterations: int = 390_000) -> bytes:
    if not password:
        raise ValueError("Encryption password must not be empty.")
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=iterations)
    return base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))


def encrypt_bytes(data: bytes, password: str, *, salt: bytes | None = None) -> bytes:
    salt = salt or hashlib.sha256(datetime.now(timezone.utc).isoformat().encode("utf-8")).digest()[:16]
    token = Fernet(_derive_fernet_key(password, salt)).encrypt(data)
    return b"GSTAP1" + salt + token


def decrypt_bytes(blob: bytes, password: str) -> bytes:
    if not blob.startswith(b"GSTAP1") or len(blob) < 22:
        raise ValueError("Unsupported encrypted payload format.")
    salt = blob[6:22]
    token = blob[22:]
    try:
        return Fernet(_derive_fernet_key(password, salt)).decrypt(token)
    except InvalidToken as exc:
        raise ValueError("Invalid password or corrupted encrypted payload.") from exc


def encrypt_file(source: str | Path, target: str | Path, password: str) -> Path:
    source_path = Path(source)
    target_path = Path(target)
    target_path.write_bytes(encrypt_bytes(source_path.read_bytes(), password))
    return target_path


def decrypt_file(source: str | Path, target: str | Path, password: str) -> Path:
    source_path = Path(source)
    target_path = Path(target)
    target_path.write_bytes(decrypt_bytes(source_path.read_bytes(), password))
    return target_path


def constant_time_hash_equal(left: str, right: str) -> bool:
    return hmac.compare_digest(str(left), str(right))
