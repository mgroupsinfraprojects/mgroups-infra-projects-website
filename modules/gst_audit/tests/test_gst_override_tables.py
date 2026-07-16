from __future__ import annotations

from decimal import Decimal

from app.core.gst_compliance import detect_itc_flag, detect_rcm_flag
from app.core.gst_override_tables import lookup_itc_override, lookup_rcm_override, normalize_hsn_sac
from app.core.models import InvoiceRow


def make_row(**kwargs):
    data = dict(
        row_id=1,
        source_file="sample.xlsx",
        sheet_name="Sheet1",
        excel_row_number=2,
        raw_snapshot=[],
        supplier_name="ABC Traders",
        gstin="33ABCDE1234F1Z5",
        recipient_gstin="33AAAAA0000A1Z5",
        invoice_no="INV-001",
        taxable_value=Decimal("1000"),
        cgst=Decimal("90"),
        sgst=Decimal("90"),
        invoice_value=Decimal("1180"),
        include_in_totals=True,
    )
    data.update(kwargs)
    return InvoiceRow(**data)


def test_normalize_hsn_sac_extracts_digit_code():
    assert normalize_hsn_sac("HSN 996511 - GTA") == "996511"
    assert normalize_hsn_sac("no code") == ""


def test_itc_override_flags_blocked_hsn_prefix():
    override = lookup_itc_override("8703")
    assert override.decision == "BLOCKED"
    flag, note = detect_itc_flag(make_row(hsn_sac="8703"))
    assert flag == "BLOCKED_ITC_REVIEW"
    assert "HSN/SAC prefix" in note


def test_rcm_override_flags_rcm_hsn_prefix():
    override = lookup_rcm_override("996511")
    assert override.decision == "RCM"
    flag, note = detect_rcm_flag(make_row(hsn_sac="996511"))
    assert flag == "POSSIBLE_RCM"
    assert "HSN/SAC prefix" in note
