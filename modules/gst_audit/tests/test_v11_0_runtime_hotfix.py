from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from app.core.models import AuditResult, AuditSummary, InvoiceRow
from app.ui.main_window import MainWindow


def _row(row_id: int, *, include: bool, review: bool, status: str, reason: str = "", severity: str = "LOW", diff: str = "0.00") -> InvoiceRow:
    return InvoiceRow(
        row_id=row_id,
        source_file="sample.xlsx",
        sheet_name="B2B",
        excel_row_number=row_id + 1,
        raw_snapshot=[],
        supplier_name="ABC TRADERS",
        gstin="33ABCDE1234F1Z5",
        invoice_no=f"INV-{row_id}",
        invoice_date=date(2026, 1, row_id),
        taxable_value=Decimal("1000.00"),
        cgst=Decimal("90.00"),
        sgst=Decimal("90.00"),
        invoice_value=Decimal("1180.00"),
        expected_invoice_value=Decimal("1180.00") - Decimal(diff),
        difference_amount=Decimal(diff),
        mismatch_reason=reason,
        audit_status=status,
        audit_severity=severity,
        review_required=review,
        include_in_totals=include,
    )


def _result() -> AuditResult:
    rows = [
        _row(1, include=True, review=False, status="VALID", reason="BALANCED_OR_ROUNDING"),
        _row(2, include=False, review=True, status="REVIEW_REQUIRED", reason="UNEXPLAINED_GST_MISMATCH", severity="HIGH", diff="770.00"),
        _row(3, include=False, review=True, status="REVIEW_REQUIRED", reason="POSSIBLE_FREIGHT_OR_DISCOUNT", severity="LOW", diff="10.00"),
        _row(4, include=False, review=False, status="SKIPPED_TOTAL_OR_NON_INVOICE_ROW", reason="NO_AMOUNT_DETECTED"),
    ]
    summary = AuditSummary(
        files_processed=1,
        sheets_processed=1,
        raw_rows_read=4,
        classified_rows=4,
        official_invoice_rows=3,
        final_approved_rows=1,
        review_required_rows=2,
        skipped_rows=1,
        approved_invoice_value=Decimal("1180.00"),
        review_invoice_value=Decimal("2360.00"),
        row_coverage_status="MATCHED",
        amount_reconciliation_status="MATCHED",
        final_status="BALANCED_BUT_REVIEW_REQUIRED",
    )
    return AuditResult(rows=rows, summary=summary, source_totals={}, month_totals={}, supplier_totals={})


def test_main_window_initializes_audit_column_visibility_before_refresh(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    assert hasattr(window, "audit_extra_columns_visible")
    assert window.audit_extra_columns_visible is False
    window.result = _result()
    window.refresh_all_views()
    window._apply_audit_column_visibility()


def test_issue_counts_are_consistent_for_critical_advisory_trace(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.result = _result()
    counts = window._issue_counts_from_rows()
    assert counts["critical"] == 1
    assert counts["advisory"] == 1
    assert counts["trace"] == 1
    assert counts["review_total"] == 2
    assert counts["approved"] == 1
    assert counts["approved"] + counts["review_total"] + counts["trace"] == counts["total"]


def test_apply_audit_filter_updates_combo_when_called_from_queue_card(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.result = _result()
    window.apply_audit_filter("Trace / Excluded")
    assert window.audit_filter_combo.currentText() == "Trace / Excluded"
    assert len(window.current_rows) == 1
