from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple


NOTE_MAX_LENGTH = 2000


@dataclass
class InvoiceRow:
    row_id: int
    source_file: str
    sheet_name: str
    excel_row_number: int
    raw_snapshot: List[str]

    supplier_name: str = ""
    gstin: str = ""
    invoice_no: str = ""
    hsn_sac: str = ""
    hsn_valid: bool = False
    hsn_notes: str = ""
    recipient_gstin: str = ""
    all_gstins: Tuple[str, ...] = field(default_factory=tuple)
    self_invoice_flag: bool = False
    gstin_roles_note: str = ""
    invoice_series: str = ""
    invoice_sequence_no: Optional[int] = None
    invoice_gap_note: str = ""
    anomaly_note: str = ""
    suggested_correction: str = ""
    invoice_date: Optional[date] = None
    period: str = ""

    taxable_value: Decimal = Decimal("0.00")
    igst: Decimal = Decimal("0.00")
    cgst: Decimal = Decimal("0.00")
    sgst: Decimal = Decimal("0.00")
    cess: Decimal = Decimal("0.00")
    invoice_value: Decimal = Decimal("0.00")

    expected_invoice_value: Decimal = Decimal("0.00")
    difference_amount: Decimal = Decimal("0.00")
    difference_percent: Decimal = Decimal("0.00")
    mismatch_reason: str = ""

    audit_status: str = "PENDING"
    audit_severity: str = "LOW"
    audit_indicator: str = "⚪"
    audit_notes: str = ""
    review_required: bool = False
    review_decision: str = "NOT_REQUIRED"
    include_in_totals: bool = False
    reconstructed: bool = False
    duplicate_key: str = ""

    detected_snapshot: Dict[str, Any] = field(default_factory=dict)
    final_snapshot: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Frozen is not used here because review decisions mutate row state in the UI,
        # but all_gstins must still be immutable to prevent hidden shared-state edits.
        if not isinstance(self.all_gstins, tuple):
            self.all_gstins = tuple(str(v) for v in (self.all_gstins or ()))
        if self.include_in_totals and self.review_required:
            raise ValueError("InvoiceRow cannot be both included in totals and review_required")

    def append_audit_note(self, note: str) -> None:
        """Append one audit note once, with a hard cap to avoid unbounded growth."""
        clean = str(note or "").strip()
        if not clean or clean in self.audit_notes:
            return
        combined = f"{self.audit_notes}; {clean}" if self.audit_notes else clean
        self.audit_notes = combined[:NOTE_MAX_LENGTH]

    def validate_state(self) -> None:
        """Validate mutable row invariants after UI or engine state changes."""
        if self.include_in_totals and self.review_required:
            raise ValueError("InvoiceRow cannot be both included in totals and review_required")

    def apply_review_decision(
        self,
        accepted: bool,
        decision_str: str,
        status_str: str,
        indicator: str,
        note: str = "",
    ) -> None:
        """Apply a manual review decision atomically.

        The include_in_totals/review_required invariant must never depend on
        scattered UI-layer assignment order.
        """
        self.review_required = False
        self.include_in_totals = bool(accepted)
        self.review_decision = decision_str
        self.audit_status = status_str
        self.audit_indicator = indicator
        self.append_audit_note("Bulk manual review decision saved." + (f" {note}" if note else ""))
        self.validate_state()

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        for key in [
            "taxable_value", "igst", "cgst", "sgst", "cess", "invoice_value",
            "expected_invoice_value", "difference_amount", "difference_percent",
        ]:
            data[key] = float(getattr(self, key))
        data["all_gstins"] = list(self.all_gstins)
        data["invoice_sequence_no"] = self.invoice_sequence_no if self.invoice_sequence_no is not None else ""
        data["invoice_date"] = self.invoice_date.isoformat() if self.invoice_date else ""
        return data


@dataclass
class AuditSummary:
    files_processed: int = 0
    sheets_processed: int = 0
    raw_rows_read: int = 0
    classified_rows: int = 0
    official_invoice_rows: int = 0
    valid_rows: int = 0
    accepted_warning_rows: int = 0
    review_required_rows: int = 0
    skipped_rows: int = 0
    duplicate_rows: int = 0
    final_approved_rows: int = 0
    gst_mismatch_rows: int = 0
    high_severity_rows: int = 0
    critical_rows: int = 0

    approved_invoice_value: Decimal = Decimal("0.00")
    review_invoice_value: Decimal = Decimal("0.00")
    excluded_invoice_value: Decimal = Decimal("0.00")
    raw_detected_invoice_value: Decimal = Decimal("0.00")
    approved_taxable_value: Decimal = Decimal("0.00")
    approved_igst: Decimal = Decimal("0.00")
    approved_cgst: Decimal = Decimal("0.00")
    approved_sgst: Decimal = Decimal("0.00")
    approved_cess: Decimal = Decimal("0.00")
    approved_total_gst: Decimal = Decimal("0.00")
    # Approved counters power official dashboard totals. Detected counters show
    # source-file coverage, including rows held back for review or duplicates.
    unique_suppliers: int = 0
    unique_gstins: int = 0
    detected_unique_suppliers: int = 0
    detected_unique_gstins: int = 0

    row_coverage_status: str = "UNKNOWN"
    amount_reconciliation_status: str = "UNKNOWN"
    final_status: str = "UNKNOWN"

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        for key, value in list(data.items()):
            if isinstance(value, Decimal):
                data[key] = float(value)
        return data


@dataclass
class AuditResult:
    rows: List[InvoiceRow]
    summary: AuditSummary
    source_totals: Dict[str, Decimal]
    month_totals: Dict[str, Decimal]
    supplier_totals: Dict[str, Decimal]
