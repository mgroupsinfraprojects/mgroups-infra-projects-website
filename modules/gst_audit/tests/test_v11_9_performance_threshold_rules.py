from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.core.models import InvoiceRow
from app.core.review_policy import is_mandatory_review, is_meaningful_duplicate_row
from app.core.review_thresholds import save_review_thresholds


def _row(**kwargs) -> InvoiceRow:
    data = dict(
        row_id=1,
        source_file="MAY 25.xlsx",
        sheet_name="B2B",
        excel_row_number=10,
        raw_snapshot=["supplier", "gstin", "invoice"],
        supplier_name="Ambika Global",
        gstin="33BMAPR9726H1ZU",
        invoice_no="AGT/25-26/1642",
        invoice_date=date(2025, 5, 17),
        taxable_value=Decimal("25000.00"),
        igst=Decimal("0.00"),
        cgst=Decimal("2500.00"),
        sgst=Decimal("2500.00"),
        invoice_value=Decimal("30245.00"),
        expected_invoice_value=Decimal("29944.92"),
        difference_amount=Decimal("300.08"),
        difference_percent=Decimal("1.00"),
        mismatch_reason="ROUNDING_IN_MULTIPLE_COMPONENTS",
        audit_status="REVIEW_REQUIRED",
        audit_severity="MEDIUM",
        review_required=True,
        include_in_totals=False,
        duplicate_key="33BMAPR9726H1ZU|AGT/25-26/1642|2025-05-17",
    )
    data.update(kwargs)
    return InvoiceRow(**data)


def test_low_rounding_difference_with_duplicate_key_is_not_mandatory(monkeypatch, tmp_path):
    monkeypatch.setenv("GST_AUDIT_REVIEW_RULES", str(tmp_path / "thresholds.json"))
    save_review_thresholds({
        "critical_amount": 10000,
        "advisory_amount": 2500,
        "ignore_amount": 5000,
        "gst_critical_amount": 2500,
        "duplicate_min_amount": 10000,
        "critical_percent": 10,
        "high_value_supplier": 100000,
    })
    row = _row()
    assert is_meaningful_duplicate_row(row) is False
    assert is_mandatory_review(row) is False


def test_explicit_large_duplicate_stays_mandatory(monkeypatch, tmp_path):
    monkeypatch.setenv("GST_AUDIT_REVIEW_RULES", str(tmp_path / "thresholds.json"))
    save_review_thresholds({"duplicate_min_amount": 10000, "critical_amount": 10000, "advisory_amount": 2500, "ignore_amount": 500})
    row = _row(
        audit_status="DUPLICATE_EXCLUDED",
        audit_notes="Duplicate of row id 10. Excluded from totals.",
        mismatch_reason="UNEXPLAINED_GST_MISMATCH",
        difference_amount=Decimal("12500.00"),
        invoice_value=Decimal("50000.00"),
        expected_invoice_value=Decimal("37500.00"),
        audit_severity="HIGH",
    )
    assert is_meaningful_duplicate_row(row) is True
    assert is_mandatory_review(row) is True
