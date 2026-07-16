from decimal import Decimal
from pathlib import Path

from openpyxl import Workbook

from app.core.audit_engine import InvoiceAuditEngine, is_gst_invoice_detail_sheet
from app.core.config import AuditConfig
from app.core.header_detector import detect_header_map_with_metadata
import pandas as pd


def test_two_row_b2b_cdnr_header_maps_note_fields():
    frame = pd.DataFrame([
        ["Goods and Services Tax - GSTR-2B", "", "", "", "", "", ""],
        ["Debit/Credit notes (Original)", "", "", "", "", "", ""],
        ["GSTIN of supplier", "Trade/Legal name", "Credit note/Debit note details", "", "", "", ""],
        ["", "", "Note number", "Note type", "Note date", "Note Value (₹)", "Taxable Value (₹)"],
    ])
    detected = detect_header_map_with_metadata(frame, max_scan_rows=10, min_score=2)
    assert detected.field_map["gstin"] == 0
    assert detected.field_map["supplier_name"] == 1
    assert detected.field_map["invoice_no"] == 2
    assert detected.field_map["invoice_date"] == 4
    assert detected.field_map["invoice_value"] == 5
    assert detected.field_map["taxable_value"] == 6


def test_b2b_cdnr_note_value_is_counted_as_invoice_value(tmp_path: Path):
    path = tmp_path / "cdnr.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.title = "B2B-CDNR"
    ws.append(["Goods and Services Tax  - GSTR-2B"])
    ws.append([])
    ws.append(["Debit/Credit notes (Original)"])
    ws.append([
        "GSTIN of supplier", "Trade/Legal name", "Credit note/Debit note details", "", "", "", "",
        "Place of supply", "Supply Attract Reverse Charge", "Taxable Value (₹)", "Tax Amount", "", "", "",
        "GSTR-1/IFF/GSTR-5 Period", "GSTR-1/IFF/GSTR-5 Filing Date", "ITC Availability", "Reason", "Applicable % of Tax Rate", "Source", "IRN", "IRN Date",
    ])
    ws.append([
        "", "", "Note number", "Note type", "Note Supply type", "Note date", "Note Value (₹)",
        "", "", "", "Integrated Tax(₹)", "Central Tax(₹)", "State/UT Tax(₹)", "Cess(₹)", "", "", "", "", "", "", "", "",
    ])
    ws.append([
        "33AAHCS8802L1Z3", "SUSEE ENGINEERING AND AUTOMOBILES PRIVATE LIMITED", "CN/24-25/66", "Credit Note", "Regular", "23/04/2025", "40000",
        "Tamil Nadu", "No", "30534.35", "0", "4274.81", "4274.81", "916.03", "Apr'25", "10/05/2025", "Yes", "", "100%", "", "", "",
    ])
    wb.save(path)

    result = InvoiceAuditEngine(AuditConfig()).process_files([path])
    note_rows = [row for row in result.rows if row.invoice_no == "CN/24-25/66"]
    assert len(note_rows) == 1
    row = note_rows[0]
    assert row.invoice_value == Decimal("40000.00")
    assert row.taxable_value == Decimal("30534.35")
    assert row.cgst == Decimal("4274.81")
    assert row.sgst == Decimal("4274.81")
    assert row.cess == Decimal("916.03")
    assert result.summary.raw_detected_invoice_value == Decimal("40000.00")
    assert result.summary.official_invoice_rows == 1


def test_official_invoice_sheet_classifier_excludes_summary_tabs():
    assert is_gst_invoice_detail_sheet("B2B")
    assert is_gst_invoice_detail_sheet("B2B-CDNR")
    assert is_gst_invoice_detail_sheet("IMPGSEZ")
    assert not is_gst_invoice_detail_sheet("Read me")
    assert not is_gst_invoice_detail_sheet("ITC Available")
    assert not is_gst_invoice_detail_sheet("All other ITC")
