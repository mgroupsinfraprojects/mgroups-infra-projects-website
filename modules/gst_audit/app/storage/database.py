from __future__ import annotations

import sqlite3
from pathlib import Path

from app.storage.migrations import SCHEMA_SQL


class Database:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path or ":memory:")

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def initialize(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA_SQL)
            conn.commit()
