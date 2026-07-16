from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class UserRecord:
    username: str
    role: str
    password_hash: str
    salt: str


class UserManager:
    def __init__(self) -> None:
        self._users: dict[str, UserRecord] = {}

    @staticmethod
    def _hash(password: str, salt: bytes) -> str:
        return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000).hex()

    def create_user(self, username: str, password: str, role: str) -> UserRecord:
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters")
        salt = os.urandom(16)
        record = UserRecord(username=username, role=role.upper(), password_hash=self._hash(password, salt), salt=salt.hex())
        self._users[username] = record
        return record

    def verify_password(self, username: str, password: str) -> bool:
        record = self._users.get(username)
        if not record:
            return False
        return self._hash(password, bytes.fromhex(record.salt)) == record.password_hash
