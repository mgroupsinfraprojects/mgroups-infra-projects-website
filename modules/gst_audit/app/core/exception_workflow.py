from __future__ import annotations

from dataclasses import dataclass, asdict
from decimal import Decimal
from typing import Iterable, Sequence

import pandas as pd

from app.core.models import AuditResult, InvoiceRow


@dataclass(frozen=True)
class ExceptionGroup:
    reason: str
    severity: str
    row_count: int
    invoice_value_total: Decimal
    difference_total: Decimal
    suggested_action: str

    def to_dict(self) -> dict:
        data = asdict(self)
        data["invoice_value_total"] = float(self.invoice_value_total)
        data["difference_total"] = float(self.difference_total)
        return data


def exception_reason(row: InvoiceRow) -> str:
    if row.audit_status.startswith("ERROR"):
        return "File / row could not be read"
    if row.audit_status.startswith("SKIPPED"):
        return "Skipped or excluded row"
    if row.self_invoice_flag:
        return "Self-invoice / own GSTIN detected"
    if row.audit_severity in {"HIGH", "CRITICAL"}:
        return row.mismatch_reason or row.audit_status or "High-severity audit issue"
    if row.mismatch_reason and row.mismatch_reason not in {"BALANCED_OR_ROUNDING", "MINOR_ROUNDING_OR_DECIMAL_ISSUE"}:
        return row.mismatch_reason
    if row.review_required:
        return row.audit_status or "Review required"
    return "No exception"


def suggested_exception_action(reason: str, severity: str) -> str:
    reason_upper = reason.upper()
    if "SELF" in reason_upper:
        return "Confirm whether this is an internal/self invoice. Exclude if it should not affect ITC/revenue totals."
    if "GSTIN" in reason_upper:
        return "Verify supplier GSTIN against source invoice/GST portal before approval."
    if "MISMATCH" in reason_upper or "DIFFER" in reason_upper or "ROUND" in reason_upper:
        return "Compare taxable, tax and invoice values. Accept only if variance is explained and documented."
    if "SKIPPED" in reason_upper or "EXCLUDED" in reason_upper:
        return "Check source row. Include only after fields are corrected or manually accepted."
    if severity == "CRITICAL":
        return "Do not finalize until corrected or formally documented by reviewer."
    return "Review source row, add reviewer note, then accept or reject."


def group_exceptions(rows: Sequence[InvoiceRow]) -> list[ExceptionGroup]:
    grouped: dict[tuple[str, str], dict[str, object]] = {}
    for row in rows:
        if row.include_in_totals and not row.review_required and row.audit_severity not in {"HIGH", "CRITICAL"}:
            continue
        reason = exception_reason(row)
        severity = row.audit_severity or "LOW"
        key = (reason, severity)
        item = grouped.setdefault(key, {
            "reason": reason,
            "severity": severity,
            "row_count": 0,
            "invoice_value_total": Decimal("0.00"),
            "difference_total": Decimal("0.00"),
            "suggested_action": suggested_exception_action(reason, severity),
        })
        item["row_count"] = int(item["row_count"]) + 1
        item["invoice_value_total"] = item["invoice_value_total"] + row.invoice_value  # type: ignore[operator]
        item["difference_total"] = item["difference_total"] + row.difference_amount  # type: ignore[operator]
    groups = [ExceptionGroup(**item) for item in grouped.values()]  # type: ignore[arg-type]
    severity_rank = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    return sorted(groups, key=lambda g: (severity_rank.get(g.severity, 9), -g.row_count, g.reason))


def exception_summary_dataframe(result: AuditResult) -> pd.DataFrame:
    return pd.DataFrame([group.to_dict() for group in group_exceptions(result.rows)])


def review_queue_dataframe(rows: Iterable[InvoiceRow]) -> pd.DataFrame:
    data = []
    for row in rows:
        if not (row.review_required or row.audit_severity in {"HIGH", "CRITICAL"} or row.audit_status.startswith("SKIPPED") or row.audit_status.startswith("ERROR")):
            continue
        data.append({
            "source_file": row.source_file,
            "sheet_name": row.sheet_name,
            "excel_row_number": row.excel_row_number,
            "supplier_name": row.supplier_name,
            "gstin": row.gstin,
            "invoice_no": row.invoice_no,
            "invoice_value": float(row.invoice_value),
            "difference_amount": float(row.difference_amount),
            "severity": row.audit_severity,
            "reason": exception_reason(row),
            "suggested_action": suggested_exception_action(exception_reason(row), row.audit_severity),
            "review_decision": row.review_decision,
            "include_in_totals": row.include_in_totals,
        })
    return pd.DataFrame(data)


def final_lock_checklist(result: AuditResult) -> pd.DataFrame:
    s = result.summary
    rows = [
        ("Row coverage", s.row_coverage_status == "MATCHED", s.row_coverage_status, "Raw rows read must equal classified rows."),
        ("Amount reconciliation", s.amount_reconciliation_status == "MATCHED", s.amount_reconciliation_status, "Approved + review + excluded must equal raw detected total."),
        ("Critical rows", s.critical_rows == 0, s.critical_rows, "Critical rows should be zero before final sign-off."),
        ("Review rows", s.review_required_rows == 0, s.review_required_rows, "Open review rows must be accepted, rejected, or documented."),
        ("High severity rows", s.high_severity_rows == 0, s.high_severity_rows, "High-severity exceptions require reviewer notes."),
    ]
    return pd.DataFrame(rows, columns=["control", "passed", "current_value", "required_action"])


def can_lock_final(result: AuditResult) -> bool:
    checklist = final_lock_checklist(result)
    return bool(checklist["passed"].all())
