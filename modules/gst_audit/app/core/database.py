from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import sqlite3
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Iterable, List, Optional

from app.core.models import InvoiceRow

LOGGER = logging.getLogger(__name__)
SCHEMA_VERSION = 7

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS datasets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    summary_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS invoice_rows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dataset_id INTEGER NOT NULL,
    row_id INTEGER NOT NULL,
    source_file TEXT,
    sheet_name TEXT,
    excel_row_number INTEGER,
    supplier_name TEXT,
    gstin TEXT,
    invoice_no TEXT,
    hsn_sac TEXT,
    hsn_valid INTEGER,
    hsn_notes TEXT,
    recipient_gstin TEXT,
    all_gstins_json TEXT,
    self_invoice_flag INTEGER,
    gstin_roles_note TEXT,
    invoice_series TEXT,
    invoice_sequence_no INTEGER,
    invoice_gap_note TEXT,
    anomaly_note TEXT,
    suggested_correction TEXT,
    invoice_date TEXT,
    period TEXT,
    taxable_value TEXT,
    igst TEXT,
    cgst TEXT,
    sgst TEXT,
    cess TEXT,
    invoice_value TEXT,
    expected_invoice_value TEXT,
    difference_amount TEXT,
    difference_percent TEXT,
    mismatch_reason TEXT,
    audit_status TEXT,
    audit_severity TEXT,
    audit_indicator TEXT,
    audit_notes TEXT,
    review_required INTEGER,
    review_decision TEXT,
    include_in_totals INTEGER,
    reconstructed INTEGER,
    duplicate_key TEXT,
    raw_snapshot_json TEXT,
    detected_snapshot_json TEXT,
    final_snapshot_json TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(dataset_id, row_id),
    FOREIGN KEY(dataset_id) REFERENCES datasets(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS review_decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dataset_id INTEGER NOT NULL,
    row_id INTEGER NOT NULL,
    decision TEXT NOT NULL,
    include_in_totals INTEGER NOT NULL,
    note TEXT,
    decided_at TEXT DEFAULT CURRENT_TIMESTAMP,
    previous_hash TEXT,
    decision_hash TEXT,
    FOREIGN KEY(dataset_id) REFERENCES datasets(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_invoice_rows_supplier ON invoice_rows(supplier_name);
CREATE INDEX IF NOT EXISTS idx_invoice_rows_gstin ON invoice_rows(gstin);
CREATE INDEX IF NOT EXISTS idx_invoice_rows_include ON invoice_rows(include_in_totals);
CREATE INDEX IF NOT EXISTS idx_invoice_rows_dataset_row ON invoice_rows(dataset_id, row_id);
"""


def get_default_db_path() -> Path:
    """Return a per-user application data path for the local SQLite database.

    Production builds should not write mutable audit data into the executable or
    current working directory. This path avoids admin permissions and keeps data
    under the user's OS-managed profile folder.
    """
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    elif sys_platform := os.environ.get("XDG_DATA_HOME"):
        base = Path(sys_platform)
    else:
        base = Path.home() / ".local" / "share"
    data_dir = base / "GSTAuditPro"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "gst_invoice_audit.sqlite3"


def _json_loads(text: str, default):
    try:
        return json.loads(text) if text else default
    except Exception:
        return default


def _decimal(value: object) -> Decimal:
    try:
        return Decimal(str(value or 0)).quantize(Decimal("0.01"))
    except Exception:
        return Decimal("0.00")


def _row_get(row: sqlite3.Row, key: str, default=None):
    return row[key] if key in row.keys() else default


class AuditDatabase:
    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path) if db_path else get_default_db_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.executescript(SCHEMA)
        self._migrate_schema()
        self.conn.commit()

    def _migrate_schema(self) -> None:
        """Versioned SQLite migrations for safe upgrades from v4/v5 databases."""
        current = int(self.conn.execute("PRAGMA user_version").fetchone()[0])
        if current < SCHEMA_VERSION and self.db_path.exists() and self.db_path.stat().st_size > 0:
            # Best-effort backup before any ALTER TABLE operation.
            try:
                self.backup_database(f"before_migration_v{current}_to_v{SCHEMA_VERSION}")
            except Exception as exc:  # pragma: no cover - backup failure is logged but migration can proceed
                LOGGER.warning("Database migration backup failed: %s", exc)
        self._ensure_columns()
        self.conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")

    def _ensure_columns(self) -> None:
        """Apply idempotent column migrations for existing local SQLite files."""
        existing = {row[1] for row in self.conn.execute("PRAGMA table_info(invoice_rows)").fetchall()}
        migrations = {
            "hsn_sac": "ALTER TABLE invoice_rows ADD COLUMN hsn_sac TEXT",
            "hsn_valid": "ALTER TABLE invoice_rows ADD COLUMN hsn_valid INTEGER DEFAULT 0",
            "hsn_notes": "ALTER TABLE invoice_rows ADD COLUMN hsn_notes TEXT",
            "recipient_gstin": "ALTER TABLE invoice_rows ADD COLUMN recipient_gstin TEXT",
            "all_gstins_json": "ALTER TABLE invoice_rows ADD COLUMN all_gstins_json TEXT",
            "self_invoice_flag": "ALTER TABLE invoice_rows ADD COLUMN self_invoice_flag INTEGER DEFAULT 0",
            "gstin_roles_note": "ALTER TABLE invoice_rows ADD COLUMN gstin_roles_note TEXT",
            "invoice_series": "ALTER TABLE invoice_rows ADD COLUMN invoice_series TEXT",
            "invoice_sequence_no": "ALTER TABLE invoice_rows ADD COLUMN invoice_sequence_no INTEGER",
            "invoice_gap_note": "ALTER TABLE invoice_rows ADD COLUMN invoice_gap_note TEXT",
            "anomaly_note": "ALTER TABLE invoice_rows ADD COLUMN anomaly_note TEXT",
            "suggested_correction": "ALTER TABLE invoice_rows ADD COLUMN suggested_correction TEXT",
        }
        for column, statement in migrations.items():
            if column not in existing:
                LOGGER.info("Applying SQLite migration: add invoice_rows.%s", column)
                self.conn.execute(statement)

        review_existing = {row[1] for row in self.conn.execute("PRAGMA table_info(review_decisions)").fetchall()}
        review_migrations = {
            "previous_hash": "ALTER TABLE review_decisions ADD COLUMN previous_hash TEXT",
            "decision_hash": "ALTER TABLE review_decisions ADD COLUMN decision_hash TEXT",
        }
        for column, statement in review_migrations.items():
            if column not in review_existing:
                LOGGER.info("Applying SQLite migration: add review_decisions.%s", column)
                self.conn.execute(statement)

    def backup_database(self, reason: str = "manual") -> Optional[Path]:
        """Create a timestamped backup of the SQLite file before major writes."""
        if not self.db_path.exists() or self.db_path.stat().st_size == 0:
            return None
        backup_dir = self.db_path.parent / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        safe_reason = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in reason)[:40]
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        target = backup_dir / f"{self.db_path.stem}_{safe_reason}_{stamp}.sqlite3"
        self.conn.commit()
        shutil.copy2(self.db_path, target)
        return target

    def save_result(self, name: str, summary: dict, rows: Iterable[InvoiceRow]) -> int:
        self.backup_database("before_save_result")
        cur = self.conn.cursor()
        cur.execute("INSERT INTO datasets(name, summary_json) VALUES (?, ?)", (name, json.dumps(summary)))
        dataset_id = int(cur.lastrowid)
        self.replace_rows(dataset_id, rows)
        return dataset_id

    def replace_rows(self, dataset_id: int, rows: Iterable[InvoiceRow]) -> None:
        cur = self.conn.cursor()
        cur.execute("DELETE FROM invoice_rows WHERE dataset_id=?", (dataset_id,))
        for row in rows:
            self._insert_row(cur, dataset_id, row)
        self.conn.commit()

    def _insert_row(self, cur: sqlite3.Cursor, dataset_id: int, row: InvoiceRow) -> None:
        d = row.to_dict()
        cur.execute(
            """
            INSERT INTO invoice_rows(
                dataset_id, row_id, source_file, sheet_name, excel_row_number,
                supplier_name, gstin, invoice_no, hsn_sac, hsn_valid, hsn_notes,
                recipient_gstin, all_gstins_json, self_invoice_flag, gstin_roles_note,
                invoice_series, invoice_sequence_no, invoice_gap_note, anomaly_note, suggested_correction,
                invoice_date, period,
                taxable_value, igst, cgst, sgst, cess, invoice_value,
                expected_invoice_value, difference_amount, difference_percent,
                mismatch_reason, audit_status, audit_severity, audit_indicator,
                audit_notes, review_required, review_decision, include_in_totals,
                reconstructed, duplicate_key, raw_snapshot_json,
                detected_snapshot_json, final_snapshot_json
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                dataset_id, d["row_id"], d["source_file"], d["sheet_name"], d["excel_row_number"],
                d["supplier_name"], d["gstin"], d["invoice_no"], d.get("hsn_sac", ""), int(bool(d.get("hsn_valid", False))), d.get("hsn_notes", ""),
                d.get("recipient_gstin", ""), json.dumps(d.get("all_gstins", [])), int(bool(d.get("self_invoice_flag", False))), d.get("gstin_roles_note", ""),
                d.get("invoice_series", ""), d.get("invoice_sequence_no") or None, d.get("invoice_gap_note", ""), d.get("anomaly_note", ""), d.get("suggested_correction", ""),
                d["invoice_date"], d.get("period", ""),
                str(d["taxable_value"]), str(d["igst"]), str(d["cgst"]), str(d["sgst"]), str(d["cess"]), str(d["invoice_value"]),
                str(d["expected_invoice_value"]), str(d["difference_amount"]), str(d.get("difference_percent", 0)),
                d["mismatch_reason"], d["audit_status"], d["audit_severity"], d["audit_indicator"],
                d["audit_notes"], int(d["review_required"]), d["review_decision"],
                int(d["include_in_totals"]), int(d["reconstructed"]), d.get("duplicate_key", ""),
                json.dumps(d["raw_snapshot"]), json.dumps(d["detected_snapshot"]), json.dumps(d["final_snapshot"]),
            ),
        )

    def update_dataset_summary(self, dataset_id: int, summary: dict) -> None:
        self.conn.execute("UPDATE datasets SET summary_json=? WHERE id=?", (json.dumps(summary), dataset_id))
        self.conn.commit()

    def _latest_decision_hash(self, dataset_id: int) -> str:
        row = self.conn.execute(
            "SELECT decision_hash FROM review_decisions WHERE dataset_id=? ORDER BY id DESC LIMIT 1",
            (dataset_id,),
        ).fetchone()
        return str(row["decision_hash"] or "GENESIS") if row else "GENESIS"

    @staticmethod
    def _decision_hash(previous_hash: str, dataset_id: int, row_id: int, decision: str, include_in_totals: bool, note: str, decided_at: str) -> str:
        payload = "|".join([
            previous_hash,
            str(dataset_id),
            str(row_id),
            decision,
            "1" if include_in_totals else "0",
            note or "",
            decided_at,
        ])
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _append_review_decision(self, dataset_id: int, row_id: int, decision: str, include_in_totals: bool, note: str) -> None:
        decided_at = datetime.now().isoformat(timespec="seconds")
        previous_hash = self._latest_decision_hash(dataset_id)
        decision_hash = self._decision_hash(previous_hash, dataset_id, row_id, decision, include_in_totals, note, decided_at)
        self.conn.execute(
            """
            INSERT INTO review_decisions(dataset_id, row_id, decision, include_in_totals, note, decided_at, previous_hash, decision_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (dataset_id, row_id, decision, int(include_in_totals), note, decided_at, previous_hash, decision_hash),
        )

    def update_review_decision(
        self,
        dataset_id: int,
        row_id: int,
        decision: str,
        include_in_totals: bool,
        status: str,
        indicator: str,
        review_required: bool,
        note: str = "",
    ) -> None:
        self.backup_database("before_review_decision")
        suffix = f"; Review note: {note}" if note else ""
        self.conn.execute(
            """
            UPDATE invoice_rows
            SET review_decision=?, include_in_totals=?, audit_status=?, audit_indicator=?,
                review_required=?, audit_notes=audit_notes || ?, updated_at=CURRENT_TIMESTAMP
            WHERE dataset_id=? AND row_id=?
            """,
            (decision, int(include_in_totals), status, indicator, int(review_required), suffix, dataset_id, row_id),
        )
        self._append_review_decision(dataset_id, row_id, decision, include_in_totals, note)
        self.conn.commit()

    def update_review_decisions_bulk(
        self,
        dataset_id: int,
        row_ids: Iterable[int],
        decision: str,
        include_in_totals: bool,
        status: str,
        indicator: str,
        review_required: bool,
        note: str = "",
    ) -> int:
        self.backup_database("before_bulk_review")
        count = 0
        for row_id in row_ids:
            suffix = f"; Bulk review note: {note}" if note else "; Bulk review decision saved."
            self.conn.execute(
                """
                UPDATE invoice_rows
                SET review_decision=?, include_in_totals=?, audit_status=?, audit_indicator=?,
                    review_required=?, audit_notes=audit_notes || ?, updated_at=CURRENT_TIMESTAMP
                WHERE dataset_id=? AND row_id=?
                """,
                (decision, int(include_in_totals), status, indicator, int(review_required), suffix, dataset_id, int(row_id)),
            )
            self._append_review_decision(dataset_id, int(row_id), decision, include_in_totals, note)
            count += 1
        self.conn.commit()
        return count


    def verify_review_decision_chain(self, dataset_id: int) -> tuple[bool, list[str]]:
        """Verify that saved review decisions form an unbroken SHA-256 hash chain."""
        rows = self.conn.execute(
            """
            SELECT id, row_id, decision, include_in_totals, note, decided_at, previous_hash, decision_hash
            FROM review_decisions
            WHERE dataset_id=?
            ORDER BY id
            """,
            (dataset_id,),
        ).fetchall()
        problems: list[str] = []
        expected_previous = "GENESIS"
        for record in rows:
            previous_hash = str(record["previous_hash"] or "")
            if previous_hash != expected_previous:
                problems.append(f"Decision {record['id']} previous_hash mismatch.")
            recomputed = self._decision_hash(
                previous_hash,
                dataset_id,
                int(record["row_id"]),
                str(record["decision"]),
                bool(record["include_in_totals"]),
                str(record["note"] or ""),
                str(record["decided_at"]),
            )
            if recomputed != str(record["decision_hash"] or ""):
                problems.append(f"Decision {record['id']} decision_hash mismatch.")
            expected_previous = str(record["decision_hash"] or "")
        return not problems, problems

    def latest_dataset_id(self) -> Optional[int]:
        row = self.conn.execute("SELECT id FROM datasets ORDER BY id DESC LIMIT 1").fetchone()
        return int(row["id"]) if row else None

    def load_rows(self, dataset_id: int) -> List[InvoiceRow]:
        rows = self.conn.execute(
            "SELECT * FROM invoice_rows WHERE dataset_id=? ORDER BY row_id", (dataset_id,)
        ).fetchall()
        return [self._row_from_db(r) for r in rows]

    def dataset_name(self, dataset_id: int) -> str:
        row = self.conn.execute("SELECT name FROM datasets WHERE id=?", (dataset_id,)).fetchone()
        return str(row["name"]) if row else f"Dataset {dataset_id}"

    def _row_from_db(self, r: sqlite3.Row) -> InvoiceRow:
        inv_date = None
        if r["invoice_date"]:
            try:
                inv_date = date.fromisoformat(r["invoice_date"])
            except Exception:
                inv_date = None
        row = InvoiceRow(
            row_id=int(r["row_id"]),
            source_file=r["source_file"] or "",
            sheet_name=r["sheet_name"] or "",
            excel_row_number=int(r["excel_row_number"] or 0),
            raw_snapshot=_json_loads(r["raw_snapshot_json"], []),
            supplier_name=r["supplier_name"] or "",
            gstin=r["gstin"] or "",
            invoice_no=r["invoice_no"] or "",
            hsn_sac=_row_get(r, "hsn_sac", "") or "",
            hsn_valid=bool(_row_get(r, "hsn_valid", 0)),
            hsn_notes=_row_get(r, "hsn_notes", "") or "",
            recipient_gstin=_row_get(r, "recipient_gstin", "") or "",
            all_gstins=tuple(_json_loads(_row_get(r, "all_gstins_json", "[]"), [])),
            self_invoice_flag=bool(_row_get(r, "self_invoice_flag", 0)),
            gstin_roles_note=_row_get(r, "gstin_roles_note", "") or "",
            invoice_series=_row_get(r, "invoice_series", "") or "",
            invoice_sequence_no=_row_get(r, "invoice_sequence_no", None),
            invoice_gap_note=_row_get(r, "invoice_gap_note", "") or "",
            anomaly_note=_row_get(r, "anomaly_note", "") or "",
            suggested_correction=_row_get(r, "suggested_correction", "") or "",
            invoice_date=inv_date,
            period=r["period"] or "",
            taxable_value=_decimal(r["taxable_value"]),
            igst=_decimal(r["igst"]),
            cgst=_decimal(r["cgst"]),
            sgst=_decimal(r["sgst"]),
            cess=_decimal(r["cess"]),
            invoice_value=_decimal(r["invoice_value"]),
            expected_invoice_value=_decimal(r["expected_invoice_value"]),
            difference_amount=_decimal(r["difference_amount"]),
            difference_percent=_decimal(r["difference_percent"]),
            mismatch_reason=r["mismatch_reason"] or "",
            audit_status=r["audit_status"] or "PENDING",
            audit_severity=r["audit_severity"] or "LOW",
            audit_indicator=r["audit_indicator"] or "⚪",
            audit_notes=r["audit_notes"] or "",
            review_required=bool(r["review_required"]),
            review_decision=r["review_decision"] or "NOT_REQUIRED",
            include_in_totals=bool(r["include_in_totals"]),
            reconstructed=bool(r["reconstructed"]),
            duplicate_key=r["duplicate_key"] or "",
        )
        row.detected_snapshot = _json_loads(r["detected_snapshot_json"], {})
        row.final_snapshot = _json_loads(r["final_snapshot_json"], {})
        return row

    def close(self) -> None:
        if getattr(self, "conn", None) is not None:
            self.conn.close()
            self.conn = None

    def __del__(self) -> None:
        # Best-effort cleanup for tests and abnormal GUI shutdown. Explicit
        # closeEvent/context-manager shutdown remains the primary path.
        try:
            self.close()
        except Exception:
            pass

    def __enter__(self) -> "AuditDatabase":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
