from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Mapping


@dataclass(frozen=True)
class WebUser:
    username: str
    role: str
    display_name: str


ROLE_PERMISSIONS: Mapping[str, set[str]] = {
    "admin": {"upload", "review", "export", "view", "audit_log", "clear"},
    "auditor": {"upload", "review", "export", "view", "clear"},
    "viewer": {"view", "export"},
}


class AuthError(ValueError):
    pass


class WebAuthManager:
    """Small local-web auth manager for the standalone browser mode.

    This is deliberately lightweight and dependency-free. It is suitable for local/LAN
    operation of the included stdlib web server. In the M-Groups portal, replace this
    with the main Flask/Django login/RBAC tables.
    """

    def __init__(self, runtime_dir: str | Path) -> None:
        self.runtime_dir = Path(runtime_dir)
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.users_path = self.runtime_dir / "users.json"
        self.sessions: Dict[str, WebUser] = {}
        self._ensure_users()

    def authenticate(self, username: str, password: str) -> WebUser:
        username = (username or "").strip().lower()
        password = password or ""
        data = self._read_users()
        record = data.get("users", {}).get(username)
        if not record:
            raise AuthError("Invalid username or password.")
        salt = bytes.fromhex(record["salt"])
        expected = record["password_hash"]
        actual = self._hash_password(password, salt)
        if not hmac.compare_digest(expected, actual):
            raise AuthError("Invalid username or password.")
        return WebUser(username=username, role=record["role"], display_name=record.get("display_name") or username.title())

    def create_session(self, user: WebUser) -> str:
        token = secrets.token_urlsafe(32)
        self.sessions[token] = user
        return token

    def destroy_session(self, token: str | None) -> None:
        if token:
            self.sessions.pop(token, None)

    def user_for_token(self, token: str | None) -> WebUser | None:
        if not token:
            return None
        return self.sessions.get(token)

    def require(self, user: WebUser | None, permission: str) -> None:
        if not user:
            raise AuthError("Login required.")
        if permission not in ROLE_PERMISSIONS.get(user.role, set()):
            raise AuthError(f"Permission denied: {permission} access is not enabled for {user.role}.")

    @staticmethod
    def permissions_for(user: WebUser | None) -> Mapping[str, bool]:
        allowed = ROLE_PERMISSIONS.get(user.role, set()) if user else set()
        return {name: name in allowed for name in ["upload", "review", "export", "view", "audit_log", "clear"]}

    def public_user_payload(self, user: WebUser | None) -> Mapping[str, object]:
        if not user:
            return {"authenticated": False, "permissions": self.permissions_for(None)}
        return {
            "authenticated": True,
            "username": user.username,
            "role": user.role,
            "display_name": user.display_name,
            "permissions": self.permissions_for(user),
        }

    def _ensure_users(self) -> None:
        if self.users_path.exists():
            return
        admin_password = os.environ.get("GST_AUDIT_WEB_ADMIN_PASSWORD", "admin123")
        auditor_password = os.environ.get("GST_AUDIT_WEB_AUDITOR_PASSWORD", "audit123")
        viewer_password = os.environ.get("GST_AUDIT_WEB_VIEWER_PASSWORD", "view123")
        users = {
            "admin": self._user_record("admin", "admin", "Administrator", admin_password),
            "auditor": self._user_record("auditor", "auditor", "Auditor", auditor_password),
            "viewer": self._user_record("viewer", "viewer", "Viewer", viewer_password),
        }
        payload = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "note": "Change default local passwords before LAN/server use. Use environment variables before first launch.",
            "users": users,
        }
        self.users_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _user_record(self, username: str, role: str, display_name: str, password: str) -> Mapping[str, str]:
        salt = secrets.token_bytes(16)
        return {
            "username": username,
            "role": role,
            "display_name": display_name,
            "salt": salt.hex(),
            "password_hash": self._hash_password(password, salt),
        }

    def _read_users(self) -> Mapping[str, object]:
        return json.loads(self.users_path.read_text(encoding="utf-8"))

    @staticmethod
    def _hash_password(password: str, salt: bytes) -> str:
        return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 180_000).hex()
