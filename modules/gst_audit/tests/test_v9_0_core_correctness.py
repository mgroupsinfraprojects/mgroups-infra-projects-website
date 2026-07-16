from __future__ import annotations

from datetime import date
from decimal import Decimal

import pandas as pd

from app.core.audit_engine import InvoiceAuditEngine, classify_gst_mismatch_details
from app.core.gstin import calculate_gstin_checksum
from app.core.models import InvoiceRow


def valid_gstin(prefix: str = "33ABCDE1234F1Z") -> str:
    return prefix + calculate_gstin_checksum(prefix)


def row(row_id: int, *, invoice_no: str = "INV-1", invoice_value: str = "118.00") -> InvoiceRow:
    r = InvoiceRow(
        row_id=row_id,
        source_file="sample.xlsx",
        sheet_name="Sheet1",
        excel_row_number=row_id,
        raw_snapshot=["raw"],
        supplier_name="ABC Traders",
        gstin=valid_gstin(),
        invoice_no=invoice_no,
        invoice_date=date(2026, 1, 1),
        taxable_value=Decimal("100.00"),
        cgst=Decimal("9.00"),
        sgst=Decimal("9.00"),
        invoice_value=Decimal(invoice_value),
        expected_invoice_value=Decimal("118.00"),
        difference_amount=Decimal(invoice_value) - Decimal("118.00"),
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


def test_recalculate_result_reruns_duplicate_detection_after_manual_accept():
    engine = InvoiceAuditEngine()
    first = row(1)
    duplicate = row(2)
    result = engine.build_result_from_rows([first, duplicate], 1, 1)
    engine._mark_duplicates(result.rows)
    assert duplicate.audit_status == "DUPLICATE_EXCLUDED"

    duplicate.apply_review_decision(True, "ACCEPTED_MANUAL", "ACCEPTED_WARNING_MANUAL", "📌", "operator accepted")
    assert duplicate.include_in_totals is True

    engine.recalculate_result(result)
    assert duplicate.audit_status == "DUPLICATE_EXCLUDED"
    assert duplicate.include_in_totals is False
    assert result.summary.duplicate_rows == 1
    assert result.summary.final_approved_rows == 1


def test_duplicate_key_ignores_invoice_value_during_processing(tmp_path):
    gstin = valid_gstin()
    df = pd.DataFrame([
        ["GSTIN of supplier", "Trade/Legal name", "Invoice number", "Invoice date", "Taxable Value", "CGST", "SGST", "IGST", "Invoice Value"],
        [gstin, "ABC Traders", "INV-77", "01-01-2026", 100, 9, 9, 0, 118],
        [gstin, "ABC Traders", "INV-77", "01-01-2026", 100, 9, 9, 0, 119],
    ])
    path = tmp_path / "dupes.xlsx"
    df.to_excel(path, index=False, header=False)

    result = InvoiceAuditEngine().process_files([str(path)])
    duplicate_rows = [r for r in result.rows if r.audit_status == "DUPLICATE_EXCLUDED"]
    assert len(duplicate_rows) == 1
    assert result.summary.final_approved_rows == 1


def test_credit_note_balanced_negative_components_are_not_high_severity_mismatch():
    details = classify_gst_mismatch_details(
        Decimal("-118.00"),
        Decimal("-118.00"),
        Decimal("-100.00"),
        Decimal("-18.00"),
    )
    assert details["reason"] == "CREDIT_NOTE_BALANCED"
    assert details["review"] is False
    assert details["include"] is True


def test_apply_review_decision_is_atomic_and_deduplicates_notes():
    r = row(1)
    r.review_required = True
    r.include_in_totals = False
    r.apply_review_decision(True, "ACCEPTED_MANUAL", "ACCEPTED_WARNING_MANUAL", "📌", "checked")
    r.apply_review_decision(True, "ACCEPTED_MANUAL", "ACCEPTED_WARNING_MANUAL", "📌", "checked")
    assert r.include_in_totals is True
    assert r.review_required is False
    assert r.audit_notes.count("Bulk manual review decision saved. checked") == 1
