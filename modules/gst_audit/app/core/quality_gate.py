from __future__ import annotations

from dataclasses import dataclass, asdict
from decimal import Decimal
from typing import Iterable

import pandas as pd

from app.core.models import AuditResult, InvoiceRow


@dataclass(frozen=True)
class QualityGateItem:
    """One reviewer-facing release/audit control result.

    This is intentionally business-readable: it is used in the Excel export,
    pre-final review, and regression tests. It does not mutate the audit result.
    """

    control: str
    status: str
    severity: str
    current_value: str
    required_action: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


PASS = "PASS"
WARN = "WARN"
FAIL = "FAIL"


def _money(value: Decimal) -> str:
    return f"{value:.2f}"


def _has_source_traceability(rows: Iterable[InvoiceRow]) -> bool:
    rows = list(rows)
    if not rows:
        return False
    material_rows = [row for row in rows if not row.audit_status.startswith("SKIPPED")]
    return all(row.source_file and row.sheet_name and row.excel_row_number > 0 for row in material_rows)


def quality_gate_items(result: AuditResult) -> list[QualityGateItem]:
    """Return professional finalization controls for a completed audit run."""

    s = result.summary
    items: list[QualityGateItem] = []

    items.append(QualityGateItem(
        "Row coverage",
        PASS if s.row_coverage_status == "MATCHED" else FAIL,
        "CRITICAL",
        s.row_coverage_status,
        "Raw rows read must equal classified rows before any report is trusted.",
    ))
    items.append(QualityGateItem(
        "Amount reconciliation",
        PASS if s.amount_reconciliation_status == "MATCHED" else FAIL,
        "CRITICAL",
        s.amount_reconciliation_status,
        "Approved + review + excluded invoice values must reconcile to raw detected invoice value.",
    ))
    items.append(QualityGateItem(
        "Critical row isolation",
        PASS if s.critical_rows == 0 else FAIL,
        "CRITICAL",
        str(s.critical_rows),
        "Critical unreadable/corrupt/error rows must be corrected or formally documented.",
    ))
    items.append(QualityGateItem(
        "Open review queue",
        PASS if s.review_required_rows == 0 else WARN,
        "HIGH",
        str(s.review_required_rows),
        "Every review-required row should be accepted, rejected, or documented before final sign-off.",
    ))
    items.append(QualityGateItem(
        "High-severity exception queue",
        PASS if s.high_severity_rows == 0 else WARN,
        "HIGH",
        str(s.high_severity_rows),
        "High-severity GST, amount, GSTIN, or column-shift issues require reviewer notes.",
    ))
    items.append(QualityGateItem(
        "GST mismatch visibility",
        PASS if s.gst_mismatch_rows == 0 else WARN,
        "MEDIUM",
        str(s.gst_mismatch_rows),
        "GST mismatch rows remain visible in the exception sheets; do not hide them from export.",
    ))
    items.append(QualityGateItem(
        "Duplicate control",
        PASS if s.duplicate_rows == 0 else WARN,
        "MEDIUM",
        str(s.duplicate_rows),
        "Duplicate invoices are excluded from official totals and should be reviewed when material.",
    ))
    items.append(QualityGateItem(
        "Source traceability",
        PASS if _has_source_traceability(result.rows) else FAIL,
        "HIGH",
        f"{len(result.rows)} classified row(s)",
        "Every material row must retain source file, sheet, and Excel row number.",
    ))
    items.append(QualityGateItem(
        "Approved total basis",
        PASS if s.final_approved_rows > 0 or s.raw_detected_invoice_value == 0 else WARN,
        "MEDIUM",
        f"approved_rows={s.final_approved_rows}; approved_value={_money(s.approved_invoice_value)}",
        "Official dashboard/export totals must be based only on include_in_totals=True rows.",
    ))
    items.append(QualityGateItem(
        "Spreadsheet injection guard",
        PASS,
        "HIGH",
        "enabled",
        "Formula-like text values are neutralized before Excel export.",
    ))

    items.append(QualityGateItem(
        "Final lock readiness",
        PASS if s.final_status == "FULLY_VERIFIED" else WARN,
        "HIGH",
        s.final_status,
        "FULLY_VERIFIED is required for a clean final report; other states require reviewer sign-off.",
    ))
    return items


def quality_gate_dataframe(result: AuditResult) -> pd.DataFrame:
    df = pd.DataFrame([item.to_dict() for item in quality_gate_items(result)])
    if df.empty:
        return pd.DataFrame(columns=["gate", "status", "severity", "evidence", "required_action"])
    return df.rename(columns={"control": "gate", "current_value": "evidence"})[
        ["gate", "status", "severity", "evidence", "required_action"]
    ]


def quality_gate_score(result: AuditResult) -> int:
    """Return a conservative reviewer score from 0 to 100.

    FAIL costs more than WARN because it blocks trust in the output. The score
    is not marketing; it is a deterministic triage signal for the reviewer.
    """

    score = 100
    for item in quality_gate_items(result):
        if item.status == FAIL:
            score -= 18 if item.severity == "CRITICAL" else 12
        elif item.status == WARN:
            score -= 7 if item.severity in {"HIGH", "CRITICAL"} else 4
    return max(0, min(100, score))


def quality_gate_status(result: AuditResult) -> str:
    items = quality_gate_items(result)
    if any(item.status == FAIL for item in items):
        return "BLOCKED"
    if any(item.status == WARN for item in items):
        return "REVIEW_REQUIRED"
    return "READY_TO_LOCK"
