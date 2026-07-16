from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Iterable, Literal

from app.core.models import InvoiceRow
from app.core.review_policy import (
    CLEAN_REASONS,
    CRITICAL_REASONS,
    MANDATORY_REVIEW_AMOUNT,
    has_gst_or_amount_exception,
    has_required_amount_problem,
    has_required_identity_problem,
    is_advisory_exception,
    is_empty_or_noise_row,
    is_mandatory_review,
    is_trace_only,
)

ReviewBucket = Literal["MANDATORY_REVIEW", "ADVISORY_REVIEW", "TRACE_ONLY", "APPROVED", "MATCHED"]


@dataclass(frozen=True)
class ReviewQueueItem:
    """UI-safe review queue record.

    The dashboard should render these records instead of re-deciding review
    severity in the UI layer. This keeps the audit queue deterministic and
    prevents empty rows, page headers, and tiny rounding differences from being
    shown as blocking issues.
    """

    row_id: int
    bucket: ReviewBucket
    priority_score: int
    supplier_name: str
    gstin: str
    invoice_no: str
    issue_type: str
    expected_value: Decimal
    actual_value: Decimal
    difference_amount: Decimal
    difference_percent: Decimal
    status: str
    severity: str
    reason: str
    notes: str
    source_file: str
    sheet_name: str
    excel_row_number: int
    can_block_export: bool
    actions: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ReviewQueueSummary:
    total_rows: int
    mandatory_count: int
    advisory_count: int
    trace_only_count: int
    approved_count: int
    matched_count: int
    blocking_invoice_value: Decimal
    blocking_difference_value: Decimal
    top_issue_types: tuple[tuple[str, int], ...]

    @property
    def export_blocked(self) -> bool:
        return self.mandatory_count > 0


def _clean(text: object, fallback: str = "") -> str:
    value = str(text or "").strip()
    return value if value else fallback


def _issue_type(row: InvoiceRow) -> str:
    reason = _clean(row.mismatch_reason).upper()
    notes = _clean(row.audit_notes).upper()
    status = _clean(row.audit_status).upper()

    if has_required_identity_problem(row):
        if "GSTIN" in notes or not row.gstin:
            return "GSTIN / tax identity problem"
        if "INVOICE" in notes or not row.invoice_no:
            return "Invoice number identity problem"
        return "Supplier identity problem"
    if reason in CRITICAL_REASONS or has_required_amount_problem(row):
        if "GST" in reason or "COMPONENT" in reason:
            return "GST component mismatch"
        if row.invoice_value < row.taxable_value:
            return "Invoice value below taxable value"
        return "Material amount mismatch"
    if is_advisory_exception(row):
        if "FREIGHT" in reason or "DISCOUNT" in reason:
            return "Freight / discount advisory"
        if "TCS" in reason or "TDS" in reason:
            return "TCS / TDS advisory"
        return "Low-risk exception"
    if is_trace_only(row) or is_empty_or_noise_row(row):
        if "DUPLICATE" in status:
            return "Duplicate / excluded trace"
        return "Empty / skipped trace"
    return "Matched / approved"


def _bucket(row: InvoiceRow) -> ReviewBucket:
    if is_mandatory_review(row):
        return "MANDATORY_REVIEW"
    if is_advisory_exception(row):
        return "ADVISORY_REVIEW"
    # Clean rounding/balanced reasons are not human-review items even when the
    # source row was initially flagged during parsing. Keep them searchable but
    # out of the blocking and trace/noise lanes.
    if str(row.mismatch_reason or "").upper() in CLEAN_REASONS:
        return "MATCHED"
    if is_trace_only(row) or is_empty_or_noise_row(row):
        return "TRACE_ONLY"
    if row.include_in_totals:
        return "APPROVED"
    return "MATCHED"


def _priority_score(row: InvoiceRow, bucket: ReviewBucket) -> int:
    if bucket == "MANDATORY_REVIEW":
        score = 100
        if has_required_identity_problem(row):
            score += 50
        if has_required_amount_problem(row):
            score += 40
        if str(row.audit_severity).upper() == "CRITICAL":
            score += 30
        elif str(row.audit_severity).upper() == "HIGH":
            score += 20
        # Material amount raises sorting priority without letting one huge invoice
        # hide identity defects entirely.
        score += min(int(abs(row.difference_amount) / Decimal("1000")), 40)
        return score
    if bucket == "ADVISORY_REVIEW":
        score = 50 + min(int(abs(row.difference_amount) / Decimal("1000")), 20)
        if has_gst_or_amount_exception(row):
            score += 10
        return score
    if bucket == "TRACE_ONLY":
        return 10
    return 0


def _actions(bucket: ReviewBucket) -> tuple[str, ...]:
    if bucket == "MANDATORY_REVIEW":
        return ("Open Invoice", "Accept With Note", "Fix Values", "Reject / Exclude", "Export Issue")
    if bucket == "ADVISORY_REVIEW":
        return ("Open Invoice", "Accept Advisory", "Promote To Mandatory", "Ignore")
    if bucket == "TRACE_ONLY":
        return ("Open Trace", "Keep Excluded")
    return ("Open Invoice",)


def make_review_queue_item(row: InvoiceRow) -> ReviewQueueItem:
    bucket = _bucket(row)
    return ReviewQueueItem(
        row_id=row.row_id,
        bucket=bucket,
        priority_score=_priority_score(row, bucket),
        supplier_name=_clean(row.supplier_name, "UNKNOWN SUPPLIER"),
        gstin=_clean(row.gstin, "NO GSTIN"),
        invoice_no=_clean(row.invoice_no, "NO INVOICE NO"),
        issue_type=_issue_type(row),
        expected_value=row.expected_invoice_value,
        actual_value=row.invoice_value,
        difference_amount=abs(row.difference_amount),
        difference_percent=abs(row.difference_percent),
        status=_clean(row.audit_status, "UNKNOWN"),
        severity=_clean(row.audit_severity, "LOW").upper(),
        reason=_clean(row.mismatch_reason, "NO MISMATCH"),
        notes=_clean(row.audit_notes),
        source_file=_clean(row.source_file),
        sheet_name=_clean(row.sheet_name),
        excel_row_number=row.excel_row_number,
        can_block_export=bucket == "MANDATORY_REVIEW",
        actions=_actions(bucket),
    )


def build_review_queue(rows: Iterable[InvoiceRow], *, include_non_blocking: bool = True) -> list[ReviewQueueItem]:
    items = [make_review_queue_item(row) for row in rows]
    if not include_non_blocking:
        items = [item for item in items if item.bucket == "MANDATORY_REVIEW"]
    return sorted(
        items,
        key=lambda item: (
            0 if item.bucket == "MANDATORY_REVIEW" else 1 if item.bucket == "ADVISORY_REVIEW" else 2,
            -item.priority_score,
            item.supplier_name,
            item.invoice_no,
            item.row_id,
        ),
    )


def summarize_review_queue(items: Iterable[ReviewQueueItem]) -> ReviewQueueSummary:
    item_list = list(items)
    counts: dict[str, int] = {"MANDATORY_REVIEW": 0, "ADVISORY_REVIEW": 0, "TRACE_ONLY": 0, "APPROVED": 0, "MATCHED": 0}
    issue_counts: dict[str, int] = {}
    blocking_invoice_value = Decimal("0.00")
    blocking_difference_value = Decimal("0.00")
    for item in item_list:
        counts[item.bucket] += 1
        issue_counts[item.issue_type] = issue_counts.get(item.issue_type, 0) + 1
        if item.can_block_export:
            blocking_invoice_value += item.actual_value
            blocking_difference_value += item.difference_amount
    top = tuple(sorted(issue_counts.items(), key=lambda pair: (-pair[1], pair[0]))[:8])
    return ReviewQueueSummary(
        total_rows=len(item_list),
        mandatory_count=counts["MANDATORY_REVIEW"],
        advisory_count=counts["ADVISORY_REVIEW"],
        trace_only_count=counts["TRACE_ONLY"],
        approved_count=counts["APPROVED"],
        matched_count=counts["MATCHED"],
        blocking_invoice_value=blocking_invoice_value,
        blocking_difference_value=blocking_difference_value,
        top_issue_types=top,
    )
