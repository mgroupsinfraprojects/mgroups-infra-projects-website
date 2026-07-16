from __future__ import annotations

import shutil
import tempfile
import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence

from app.core.audit_engine import InvoiceAuditEngine, SUPPORTED_EXTENSIONS
from app.core.exporter import export_verified_excel
from app.core.models import AuditResult, InvoiceRow
from app.core.review_policy import (
    has_financial_value,
    is_empty_or_noise_row,
    is_mandatory_review,
    is_meaningful_duplicate_row,
    is_real_invoice_candidate,
    is_support_or_summary_row,
)
from app.version import APP_NAME, APP_VERSION
from web_portal.audit_history import AuditEventStore


class WebAuditError(ValueError):
    """Raised for user-correctable web audit errors."""


@dataclass
class WebAuditSession:
    session_id: str
    result: AuditResult
    upload_paths: List[Path] = field(default_factory=list)
    export_path: Path | None = None


class WebAuditService:
    """Stateful browser-safe wrapper around the core GST audit engine.

    The service intentionally keeps audit rows in memory for the lightweight local
    web server. The premium web mode adds role-aware actions, audit event logging,
    executive summary payloads, and hardened file handling. For a hosted M-Groups
    portal, persist the same rows/events in the main database.
    """

    def __init__(self, runtime_dir: str | Path | None = None) -> None:
        base = Path(runtime_dir) if runtime_dir else Path(tempfile.gettempdir()) / "gst_audit_web_runtime"
        self.runtime_dir = base
        self.upload_dir = base / "uploads"
        self.export_dir = base / "exports"
        self.report_dir = base / "reports"
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.export_dir.mkdir(parents=True, exist_ok=True)
        self.report_dir.mkdir(parents=True, exist_ok=True)
        self.engine = InvoiceAuditEngine()
        self.events = AuditEventStore(base / "audit_events.jsonl")
        self.sessions: Dict[str, WebAuditSession] = {}

    def create_audit(self, files: Sequence[tuple[str, bytes]], actor: str = "web", role: str = "auditor") -> WebAuditSession:
        safe_files = self._validate_files(files)
        session_id = uuid.uuid4().hex
        target_dir = self.upload_dir / session_id
        target_dir.mkdir(parents=True, exist_ok=True)
        paths: List[Path] = []
        for filename, payload in safe_files:
            path = target_dir / filename
            path.write_bytes(payload)
            paths.append(path)
        result = self.engine.process_files([str(path) for path in paths])
        session = WebAuditSession(session_id=session_id, result=result, upload_paths=paths)
        self.sessions[session_id] = session
        self.events.record(
            actor,
            role,
            "audit_uploaded",
            session_id,
            files=[path.name for path in paths],
            rows=result.summary.raw_rows_read,
            review_rows=result.summary.review_required_rows,
            final_status=result.summary.final_status,
        )
        return session

    def get_session(self, session_id: str | None) -> WebAuditSession | None:
        if not session_id:
            return None
        return self.sessions.get(session_id)

    def apply_decision(
        self,
        session_id: str,
        row_ids: Iterable[int],
        action: str,
        note: str = "",
        actor: str = "web",
        role: str = "auditor",
    ) -> WebAuditSession:
        session = self._require_session(session_id)
        action_key = action.strip().lower()
        if action_key not in {"approve", "reject", "ignore"}:
            raise WebAuditError("Invalid review action. Use approve, reject, or ignore.")
        selected = {int(value) for value in row_ids}
        if not selected:
            raise WebAuditError("No rows selected for review decision.")

        affected = 0
        for row in session.result.rows:
            if row.row_id not in selected:
                continue
            affected += 1
            if action_key == "approve":
                row.apply_review_decision(True, "APPROVED_WEB", "VALID_ACCEPTED_BY_REVIEW", "✅", note or "Approved in web review.")
            elif action_key == "reject":
                row.apply_review_decision(False, "REJECTED_WEB", "REJECTED_BY_REVIEW", "❌", note or "Rejected in web review.")
            else:
                row.apply_review_decision(False, "IGNORED_WEB", "IGNORED_BY_REVIEW", "⚪", note or "Ignored in web review.")
        session.result = self.engine.recalculate_result(session.result)
        session.export_path = None
        self.events.record(actor, role, f"review_{action_key}", session_id, rows=affected, note=note[:250])
        return session

    def export_session(self, session_id: str, actor: str = "web", role: str = "auditor") -> Path:
        session = self._require_session(session_id)
        if session.export_path and session.export_path.exists():
            self.events.record(actor, role, "export_reused", session_id, file=session.export_path.name)
            return session.export_path
        output = self.export_dir / f"gst_audit_{session_id}.xlsx"
        export_verified_excel(session.result, output)
        session.export_path = output
        self.events.record(actor, role, "export_created", session_id, file=output.name, bytes=output.stat().st_size)
        return output

    def audit_log_csv(self) -> Path:
        return self.events.export_csv(self.report_dir / "gst_audit_web_activity_log.csv")

    def delete_session(self, session_id: str, actor: str = "web", role: str = "auditor") -> None:
        session = self.sessions.pop(session_id, None)
        if not session:
            return
        upload_parent = self.upload_dir / session_id
        if upload_parent.exists():
            shutil.rmtree(upload_parent, ignore_errors=True)
        if session.export_path and session.export_path.exists():
            session.export_path.unlink(missing_ok=True)
        self.events.record(actor, role, "session_cleared", session_id)

    def dashboard(self, session_id: str | None, user_payload: Mapping[str, object] | None = None) -> Mapping[str, object]:
        session = self.get_session(session_id)
        base_user = dict(user_payload or {"authenticated": False, "permissions": {}})
        if not session:
            return {
                "app_name": APP_NAME,
                "version": APP_VERSION,
                "has_result": False,
                "session_id": "",
                "user": base_user,
                "activity": self.events.recent(20),
            }
        payload = dict(self.result_payload(session))
        payload["user"] = base_user
        payload["activity"] = self.events.recent(20)
        return payload

    def result_payload(self, session: WebAuditSession) -> Mapping[str, object]:
        """Build the browser payload from strict invoice rows only.

        Web mode is intentionally stricter than the raw engine display. The user
        should not approve/read header bands, GSTR section labels, ITC summary
        lines, or empty support rows. Only rows with the minimum invoice identity
        are shown in web dashboards:

        supplier/company name + GSTIN + invoice number + invoice value.
        """
        result = session.result
        summary = result.summary
        invoice_rows = self._web_invoice_rows(result.rows)
        approved_rows = [row for row in invoice_rows if row.include_in_totals]
        review_rows = [row for row in invoice_rows if is_mandatory_review(row)]
        invoice_row_ids = {row.row_id for row in invoice_rows}
        trace_rows = [row for row in result.rows if row.row_id not in invoice_row_ids]
        suppliers = self._supplier_rows(invoice_rows)
        duplicate_rows = [row for row in invoice_rows if is_meaningful_duplicate_row(row)]
        mismatch_rows = [row for row in review_rows if str(row.mismatch_reason or "").strip()]
        high_risk_rows = [row for row in review_rows if (row.audit_severity or "").upper() in {"HIGH", "CRITICAL"} or row.review_required]

        approved_invoice_value = sum((row.invoice_value for row in approved_rows), Decimal("0.00"))
        approved_taxable_value = sum((row.taxable_value for row in approved_rows), Decimal("0.00"))
        approved_igst = sum((row.igst for row in approved_rows), Decimal("0.00"))
        approved_cgst = sum((row.cgst for row in approved_rows), Decimal("0.00"))
        approved_sgst = sum((row.sgst for row in approved_rows), Decimal("0.00"))
        approved_cess = sum((row.cess for row in approved_rows), Decimal("0.00"))
        approved_total_gst = approved_igst + approved_cgst + approved_sgst + approved_cess
        detected_invoice_value = sum((row.invoice_value for row in invoice_rows), Decimal("0.00"))
        detected_taxable_value = sum((row.taxable_value for row in invoice_rows), Decimal("0.00"))
        detected_total_gst = sum((row.igst + row.cgst + row.sgst + row.cess for row in invoice_rows), Decimal("0.00"))
        review_invoice_value = sum((row.invoice_value for row in review_rows), Decimal("0.00"))
        month_rows = self._month_rows(invoice_rows)
        source_rows = self._source_rows(invoice_rows)
        human_final_status = self._human_final_status(summary, len(review_rows))
        readiness_score = self._readiness_score_from_counts(
            len(review_rows),
            len(duplicate_rows),
            len(mismatch_rows),
            summary.row_coverage_status,
            summary.amount_reconciliation_status,
        )
        grade = self._grade(readiness_score, len(review_rows))
        verdict = self._human_verdict(len(review_rows))
        next_action = self._human_next_action(len(review_rows))

        return {
            "app_name": APP_NAME,
            "version": APP_VERSION,
            "has_result": True,
            "session_id": session.session_id,
            "files": [path.name for path in session.upload_paths],
            "summary": {
                "files_processed": summary.files_processed,
                "raw_rows_read": summary.raw_rows_read,
                "web_invoice_rows": len(invoice_rows),
                "approved_rows": len(approved_rows),
                "review_rows": len(review_rows),
                "engine_review_rows": summary.review_required_rows,
                "skipped_rows": summary.skipped_rows,
                "trace_rows": len(result.rows) - len(invoice_rows),
                "duplicate_rows": len(duplicate_rows),
                "critical_rows": len(high_risk_rows),
                "high_severity_rows": len(high_risk_rows),
                "gst_mismatch_rows": len(mismatch_rows),
                "suppliers": len({(row.gstin or row.supplier_name).strip().upper() for row in invoice_rows}),
                "approved_suppliers": len({(row.gstin or row.supplier_name).strip().upper() for row in approved_rows}),
                "invoice_value": self._money(approved_invoice_value),
                "taxable_value": self._money(approved_taxable_value),
                "total_gst": self._money(approved_total_gst),
                "detected_invoice_value": self._money(detected_invoice_value),
                "detected_taxable_value": self._money(detected_taxable_value),
                "detected_total_gst": self._money(detected_total_gst),
                "review_invoice_value": self._money(review_invoice_value),
                "final_status": human_final_status,
                "row_coverage_status": summary.row_coverage_status,
                "amount_reconciliation_status": summary.amount_reconciliation_status,
                "readiness_score": readiness_score,
                "readiness_grade": grade,
            },
            "executive": {
                "readiness_score": readiness_score,
                "grade": grade,
                "verdict": verdict,
                "blocked": len(review_rows) > 0,
                "risk_rows": len(high_risk_rows),
                "duplicate_rows": len(duplicate_rows),
                "recommended_next_action": next_action,
            },
            "review_rows": [self._row_payload(row) for row in review_rows[:500]],
            "approved_preview": [self._row_payload(row) for row in approved_rows[:250]],
            "invoice_rows": [self._row_payload(row) for row in invoice_rows[:2500]],
            "suppliers": suppliers[:500],
            "months": month_rows,
            "sources": source_rows,
        }

    def _require_session(self, session_id: str) -> WebAuditSession:
        session = self.sessions.get(session_id)
        if not session:
            raise WebAuditError("Audit session not found. Upload files again.")
        return session

    @staticmethod
    def _validate_files(files: Sequence[tuple[str, bytes]]) -> List[tuple[str, bytes]]:
        if not files:
            raise WebAuditError("Upload at least one Excel or CSV file.")
        safe: List[tuple[str, bytes]] = []
        seen: set[str] = set()
        total_bytes = 0
        for filename, payload in files:
            name = Path(str(filename or "")).name.strip().replace("\x00", "")
            if not name:
                raise WebAuditError("One uploaded file has no filename.")
            suffix = Path(name).suffix.lower()
            if suffix not in SUPPORTED_EXTENSIONS:
                raise WebAuditError(f"Unsupported file type for {name}. Use XLSX, XLSM, XLS, CSV, or TSV.")
            if not payload:
                raise WebAuditError(f"{name} is empty.")
            if len(payload) > 50 * 1024 * 1024:
                raise WebAuditError(f"{name} exceeds 50 MB web upload limit.")
            total_bytes += len(payload)
            if total_bytes > 250 * 1024 * 1024:
                raise WebAuditError("Total upload size exceeds 250 MB web-session limit.")
            if name.lower() in seen:
                stem = Path(name).stem
                suffix = Path(name).suffix
                name = f"{stem}_{len(seen)+1}{suffix}"
            seen.add(name.lower())
            safe.append((name, payload))
        return safe

    @staticmethod
    def _has_web_required_identity(row: InvoiceRow) -> bool:
        return bool(
            (getattr(row, "supplier_name", "") or "").strip()
            and (getattr(row, "gstin", "") or "").strip()
            and (getattr(row, "invoice_no", "") or "").strip()
        )

    @staticmethod
    def _has_invoice_value(row: InvoiceRow) -> bool:
        try:
            return abs(getattr(row, "invoice_value", Decimal("0.00"))) > Decimal("0.00")
        except Exception:
            return False

    @classmethod
    def _is_web_invoice_row(cls, row: InvoiceRow) -> bool:
        """Strict browser inclusion policy.

        The web dashboard/review screen shows only true invoice rows. Support
        headers and GSTR summary rows remain in engine proof/export evidence, but
        are not user-actionable in the browser module.
        """
        if is_empty_or_noise_row(row) or is_support_or_summary_row(row):
            return False
        if not cls._has_web_required_identity(row):
            return False
        if not cls._has_invoice_value(row):
            return False
        # A row can still be official even when the core engine did not include it
        # yet because it is pending review. Require financial value to avoid header
        # labels being treated as rows.
        return has_financial_value(row)

    @classmethod
    def _web_invoice_rows(cls, rows: Iterable[InvoiceRow]) -> List[InvoiceRow]:
        return [row for row in rows if cls._is_web_invoice_row(row)]

    @staticmethod
    def _month_key(row: InvoiceRow) -> str:
        if row.invoice_date:
            return row.invoice_date.strftime("%b %Y")
        period = str(getattr(row, "period", "") or "").strip()
        return period or "Unknown"

    @staticmethod
    def _source_key(row: InvoiceRow) -> str:
        return str(getattr(row, "source_file", "") or "Unknown")

    @classmethod
    def _group_rows(cls, rows: Iterable[InvoiceRow], key_fn) -> List[Mapping[str, object]]:
        grouped: Dict[str, Dict[str, object]] = {}
        for row in rows:
            key = key_fn(row)
            item = grouped.setdefault(key, {
                "label": key,
                "rows": 0,
                "approved_rows": 0,
                "review_rows": 0,
                "suppliers": set(),
                "invoice_value_raw": Decimal("0.00"),
                "taxable_value_raw": Decimal("0.00"),
                "gst_raw": Decimal("0.00"),
            })
            item["rows"] = int(item["rows"]) + 1
            if row.include_in_totals:
                item["approved_rows"] = int(item["approved_rows"]) + 1
                item["invoice_value_raw"] = item["invoice_value_raw"] + row.invoice_value  # type: ignore[operator]
                item["taxable_value_raw"] = item["taxable_value_raw"] + row.taxable_value  # type: ignore[operator]
                item["gst_raw"] = item["gst_raw"] + row.igst + row.cgst + row.sgst + row.cess  # type: ignore[operator]
            if is_mandatory_review(row):
                item["review_rows"] = int(item["review_rows"]) + 1
            supplier_key = (row.gstin or row.supplier_name or "UNKNOWN").strip().upper()
            item["suppliers"].add(supplier_key)  # type: ignore[union-attr]
        output: List[Mapping[str, object]] = []
        for item in grouped.values():
            output.append({
                "label": item["label"],
                "month": item["label"],
                "source": item["label"],
                "rows": item["rows"],
                "approved_rows": item["approved_rows"],
                "review_rows": item["review_rows"],
                "suppliers": len(item["suppliers"]),  # type: ignore[arg-type]
                "invoice_value": cls._money(item["invoice_value_raw"]),
                "taxable_value": cls._money(item["taxable_value_raw"]),
                "gst": cls._money(item["gst_raw"]),
                "value_raw": float(item["invoice_value_raw"]),
            })
        return sorted(output, key=lambda x: str(x["label"]))

    @classmethod
    def _month_rows(cls, rows: Iterable[InvoiceRow]) -> List[Mapping[str, object]]:
        return cls._group_rows(rows, cls._month_key)

    @classmethod
    def _source_rows(cls, rows: Iterable[InvoiceRow]) -> List[Mapping[str, object]]:
        return cls._group_rows(rows, cls._source_key)

    @staticmethod
    def _row_payload(row: InvoiceRow) -> Mapping[str, object]:
        return {
            "row_id": row.row_id,
            "source_file": row.source_file,
            "sheet_name": row.sheet_name,
            "excel_row_number": row.excel_row_number,
            "supplier_name": row.supplier_name,
            "gstin": row.gstin,
            "invoice_no": row.invoice_no,
            "invoice_date": row.invoice_date.isoformat() if row.invoice_date else "",
            "taxable_value": WebAuditService._money(row.taxable_value),
            "invoice_value": WebAuditService._money(row.invoice_value),
            "taxable_value": WebAuditService._money(row.taxable_value),
            "gst": WebAuditService._money(row.igst + row.cgst + row.sgst + row.cess),
            "igst": WebAuditService._money(row.igst),
            "cgst": WebAuditService._money(row.cgst),
            "sgst": WebAuditService._money(row.sgst),
            "cess": WebAuditService._money(row.cess),
            "difference": WebAuditService._money(row.difference_amount),
            "status": row.audit_status,
            "severity": row.audit_severity,
            "reason": row.mismatch_reason,
            "notes": row.audit_notes,
        }

    @staticmethod
    def _supplier_rows(rows: Iterable[InvoiceRow]) -> List[Mapping[str, object]]:
        by_key: Dict[str, Dict[str, object]] = {}
        for row in rows:
            key = (row.gstin or row.supplier_name or "UNKNOWN").strip().upper()
            item = by_key.setdefault(key, {
                "key": key,
                "supplier_name": row.supplier_name or "UNKNOWN",
                "gstin": row.gstin,
                "invoices": 0,
                "approved_rows": 0,
                "review_rows": 0,
                "invoice_value_raw": Decimal("0.00"),
                "taxable_value_raw": Decimal("0.00"),
                "gst_raw": Decimal("0.00"),
                "last_invoice": "",
                "last_date": "",
            })
            item["invoices"] = int(item["invoices"]) + 1
            if row.include_in_totals:
                item["approved_rows"] = int(item["approved_rows"]) + 1
                item["invoice_value_raw"] = item["invoice_value_raw"] + row.invoice_value  # type: ignore[operator]
                item["taxable_value_raw"] = item["taxable_value_raw"] + row.taxable_value  # type: ignore[operator]
                item["gst_raw"] = item["gst_raw"] + row.igst + row.cgst + row.sgst + row.cess  # type: ignore[operator]
            if is_mandatory_review(row):
                item["review_rows"] = int(item["review_rows"]) + 1
            if row.invoice_no:
                item["last_invoice"] = row.invoice_no
            if row.invoice_date:
                item["last_date"] = row.invoice_date.isoformat()
        output: List[Mapping[str, object]] = []
        for item in sorted(by_key.values(), key=lambda x: x["invoice_value_raw"], reverse=True):
            output.append({
                "key": item["key"],
                "supplier_name": item["supplier_name"],
                "gstin": item["gstin"],
                "invoices": item["invoices"],
                "approved_rows": item["approved_rows"],
                "review_rows": item["review_rows"],
                "invoice_value": WebAuditService._money(item["invoice_value_raw"]),
                "taxable_value": WebAuditService._money(item["taxable_value_raw"]),
                "gst": WebAuditService._money(item["gst_raw"]),
                "last_invoice": item["last_invoice"],
                "last_date": item["last_date"],
            })
        return output

    @staticmethod
    def _readiness_score_from_counts(
        review_rows: int,
        duplicate_rows: int,
        gst_mismatch_rows: int,
        row_coverage_status: str,
        amount_reconciliation_status: str,
    ) -> int:
        score = 100
        score -= min(45, int(review_rows) * 4)
        score -= min(15, int(duplicate_rows) * 3)
        score -= min(15, int(gst_mismatch_rows) * 2)
        if row_coverage_status != "MATCHED":
            score -= 15
        if amount_reconciliation_status != "MATCHED":
            score -= 10
        return max(0, min(100, score))

    @staticmethod
    def _human_final_status(summary: object, review_rows: int) -> str:
        if getattr(summary, "row_coverage_status", "") != "MATCHED" or getattr(summary, "amount_reconciliation_status", "") != "MATCHED":
            return "RECONCILIATION_FAILED"
        return "BALANCED_BUT_REVIEW_REQUIRED" if review_rows else "FULLY_VERIFIED"

    @staticmethod
    def _human_verdict(review_rows: int) -> str:
        if review_rows:
            return f"Final export should wait: {review_rows} invoice-level review row(s) remain."
        return "No invoice-level review rows remain. Headers and support rows are excluded from approval."

    @staticmethod
    def _human_next_action(review_rows: int) -> str:
        if review_rows:
            return "Open Review and resolve invoice-level issues only."
        return "Open report or export verified workbook."

    @staticmethod
    def _readiness_score(summary: object) -> int:
        score = 100
        score -= min(45, int(getattr(summary, "review_required_rows", 0)) * 4)
        score -= min(15, int(getattr(summary, "duplicate_rows", 0)) * 3)
        score -= min(15, int(getattr(summary, "gst_mismatch_rows", 0)) * 2)
        if getattr(summary, "row_coverage_status", "") != "PASS":
            score -= 10
        if getattr(summary, "amount_reconciliation_status", "") != "PASS":
            score -= 10
        return max(0, min(100, score))

    @staticmethod
    def _grade(score: int, review_rows: int) -> str:
        if review_rows > 0:
            return "Locked — Review Required"
        if score >= 95:
            return "A+ Ready"
        if score >= 85:
            return "A Ready"
        if score >= 75:
            return "B Usable"
        return "C Needs Work"

    @staticmethod
    def _verdict(summary: object) -> str:
        review_rows = int(getattr(summary, "review_required_rows", 0))
        if review_rows:
            return f"Final export should wait: {review_rows} review row(s) remain."
        status = getattr(summary, "final_status", "UNKNOWN")
        if "VERIFIED" in str(status).upper() or "BALANCED" in str(status).upper():
            return "Audit is balanced enough for management review/export."
        return "Audit processed; verify proof and export before statutory use."

    @staticmethod
    def _next_action(summary: object) -> str:
        if int(getattr(summary, "review_required_rows", 0)):
            return "Open Review, resolve critical rows, then export."
        if int(getattr(summary, "duplicate_rows", 0)):
            return "Check duplicate report before final submission."
        return "Download verified Excel and keep activity log with working papers."

    @staticmethod
    def _money(value: Decimal | int | float | str) -> str:
        try:
            dec = value if isinstance(value, Decimal) else Decimal(str(value or "0"))
        except Exception:
            dec = Decimal("0.00")
        return f"{dec.quantize(Decimal('0.01')):,.2f}"
