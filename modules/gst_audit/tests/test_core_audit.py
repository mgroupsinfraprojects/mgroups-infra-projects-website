from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd

from app.core.audit_engine import InvoiceAuditEngine, classify_gst_mismatch
from app.core.database import AuditDatabase
from app.core.exporter import export_verified_excel
from app.core.gstin import calculate_gstin_checksum, has_valid_gstin_checksum, is_valid_gstin
from app.core.models import InvoiceRow
from app.core.money import format_inr, to_decimal


def valid_gstin(prefix: str = "33ABCDE1234F1Z") -> str:
    return prefix + calculate_gstin_checksum(prefix)


def make_row(row_id: int = 1, *, include=True, review=False, status="VALID", invoice="118.00") -> InvoiceRow:
    row = InvoiceRow(
        row_id=row_id,
        source_file="sample.xlsx",
        sheet_name="Sheet1",
        excel_row_number=row_id,
        raw_snapshot=["raw"],
        supplier_name="ABC Traders",
        gstin=valid_gstin(),
        invoice_no=f"INV-{row_id}",
        invoice_date=date(2026, 1, 1),
        taxable_value=Decimal("100.00"),
        cgst=Decimal("9.00"),
        sgst=Decimal("9.00"),
        invoice_value=Decimal(invoice),
        expected_invoice_value=Decimal("118.00"),
        difference_amount=Decimal(invoice) - Decimal("118.00"),
        mismatch_reason="BALANCED_OR_ROUNDING",
        audit_status=status,
        include_in_totals=include,
        review_required=review,
        review_decision="ACCEPTED_AUTO" if include else "PENDING_REVIEW",
    )
    row.detected_snapshot = {"gstin": row.gstin}
    row.final_snapshot = dict(row.detected_snapshot)
    return row


def test_decimal_parsing_removes_indian_separators():
    assert to_decimal("₹1,23,456.789") == Decimal("123456.79")


def test_inr_format_uses_full_indian_amount():
    assert format_inr(Decimal("193800000")) == "₹19,38,00,000.00"
    assert format_inr(Decimal("290000")) == "₹2,90,000.00"
    assert format_inr(Decimal("9800")) == "₹9,800.00"


def test_gstin_checksum_generation_and_validation():
    gstin = valid_gstin()
    assert len(gstin) == 15
    assert has_valid_gstin_checksum(gstin)
    assert is_valid_gstin(gstin)


def test_gstin_rejects_bad_checksum():
    gstin = valid_gstin()
    bad_last = "0" if gstin[-1] != "0" else "1"
    assert not is_valid_gstin(gstin[:-1] + bad_last)


def test_balanced_gst_mismatch_classification():
    reason, severity, review, include = classify_gst_mismatch(
        Decimal("118.00"), Decimal("118.00"), Decimal("100.00"), Decimal("18.00")
    )
    assert reason == "BALANCED_OR_ROUNDING"
    assert severity == "LOW"
    assert review is False
    assert include is True


def test_unexplained_mismatch_requires_review():
    reason, severity, review, include = classify_gst_mismatch(
        Decimal("200.00"), Decimal("118.00"), Decimal("100.00"), Decimal("18.00")
    )
    assert reason == "UNEXPLAINED_GST_MISMATCH"
    assert severity == "HIGH"
    assert review is True
    assert include is False


def test_summary_reconciles_approved_review_excluded():
    engine = InvoiceAuditEngine()
    approved = make_row(1, include=True, review=False, invoice="118.00")
    review = make_row(2, include=False, review=True, status="REVIEW_REQUIRED", invoice="120.00")
    excluded = make_row(3, include=False, review=False, status="SKIPPED_TOTAL_OR_NON_INVOICE_ROW", invoice="0.00")
    result = engine.build_result_from_rows([approved, review, excluded], 1, 1)
    assert result.summary.raw_rows_read == 3
    assert result.summary.final_approved_rows == 1
    assert result.summary.review_required_rows == 1
    assert result.summary.amount_reconciliation_status == "MATCHED"
    assert result.summary.final_status == "BALANCED_BUT_REVIEW_REQUIRED"


def test_duplicate_detection_excludes_second_copy():
    engine = InvoiceAuditEngine()
    row1 = make_row(1)
    row2 = make_row(2)
    row2.invoice_no = row1.invoice_no
    row2.duplicate_key = row1.duplicate_key
    engine._mark_duplicates([row1, row2])
    assert row2.audit_status == "DUPLICATE_EXCLUDED"
    assert row2.include_in_totals is False


def test_database_save_load_and_review_decision(tmp_path: Path):
    db = AuditDatabase(tmp_path / "audit.sqlite3")
    try:
        engine = InvoiceAuditEngine()
        row = make_row(1, include=False, review=True, status="REVIEW_REQUIRED")
        result = engine.build_result_from_rows([row], 1, 1)
        dataset_id = db.save_result("test", result.summary.to_dict(), result.rows)
        db.update_review_decision(dataset_id, 1, "ACCEPTED_MANUAL", True, "ACCEPTED_WARNING_MANUAL", "📌", False, "verified")
        loaded = db.load_rows(dataset_id)
        assert loaded[0].review_decision == "ACCEPTED_MANUAL"
        assert loaded[0].include_in_totals is True
    finally:
        db.close()


def test_export_verified_excel_creates_expected_sheets(tmp_path: Path):
    engine = InvoiceAuditEngine()
    result = engine.build_result_from_rows([make_row(1)], 1, 1)
    output = export_verified_excel(result, tmp_path / "verified.xlsx")
    assert output.exists()
    sheets = pd.ExcelFile(output).sheet_names
    assert "Audit Summary" in sheets
    assert "Approved Rows" in sheets
    assert "All Classified Rows" in sheets


def test_process_synthetic_excel_reads_header_and_data(tmp_path: Path):
    gstin = valid_gstin()
    df = pd.DataFrame([
        ["GSTIN of supplier", "Trade/Legal name", "Invoice number", "Invoice date", "Taxable Value", "CGST", "SGST", "IGST", "Invoice Value"],
        [gstin, "ABC Traders", "INV-1", "01-01-2026", 100, 9, 9, 0, 118],
    ])
    path = tmp_path / "gst.xlsx"
    df.to_excel(path, index=False, header=False)
    result = InvoiceAuditEngine().process_files([str(path)])
    assert result.summary.raw_rows_read == 2
    assert result.summary.final_approved_rows == 1
    assert result.summary.row_coverage_status == "MATCHED"



def test_date_parser_handles_common_formats_and_invalid():
    from app.core.date_parser import parse_invoice_date

    assert parse_invoice_date("31-01-2026")[0] == date(2026, 1, 31)
    assert parse_invoice_date("31/01/2026")[0] == date(2026, 1, 31)
    assert parse_invoice_date("2026-01-31")[0] == date(2026, 1, 31)
    assert parse_invoice_date("")[1] == "MISSING_DATE"
    assert parse_invoice_date("not-a-date")[1] == "INVALID_DATE_FORMAT"


def test_process_marks_empty_and_header_rows(tmp_path: Path):
    gstin = valid_gstin()
    df = pd.DataFrame([
        ["", "", ""],
        ["GSTIN of supplier", "Trade/Legal name", "Invoice number", "Invoice date", "Taxable Value", "CGST", "SGST", "IGST", "Invoice Value"],
        [gstin, "ABC Traders", "INV-1", "01-01-2026", 100, 9, 9, 0, 118],
    ])
    path = tmp_path / "empty_header.xlsx"
    df.to_excel(path, index=False, header=False)
    result = InvoiceAuditEngine().process_files([str(path)])
    statuses = [row.audit_status for row in result.rows]
    assert "SKIPPED_EMPTY" in statuses
    assert "SKIPPED_HEADER_OR_TITLE" in statuses
    assert result.summary.classified_rows == result.summary.raw_rows_read


def test_reconstruction_from_continuation_row_requires_review(tmp_path: Path):
    gstin = valid_gstin()
    df = pd.DataFrame([
        ["GSTIN of supplier", "Trade/Legal name", "Invoice number", "Invoice date", "Taxable Value", "CGST", "SGST", "IGST", "Invoice Value"],
        [gstin, "ABC", "INV-1", "01-01-2026", 100, 9, 9, 0, 118],
        ["", "TRADERS PRIVATE", "", "", "", "", "", "", ""],
    ])
    path = tmp_path / "continuation.xlsx"
    df.to_excel(path, index=False, header=False)
    result = InvoiceAuditEngine().process_files([str(path)])
    invoice_row = next(row for row in result.rows if row.gstin == gstin)
    assert invoice_row.reconstructed is True
    assert invoice_row.review_required is True
    assert "TRADERS PRIVATE" in invoice_row.supplier_name


def test_invalid_gstin_checksum_goes_to_review(tmp_path: Path):
    gstin = valid_gstin()
    bad = gstin[:-1] + ("0" if gstin[-1] != "0" else "1")
    df = pd.DataFrame([
        ["GSTIN of supplier", "Trade/Legal name", "Invoice number", "Invoice date", "Taxable Value", "CGST", "SGST", "IGST", "Invoice Value"],
        [bad, "ABC Traders", "INV-1", "01-01-2026", 100, 9, 9, 0, 118],
    ])
    path = tmp_path / "bad_gstin.xlsx"
    df.to_excel(path, index=False, header=False)
    result = InvoiceAuditEngine().process_files([str(path)])
    row = result.rows[-1]
    assert row.review_required is True
    assert "GSTIN checksum" in row.audit_notes


def test_money_format_handles_negative_and_plain_values():
    assert format_inr(Decimal("-123456.78")) == "-₹1,23,456.78"
    assert format_inr(Decimal("999.10")) == "₹999.10"
    assert format_inr(Decimal("0")) == "₹0.00"


def test_inr_compact_formatter_still_available():
    from app.core.money import format_inr_compact

    assert format_inr_compact(Decimal("193800000")) == "₹19.38Cr"
    assert format_inr_compact(Decimal("-123456.78")) == "-₹1.23L"


def test_database_context_manager_closes(tmp_path: Path):
    with AuditDatabase(tmp_path / "audit.sqlite3") as db:
        engine = InvoiceAuditEngine()
        result = engine.build_result_from_rows([make_row(1)], 1, 1)
        dataset_id = db.save_result("context", result.summary.to_dict(), result.rows)
        assert dataset_id > 0
    assert db.conn is None


def test_logging_setup_is_idempotent(tmp_path: Path):
    from app.core.logging_config import setup_logging

    log_path = tmp_path / "audit.log"
    setup_logging(log_path)
    setup_logging(log_path)
    assert log_path.parent.exists()


def test_corrected_explicit_gstin_sample_is_valid():
    # Previous review flagged 33AAACC1234F1Z5 as invalid; the correct checksum is F.
    assert is_valid_gstin("33AAACC1234F1ZF")
    assert not is_valid_gstin("33AAACC1234F1Z5")


def test_hsn_sac_detection_from_header(tmp_path: Path):
    gstin = valid_gstin()
    df = pd.DataFrame([
        ["GSTIN of supplier", "Trade/Legal name", "Invoice number", "HSN/SAC", "Invoice date", "Taxable Value", "CGST", "SGST", "IGST", "Invoice Value"],
        [gstin, "ABC Traders", "INV-1", "998314", "01-01-2026", 100, 9, 9, 0, 118],
    ])
    path = tmp_path / "hsn.xlsx"
    df.to_excel(path, index=False, header=False)
    result = InvoiceAuditEngine().process_files([str(path)])
    row = next(r for r in result.rows if r.gstin == gstin)
    assert row.hsn_sac == "998314"


def test_ignored_gstin_is_excluded_from_dashboard(tmp_path: Path):
    gstin = valid_gstin()
    df = pd.DataFrame([
        ["GSTIN of supplier", "Trade/Legal name", "Invoice number", "Invoice date", "Taxable Value", "CGST", "SGST", "IGST", "Invoice Value"],
        [gstin, "ABC Traders", "INV-1", "01-01-2026", 100, 9, 9, 0, 118],
    ])
    path = tmp_path / "ignored.xlsx"
    df.to_excel(path, index=False, header=False)
    result = InvoiceAuditEngine().process_files([str(path)], ignored_gstins=[gstin])
    row = next(r for r in result.rows if r.gstin == gstin)
    assert row.audit_status == "IGNORED_GSTIN_EXCLUDED"
    assert row.include_in_totals is False
    assert result.summary.final_approved_rows == 0


def test_database_creates_backup_before_bulk_review(tmp_path: Path):
    db_path = tmp_path / "audit.sqlite3"
    with AuditDatabase(db_path) as db:
        engine = InvoiceAuditEngine()
        row1 = make_row(1, include=False, review=True, status="REVIEW_REQUIRED")
        row2 = make_row(2, include=False, review=True, status="REVIEW_REQUIRED")
        result = engine.build_result_from_rows([row1, row2], 1, 1)
        dataset_id = db.save_result("backup-test", result.summary.to_dict(), result.rows)
        changed = db.update_review_decisions_bulk(dataset_id, [1, 2], "ACCEPTED_MANUAL", True, "ACCEPTED_WARNING_MANUAL", "📌", False, "bulk ok")
        assert changed == 2
        backups = list((tmp_path / "backups").glob("*.sqlite3"))
        assert backups


def test_bulk_review_decisions_load_back(tmp_path: Path):
    db_path = tmp_path / "audit.sqlite3"
    with AuditDatabase(db_path) as db:
        engine = InvoiceAuditEngine()
        rows = [make_row(1, include=False, review=True, status="REVIEW_REQUIRED"), make_row(2, include=False, review=True, status="REVIEW_REQUIRED")]
        result = engine.build_result_from_rows(rows, 1, 1)
        dataset_id = db.save_result("bulk-test", result.summary.to_dict(), result.rows)
        db.update_review_decisions_bulk(dataset_id, [1, 2], "REJECTED_MANUAL", False, "REJECTED_MANUAL_EXCLUDED", "❌", False, "not valid")
        loaded = db.load_rows(dataset_id)
        assert all(r.review_decision == "REJECTED_MANUAL" for r in loaded)
        assert all(not r.include_in_totals for r in loaded)


def test_export_verified_excel_includes_charts_sheet_and_protection(tmp_path: Path):
    engine = InvoiceAuditEngine()
    result = engine.build_result_from_rows([make_row(1), make_row(2)], 1, 1)
    output = export_verified_excel(result, tmp_path / "protected.xlsx", protection_password="audit")
    assert output.exists()
    sheets = pd.ExcelFile(output).sheet_names
    assert "Charts" in sheets


def test_csv_import_reads_rows_and_reconciles(tmp_path: Path):
    gstin = valid_gstin()
    path = tmp_path / "gst.csv"
    pd.DataFrame([
        ["GSTIN of supplier", "Trade/Legal name", "Invoice number", "Invoice date", "Taxable Value", "CGST", "SGST", "IGST", "Invoice Value"],
        [gstin, "ABC Traders", "INV-1", "01-01-2026", 100, 9, 9, 0, 118],
    ]).to_csv(path, index=False, header=False)
    result = InvoiceAuditEngine().process_files([str(path)])
    assert result.summary.files_processed == 1
    assert result.summary.sheets_processed == 1
    assert result.summary.final_approved_rows == 1
    assert result.summary.amount_reconciliation_status == "MATCHED"


def test_multi_gstin_detection_and_self_invoice_flag(tmp_path: Path):
    from app.core.gstin import detect_gstin_roles

    self_gstin = valid_gstin("33AAAAA1234A1Z")
    supplier_gstin = valid_gstin("33BBBBB1234B1Z")
    roles = detect_gstin_roles([supplier_gstin, self_gstin], self_gstins=[self_gstin])
    assert roles.supplier_gstin == supplier_gstin
    assert roles.recipient_gstin == self_gstin
    self_roles = detect_gstin_roles([self_gstin], self_gstins=[self_gstin])
    assert self_roles.self_invoice is True


def test_process_self_invoice_goes_to_review(tmp_path: Path):
    self_gstin = valid_gstin("33AAAAA1234A1Z")
    df = pd.DataFrame([
        ["GSTIN of supplier", "Trade/Legal name", "Invoice number", "Invoice date", "Taxable Value", "CGST", "SGST", "IGST", "Invoice Value"],
        [self_gstin, "Own Company", "SELF-1", "01-01-2026", 100, 9, 9, 0, 118],
    ])
    path = tmp_path / "self.xlsx"
    df.to_excel(path, index=False, header=False)
    result = InvoiceAuditEngine().process_files([str(path)], self_gstins=[self_gstin])
    row = next(r for r in result.rows if r.gstin == self_gstin)
    assert row.self_invoice_flag is True
    assert row.review_required is True
    assert row.include_in_totals is False


def test_enhanced_mismatch_suggestion_for_extra_charge():
    from app.core.audit_engine import classify_gst_mismatch_details

    detail = classify_gst_mismatch_details(Decimal("11850"), Decimal("11800"), Decimal("10000"), Decimal("1800"))
    assert detail["reason"] in {"POSSIBLE_FREIGHT_OR_DISCOUNT", "INVOICE_VALUE_INCLUDES_EXPENSES"}
    assert "Expected" in str(detail["suggestion"]) or "Taxable + GST" in str(detail["suggestion"])


def test_hsn_validation_rejects_bad_length():
    from app.core.hsn import validate_hsn_sac

    assert validate_hsn_sac("998314").is_valid is True
    assert validate_hsn_sac("123").is_valid is False
    assert validate_hsn_sac("123456789").is_valid is False


def test_invoice_number_series_parser_detects_sequence():
    from app.core.invoice_number import parse_invoice_number

    info = parse_invoice_number("INV-2026-001")
    assert info.sequence == 1
    assert "{n}" in info.series


def test_invoice_gap_annotation_marks_gap(tmp_path: Path):
    gstin = valid_gstin()
    df = pd.DataFrame([
        ["GSTIN of supplier", "Trade/Legal name", "Invoice number", "Invoice date", "Taxable Value", "CGST", "SGST", "IGST", "Invoice Value"],
        [gstin, "ABC Traders", "INV-001", "01-01-2026", 100, 9, 9, 0, 118],
        [gstin, "ABC Traders", "INV-003", "02-01-2026", 100, 9, 9, 0, 118],
        [gstin, "ABC Traders", "INV-004", "03-01-2026", 100, 9, 9, 0, 118],
    ])
    path = tmp_path / "gap.xlsx"
    df.to_excel(path, index=False, header=False)
    result = InvoiceAuditEngine().process_files([str(path)])
    invoice_rows = [r for r in result.rows if r.gstin == gstin]
    assert any("2" in r.invoice_gap_note for r in invoice_rows)


def test_large_csv_smoke_5000_rows(tmp_path: Path):
    gstin = valid_gstin()
    rows = [["GSTIN of supplier", "Trade/Legal name", "Invoice number", "Invoice date", "Taxable Value", "CGST", "SGST", "IGST", "Invoice Value"]]
    rows.extend([[gstin, "ABC Traders", f"INV-{i:05d}", "01-01-2026", 100, 9, 9, 0, 118] for i in range(1, 5001)])
    path = tmp_path / "large.csv"
    pd.DataFrame(rows).to_csv(path, index=False, header=False)
    result = InvoiceAuditEngine().process_files([str(path)])
    assert result.summary.raw_rows_read == 5001
    assert result.summary.final_approved_rows == 5000
    assert result.summary.row_coverage_status == "MATCHED"


def test_corrupted_file_is_isolated_not_crashing(tmp_path: Path):
    path = tmp_path / "broken.xlsx"
    path.write_text("not an excel file", encoding="utf-8")
    result = InvoiceAuditEngine().process_files([str(path)])
    assert result.summary.critical_rows == 1
    assert result.rows[0].audit_status == "ERROR_FILE_UNREADABLE"


def test_database_persists_v5_fields(tmp_path: Path):
    row = make_row(1)
    row.recipient_gstin = valid_gstin("33BBBBB1234B1Z")
    row.all_gstins = (row.gstin, row.recipient_gstin)
    row.hsn_sac = "998314"
    row.hsn_valid = True
    row.suggested_correction = "No correction needed"
    engine = InvoiceAuditEngine()
    result = engine.build_result_from_rows([row], 1, 1)
    with AuditDatabase(tmp_path / "audit.sqlite3") as db:
        dataset_id = db.save_result("v5", result.summary.to_dict(), result.rows)
        loaded = db.load_rows(dataset_id)[0]
    assert loaded.recipient_gstin == row.recipient_gstin
    assert loaded.all_gstins == row.all_gstins
    assert loaded.hsn_sac == "998314"
    assert loaded.suggested_correction == "No correction needed"


def test_header_detector_low_confidence_marks_rows_for_review(tmp_path: Path):
    gstin = valid_gstin()
    df = pd.DataFrame([
        [gstin, "ABC Traders", "INV-1", "01-01-2026", 100, 9, 9, 0, 118],
    ])
    path = tmp_path / "no_header.xlsx"
    df.to_excel(path, index=False, header=False)
    result = InvoiceAuditEngine().process_files([str(path)])
    row = next(r for r in result.rows if r.gstin == gstin)
    assert row.review_required is True
    assert row.include_in_totals is False
    assert "Header detection confidence too low" in row.audit_notes


def test_csv_utf16_bom_import(tmp_path: Path):
    gstin = valid_gstin()
    path = tmp_path / "utf16.csv"
    pd.DataFrame([
        ["GSTIN of supplier", "Trade/Legal name", "Invoice number", "Invoice date", "Taxable Value", "CGST", "SGST", "IGST", "Invoice Value"],
        [gstin, "ABC Traders", "INV-1", "01-01-2026", 100, 9, 9, 0, 118],
    ]).to_csv(path, index=False, header=False, encoding="utf-16")
    result = InvoiceAuditEngine().process_files([str(path)])
    assert result.summary.final_approved_rows == 1


def test_sqlite_user_version_migration_from_old_schema(tmp_path: Path):
    import sqlite3

    db_path = tmp_path / "old.sqlite3"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE datasets (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, created_at TEXT, summary_json TEXT NOT NULL)")
    conn.execute(
        """
        CREATE TABLE invoice_rows (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dataset_id INTEGER NOT NULL,
            row_id INTEGER NOT NULL,
            source_file TEXT,
            sheet_name TEXT,
            excel_row_number INTEGER,
            supplier_name TEXT,
            gstin TEXT,
            invoice_no TEXT,
            invoice_date TEXT,
            period TEXT,
            taxable_value TEXT,
            igst TEXT,
            cgst TEXT,
            sgst TEXT,
            cess TEXT,
            invoice_value TEXT,
            expected_invoice_value TEXT,
            difference_amount TEXT,
            difference_percent TEXT,
            mismatch_reason TEXT,
            audit_status TEXT,
            audit_severity TEXT,
            audit_indicator TEXT,
            audit_notes TEXT,
            review_required INTEGER,
            review_decision TEXT,
            include_in_totals INTEGER,
            reconstructed INTEGER,
            duplicate_key TEXT,
            raw_snapshot_json TEXT,
            detected_snapshot_json TEXT,
            final_snapshot_json TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()

    with AuditDatabase(db_path) as db:
        version = db.conn.execute("PRAGMA user_version").fetchone()[0]
        cols = {r[1] for r in db.conn.execute("PRAGMA table_info(invoice_rows)").fetchall()}
    assert version >= 6
    assert "anomaly_note" in cols
    assert "all_gstins_json" in cols
    assert list((tmp_path / "backups").glob("*.sqlite3"))


def test_safety_row_limit_isolated_as_file_error(tmp_path: Path):
    from app.core.config import AuditConfig

    gstin = valid_gstin()
    path = tmp_path / "too_many.csv"
    pd.DataFrame([
        ["GSTIN of supplier", "Trade/Legal name", "Invoice number", "Invoice date", "Taxable Value", "CGST", "SGST", "IGST", "Invoice Value"],
        [gstin, "ABC Traders", "INV-1", "01-01-2026", 100, 9, 9, 0, 118],
    ]).to_csv(path, index=False, header=False)
    result = InvoiceAuditEngine(config=AuditConfig(max_rows_per_file=1)).process_files([str(path)])
    assert any(r.audit_status == "ERROR_FILE_UNREADABLE" for r in result.rows)
    assert result.summary.critical_rows == 1


def test_supplier_totals_use_gstin_not_cleaned_name_only():
    gstin1 = valid_gstin("33AAAAA1234A1Z")
    gstin2 = valid_gstin("33BBBBB1234B1Z")
    row1 = make_row(1, invoice="118.00")
    row1.gstin = gstin1
    row1.supplier_name = "ABC Traders Pvt Ltd"
    row2 = make_row(2, invoice="236.00")
    row2.gstin = gstin2
    row2.supplier_name = "ABC Traders Ltd"
    result = InvoiceAuditEngine().build_result_from_rows([row1, row2], 1, 1)
    assert len(result.supplier_totals) == 2
    assert any(gstin1 in key for key in result.supplier_totals)
    assert any(gstin2 in key for key in result.supplier_totals)


def test_excel_export_sanitizes_formula_like_text_values(tmp_path):
    from app.core.exporter import sanitize_excel_value, sanitize_excel_dataframe

    assert sanitize_excel_value("=HYPERLINK('x','click')") == "'=HYPERLINK('x','click')"
    assert sanitize_excel_value("+SUM(1,2)") == "'+SUM(1,2)"
    assert sanitize_excel_value("@cmd") == "'@cmd"
    assert sanitize_excel_value("Normal Supplier") == "Normal Supplier"

    df = pd.DataFrame({"supplier": ["=BAD()", "Safe"], "amount": [1, 2]})
    safe = sanitize_excel_dataframe(df)
    assert safe.loc[0, "supplier"] == "'=BAD()"
    assert safe.loc[0, "amount"] == 1


def test_review_decision_log_is_hash_chained(tmp_path):
    db = AuditDatabase(tmp_path / "audit.sqlite3")
    result = InvoiceAuditEngine().process_files([str(tmp_path / "input.csv")]) if False else None
    row = make_row(row_id=1, include=False, review=True, status="REVIEW_REQUIRED")
    dataset_id = db.save_result("hash-test", {"status": "test"}, [row])
    db.update_review_decision(
        dataset_id,
        row.row_id,
        decision="ACCEPTED_MANUAL",
        include_in_totals=True,
        status="VALID_MANUAL",
        indicator="📌",
        review_required=False,
        note="checked",
    )
    db.update_review_decision(
        dataset_id,
        row.row_id,
        decision="REJECTED_MANUAL",
        include_in_totals=False,
        status="REJECTED_MANUAL",
        indicator="❌",
        review_required=False,
        note="reversed",
    )
    logs = db.conn.execute(
        "SELECT previous_hash, decision_hash FROM review_decisions WHERE dataset_id=? ORDER BY id",
        (dataset_id,),
    ).fetchall()
    assert len(logs) == 2
    assert logs[0]["previous_hash"] == "GENESIS"
    assert len(logs[0]["decision_hash"]) == 64
    assert logs[1]["previous_hash"] == logs[0]["decision_hash"]
    assert len(logs[1]["decision_hash"]) == 64
    db.close()
