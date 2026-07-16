from __future__ import annotations

from decimal import Decimal

from app.core.models import InvoiceRow
from app.core.review_policy import (
    has_gst_or_amount_exception,
    has_required_amount_problem,
    has_required_identity_problem,
    is_advisory_exception,
    is_empty_or_noise_row,
    is_mandatory_review,
    is_trace_only,
)


def row(**kwargs) -> InvoiceRow:
    base = dict(row_id=1, source_file="sample.xlsx", sheet_name="Sheet1", excel_row_number=2, raw_snapshot=[])
    base.update(kwargs)
    return InvoiceRow(**base)


def test_review_policy_ignores_small_rounding_as_mandatory_review():
    r = row(
        supplier_name="ABC",
        gstin="33ABCDE1234F1Z5",
        invoice_no="INV1",
        review_required=True,
        mismatch_reason="MINOR_ROUNDING_OR_DECIMAL_ISSUE",
        difference_amount=Decimal("0.40"),
    )
    assert not is_mandatory_review(r)
    assert not has_gst_or_amount_exception(r)


def test_review_policy_sends_identity_problem_to_mandatory_review():
    r = row(
        supplier_name="",
        gstin="",
        invoice_no="INV1",
        review_required=True,
        audit_notes="GSTIN NOT DETECTED; SUPPLIER NAME MISSING",
    )
    assert has_required_identity_problem(r)
    assert is_mandatory_review(r)


def test_review_policy_sends_large_gst_mismatch_to_mandatory_review():
    r = row(
        supplier_name="ABC",
        gstin="33ABCDE1234F1Z5",
        invoice_no="INV1",
        review_required=True,
        audit_severity="HIGH",
        mismatch_reason="UNEXPLAINED_GST_MISMATCH",
        difference_amount=Decimal("3000.00"),
    )
    assert has_required_amount_problem(r)
    assert has_gst_or_amount_exception(r)
    assert is_mandatory_review(r)


def test_review_policy_keeps_skipped_empty_rows_trace_only():
    r = row(
        review_required=True,
        audit_status="SKIPPED_EMPTY_ROW",
        mismatch_reason="NO_AMOUNT_DETECTED",
        include_in_totals=False,
    )
    assert is_empty_or_noise_row(r)
    assert is_trace_only(r)
    assert not is_mandatory_review(r)


def test_review_policy_keeps_low_risk_exception_advisory():
    r = row(
        supplier_name="ABC",
        gstin="33ABCDE1234F1Z5",
        invoice_no="INV1",
        review_required=True,
        audit_severity="LOW",
        mismatch_reason="POSSIBLE_FREIGHT_OR_DISCOUNT",
        difference_amount=Decimal("25.00"),
    )
    assert is_advisory_exception(r)
    assert has_gst_or_amount_exception(r)
    assert not is_mandatory_review(r)
