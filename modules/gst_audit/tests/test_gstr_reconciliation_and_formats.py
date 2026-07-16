from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd

from app.core.audit_engine import InvoiceAuditEngine
from app.core.exporter import export_verified_excel
from app.core.gstin import calculate_gstin_checksum
from app.core.gstr_reconciliation import normalize_invoice_no, reconcile_gstr_2a_2b
from app.core.models import InvoiceRow


def valid_gstin(prefix: str = "33ABCDE1234F1Z") -> str:
    return prefix + calculate_gstin_checksum(prefix)


def make_row(row_id: int, gstin: str, invoice_no: str, amount: str, *, source: str = "book.xlsx") -> InvoiceRow:
    row = InvoiceRow(
        row_id=row_id,
        source_file=source,
        sheet_name="Sheet1",
        excel_row_number=row_id,
        raw_snapshot=[gstin, invoice_no, amount],
        supplier_name="ABC Traders",
        gstin=gstin,
        invoice_no=invoice_no,
        invoice_date=date(2026, 1, 1),
        taxable_value=Decimal(amount) - Decimal("18.00"),
        cgst=Decimal("9.00"),
        sgst=Decimal("9.00"),
        invoice_value=Decimal(amount),
        expected_invoice_value=Decimal(amount),
        audit_status="VALID",
        include_in_totals=True,
        review_required=False,
        review_decision="ACCEPTED_AUTO",
    )
    row.detected_snapshot = {"gstin": gstin, "invoice_no": invoice_no}
    row.final_snapshot = dict(row.detected_snapshot)
    return row


def test_normalize_invoice_no_strips_separators_and_zeroes():
    assert normalize_invoice_no(" inv-00042 / 26 ") == "INV0004226"
    assert normalize_invoice_no("00042") == "42"


def test_gstr_2b_reconciliation_detects_match_mismatch_and_missing():
    engine = InvoiceAuditEngine()
    gstin = valid_gstin()
    book = engine.build_result_from_rows([
        make_row(1, gstin, "INV-001", "118.00"),
        make_row(2, gstin, "INV-002", "200.00"),
        make_row(3, gstin, "INV-003", "300.00"),
    ], 1, 1)
    gstr = engine.build_result_from_rows([
        make_row(11, gstin, "INV-001", "118.00", source="gstr2b.xlsx"),
        make_row(12, gstin, "INV-002", "250.00", source="gstr2b.xlsx"),
        make_row(13, gstin, "INV-004", "400.00", source="gstr2b.xlsx"),
    ], 1, 1)
    reco = reconcile_gstr_2a_2b(book, gstr)
    statuses = {record.status for record in reco.records}
    assert "MATCHED" in statuses
    assert "AMOUNT_MISMATCH" in statuses
    assert "MISSING_IN_GSTR" in statuses
    assert "MISSING_IN_BOOKS" in statuses
    assert reco.summary.final_status == "GSTR_REVIEW_REQUIRED"


def test_export_includes_polished_and_gstr_sheets(tmp_path: Path):
    engine = InvoiceAuditEngine()
    gstin = valid_gstin()
    book = engine.build_result_from_rows([make_row(1, gstin, "INV-001", "118.00")], 1, 1)
    gstr = engine.build_result_from_rows([make_row(11, gstin, "INV-001", "118.00", source="gstr2b.xlsx")], 1, 1)
    reco = reconcile_gstr_2a_2b(book, gstr)
    output = export_verified_excel(book, tmp_path / "verified.xlsx", gstr_reconciliation=reco)
    sheets = pd.ExcelFile(output).sheet_names
    assert "Executive Summary" in sheets
    assert "Review Checklist" in sheets
    assert "Mismatch Reasons" in sheets
    assert "GSTR Reco Summary" in sheets
    assert "GSTR Reco Details" in sheets


def _write_invoice_frame(path: Path, sep: str = ",", encoding: str = "utf-8-sig", invoice_no: str = "INV-1") -> None:
    gstin = valid_gstin()
    rows = [
        ["GSTIN of supplier", "Trade/Legal name", "Invoice number", "Invoice date", "Taxable Value", "CGST", "SGST", "IGST", "Invoice Value"],
        [gstin, "ABC Traders", invoice_no, "01-01-2026", "100", "9", "9", "0", "118"],
    ]
    with path.open("w", encoding=encoding, newline="") as fh:
        for row in rows:
            fh.write(sep.join(row) + "\n")


def test_csv_utf16_and_tsv_are_processed(tmp_path: Path):
    csv_path = tmp_path / "gst_utf16.csv"
    tsv_path = tmp_path / "gst.tsv"
    _write_invoice_frame(csv_path, sep=",", encoding="utf-16")
    _write_invoice_frame(tsv_path, sep="\t", encoding="utf-8-sig", invoice_no="INV-2")
    result = InvoiceAuditEngine().process_files([str(csv_path), str(tsv_path)])
    assert result.summary.files_processed == 2
    assert result.summary.final_approved_rows == 2
    assert result.summary.row_coverage_status == "MATCHED"


def test_corrupted_file_is_isolated_and_valid_file_still_processed(tmp_path: Path):
    good = tmp_path / "good.csv"
    bad = tmp_path / "bad.xlsx"
    _write_invoice_frame(good)
    bad.write_text("not a real excel file", encoding="utf-8")
    result = InvoiceAuditEngine().process_files([str(good), str(bad)])
    statuses = [row.audit_status for row in result.rows]
    assert "ERROR_FILE_UNREADABLE" in statuses
    assert result.summary.final_approved_rows == 1
    assert result.summary.critical_rows >= 1


def test_advanced_gstr_reconciliation_flags_date_period_tax_and_itc():
    engine = InvoiceAuditEngine()
    gstin = valid_gstin()
    book_row = make_row(1, gstin, "INV-900", "118.00")
    gstr_row = make_row(11, gstin, "INV-900", "120.00", source="gstr2b.xlsx")
    gstr_row.taxable_value = Decimal("104.00")
    gstr_row.cgst = Decimal("9.50")
    gstr_row.sgst = Decimal("9.50")
    gstr_row.invoice_date = date(2026, 2, 1)
    gstr_row.period = "2026-02"
    gstr_row.detected_snapshot["itc_eligibility"] = "No"
    gstr_row.final_snapshot = dict(gstr_row.detected_snapshot)
    book = engine.build_result_from_rows([book_row], 1, 1)
    gstr = engine.build_result_from_rows([gstr_row], 1, 1)

    reco = reconcile_gstr_2a_2b(book, gstr)
    record = reco.records[0]

    assert record.status == "AMOUNT_MISMATCH"
    assert record.date_status == "DATE_MISMATCH"
    assert record.period_status == "PERIOD_MISMATCH"
    assert record.itc_status == "NO"
    assert reco.summary.date_mismatch_rows == 1
    assert reco.summary.period_mismatch_rows == 1
    assert reco.summary.taxable_mismatch_rows == 1
    assert "ITC" in record.action_required


def test_import_profiles_map_common_gst_portal_headers():
    from app.core.import_profiles import GST_PORTAL_PROFILE, apply_mapping, map_columns, validate_required_mapping

    df = pd.DataFrame({
        "GSTIN of supplier": [valid_gstin()],
        "Trade/Legal name": ["ABC Traders"],
        "Invoice number": ["INV-1"],
        "Invoice date": ["01-01-2026"],
        "Invoice Value": [118],
        "Taxable Value": [100],
    })
    mapping = map_columns(df.columns, GST_PORTAL_PROFILE)
    assert validate_required_mapping(mapping) == []
    canonical = apply_mapping(df, mapping)
    assert canonical.loc[0, "supplier_name"] == "ABC Traders"
    assert canonical.loc[0, "invoice_no"] == "INV-1"


def test_exception_workflow_and_export_top_one_percent_sheets(tmp_path: Path):
    from app.core.exception_workflow import exception_summary_dataframe, final_lock_checklist

    engine = InvoiceAuditEngine()
    gstin = valid_gstin()
    row = make_row(1, gstin, "INV-777", "118.00")
    row.review_required = True
    row.include_in_totals = False
    row.audit_status = "GST_MISMATCH_REVIEW"
    row.audit_severity = "HIGH"
    row.mismatch_reason = "AMOUNT_MISMATCH"
    row.difference_amount = Decimal("10.00")
    result = engine.build_result_from_rows([row], 1, 1)

    exception_df = exception_summary_dataframe(result)
    assert not exception_df.empty
    lock_df = final_lock_checklist(result)
    assert "Review rows" in lock_df["control"].tolist()

    output = export_verified_excel(result, tmp_path / "top1.xlsx")
    sheets = pd.ExcelFile(output).sheet_names
    for expected in ["Cover Sheet", "Exception Summary", "Review Queue", "Final Lock Checklist", "Import Profile Guide", "Sign Off", "Source File List"]:
        assert expected in sheets
