from __future__ import annotations

from decimal import Decimal

from app.core.gst_compliance import (
    check_place_of_supply,
    compliance_dataframe,
    detect_credit_debit_note,
    detect_irn_flag,
    detect_itc_flag,
    detect_rcm_flag,
)
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
        igst=Decimal("0"),
        cgst=Decimal("90"),
        sgst=Decimal("90"),
        cess=Decimal("0"),
        invoice_value=Decimal("1180"),
        include_in_totals=True,
    )
    data.update(kwargs)
    return InvoiceRow(**data)


def test_itc_flag_detects_blocked_credit_keyword():
    row = make_row(raw_snapshot=["Motor vehicle insurance premium"])
    flag, note = detect_itc_flag(row)
    assert flag == "BLOCKED_ITC_REVIEW"
    assert "blocked-credit" in note


def test_rcm_flag_detects_reverse_charge_keyword():
    row = make_row(audit_notes="Goods Transport Agency RCM")
    flag, note = detect_rcm_flag(row)
    assert flag == "POSSIBLE_RCM"
    assert "reverse-charge" in note


def test_place_of_supply_flags_same_state_igst_only():
    row = make_row(igst=Decimal("180"), cgst=Decimal("0"), sgst=Decimal("0"))
    flag, note = check_place_of_supply(row)
    assert flag == "POSSIBLE_TAX_TYPE_ERROR"
    assert "Same-state" in note


def test_credit_note_detection_from_negative_value():
    row = make_row(invoice_value=Decimal("-1180"))
    assert detect_credit_debit_note(row) == "CREDIT_NOTE"


def test_irn_detection_uses_64_hex_chars():
    row = make_row(raw_snapshot=["IRN", "a" * 64])
    flag, _note = detect_irn_flag(row)
    assert flag == "IRN_PRESENT_FORMAT_OK"


def test_compliance_dataframe_has_client_review_columns():
    df = compliance_dataframe([make_row(), make_row(row_id=2, invoice_no="CN-22", invoice_value=Decimal("-10"))])
    assert list(df.columns) == [
        "row_id",
        "supplier_name",
        "gstin",
        "invoice_no",
        "itc_flag",
        "rcm_flag",
        "place_of_supply_flag",
        "note_type",
        "irn_flag",
        "notes",
    ]
    assert len(df) == 2
