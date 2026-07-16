from __future__ import annotations

from datetime import date
from decimal import Decimal

import pandas as pd

from app.core.audit_engine import InvoiceAuditEngine, classify_gst_mismatch_details
from app.core.config import AuditConfig
from app.core.gstin import calculate_gstin_checksum
from app.core.header_detector import detect_header_map_with_metadata
from app.core.models import InvoiceRow


def valid_gstin(prefix: str = "33ABCDE1234F1Z") -> str:
    return prefix + calculate_gstin_checksum(prefix)


def make_row(row_id: int, *, invoice_no: str = "INV-1", value: str = "118.00") -> InvoiceRow:
    r = InvoiceRow(
        row_id=row_id,
        source_file="sample.xlsx",
        sheet_name="B2B",
        excel_row_number=row_id,
        raw_snapshot=["raw"],
        supplier_name="ABC Traders",
        gstin=valid_gstin(),
        invoice_no=invoice_no,
        invoice_date=date(2026, 1, 1),
        invoice_series="INV",
        invoice_sequence_no=row_id,
        taxable_value=Decimal("100.00"),
        cgst=Decimal("9.00"),
        sgst=Decimal("9.00"),
        invoice_value=Decimal(value),
        expected_invoice_value=Decimal("118.00"),
        difference_amount=Decimal(value) - Decimal("118.00"),
        mismatch_reason="BALANCED_OR_ROUNDING",
        audit_status="VALID",
        include_in_totals=True,
        review_required=False,
        review_decision="ACCEPTED_AUTO",
        duplicate_key=f"{valid_gstin()}|{invoice_no}|2026-01-01",
    )
    r.detected_snapshot = {"gstin": r.gstin}
    r.final_snapshot = dict(r.detected_snapshot)
    return r


def test_recalculate_result_rebuilds_totals_and_keeps_duplicates_excluded():
    engine = InvoiceAuditEngine(AuditConfig())
    first = make_row(1, value="118.00")
    duplicate = make_row(2, value="118.00")
    result = engine.build_result_from_rows([first, duplicate], 1, 1)
    engine._mark_duplicates(result.rows)
    assert result.rows[1].audit_status == "DUPLICATE_EXCLUDED"

    duplicate.apply_review_decision(True, "ACCEPTED_MANUAL", "ACCEPTED_WARNING_MANUAL", "📌", "operator override")
    result = engine.recalculate_result(result)

    assert duplicate.audit_status == "DUPLICATE_EXCLUDED"
    assert duplicate.include_in_totals is False
    assert result.summary.duplicate_rows == 1
    assert result.summary.final_approved_rows == 1
    assert result.summary.approved_invoice_value == Decimal("118.00")
    assert list(result.supplier_totals.values()) == [Decimal("118.00")]


def test_recalculate_result_reapplies_gap_skip_and_supplier_anomaly_notes():
    engine = InvoiceAuditEngine(AuditConfig(supplier_anomaly_multiplier=Decimal("2.0")))
    rows = [make_row(1, invoice_no="INV-2026010001", value="100.00"), make_row(2, invoice_no="INV-2026999999", value="100.00"), make_row(3, invoice_no="INV-2026999998", value="10000.00")]
    for idx, r in enumerate(rows, start=1):
        r.invoice_sequence_no = 2026000000 + idx * 9999
        r.duplicate_key = f"{r.gstin}|{r.invoice_no}|2026-01-01"
    result = engine.build_result_from_rows(rows, 1, 1)
    result = engine.recalculate_result(result)

    assert any("GAP_DETECTION_SKIPPED" in r.audit_notes for r in rows)
    assert any("Invoice value is more than" in r.audit_notes for r in rows)


def test_positive_invoice_with_negative_taxable_is_component_sign_mismatch_not_credit_note():
    # A record with invoice_value > 0 but taxable < 0 is a data quality issue,
    # NOT a credit note. v9.3 incorrectly classified it as CREDIT_NOTE_BALANCED
    # because the guard used OR instead of only checking invoice_value < 0.
    details = classify_gst_mismatch_details(
        invoice_value=Decimal("118.00"),
        expected_value=Decimal("118.00"),
        taxable=Decimal("-100.00"),
        gst_total=Decimal("218.00"),
    )
    assert details["reason"] == "COMPONENT_SIGN_MISMATCH"
    assert details["review"] is True
    assert details["include"] is False


def test_header_detector_accepts_gstr2b_aliases():
    frame = pd.DataFrame([
        ["GSTIN/UIN of Supplier", "Trade/Legal name of Supplier", "Invoice/Document Number", "Invoice/Document Date", "Total Invoice Value", "Taxable Value (₹)", "Integrated Tax(₹)", "Central Tax(₹)", "State/UT Tax(₹)", "Return Period"],
        [valid_gstin(), "ABC Traders", "INV-1", "01/01/2026", "118", "100", "0", "9", "9", "Jan 2026"],
    ])
    detection = detect_header_map_with_metadata(frame, max_scan_rows=5, min_score=2)
    assert not detection.uncertain
    assert detection.field_map["gstin"] == 0
    assert detection.field_map["supplier_name"] == 1
    assert detection.field_map["invoice_no"] == 2
    assert detection.field_map["invoice_date"] == 3
    assert detection.field_map["invoice_value"] == 4
