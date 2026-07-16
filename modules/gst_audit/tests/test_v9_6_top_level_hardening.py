from __future__ import annotations

from pathlib import Path

from app.core.audit_engine import InvoiceAuditEngine
from app.core.database import AuditDatabase
from app.core.gstin import calculate_gstin_checksum
from app.core.security import Permission, Role, decrypt_bytes, encrypt_bytes, has_permission, sha256_file


def valid_gstin(prefix: str = "33ABCDE1234F1Z") -> str:
    return prefix + calculate_gstin_checksum(prefix)


def test_v96_csv_reader_streams_and_handles_sep_metadata(tmp_path: Path) -> None:
    gstin = valid_gstin()
    csv_path = tmp_path / "portal_export.csv"
    csv_path.write_text(
        "sep=;\n"
        "GSTR-2B;B2B Invoices\n"
        "GSTIN/UIN of Supplier;Trade/Legal name of Supplier;Invoice number;Invoice date;Taxable Value(₹);Integrated Tax(₹);Central Tax(₹);State/UT Tax(₹);Invoice Value\n"
        f"{gstin};ABC Traders;INV-1;01-01-2026;100.00;0.00;9.00;9.00;118.00\n",
        encoding="utf-8-sig",
    )

    result = InvoiceAuditEngine().process_files([str(csv_path)])
    assert result.summary.files_processed == 1
    assert result.summary.final_approved_rows == 1
    assert result.summary.approved_invoice_value == 118
    assert any(row.audit_status == "SKIPPED_HEADER_OR_TITLE" and "delimiter declaration" in row.audit_notes for row in result.rows)


def test_v96_utf16_tab_gst_csv_is_processed(tmp_path: Path) -> None:
    gstin = valid_gstin("33ABCDE1234F2Z")
    csv_path = tmp_path / "portal_utf16.tsv"
    csv_path.write_text(
        "GSTIN of Supplier\tLegal name of Supplier\tInvoice No\tInvoice Date\tTaxable Value\tCGST\tSGST\tIGST\tInvoice Value\n"
        f"{gstin}\tXYZ Services\tCN-1\t02/01/2026\t100\t9\t9\t0\t118\n",
        encoding="utf-16",
    )

    result = InvoiceAuditEngine().process_files([str(csv_path)])
    assert result.summary.final_approved_rows == 1
    assert result.rows[-1].supplier_name == "XYZ Services"


def test_v96_csv_engine_does_not_reintroduce_all_rows_buffer() -> None:
    source = Path("app/core/audit_engine.py").read_text(encoding="utf-8")
    assert "all_rows_buffered" not in source
    assert "raw_rows: List[List[object]]" not in source
    assert "preview_rows: List[tuple[int, List[object]]]" in source
    assert "def remaining_records" in source


def test_v96_security_encryption_roundtrip_and_rbac(tmp_path: Path) -> None:
    payload = b"sensitive gst audit export"
    encrypted = encrypt_bytes(payload, "strong test password")
    assert encrypted != payload
    assert decrypt_bytes(encrypted, "strong test password") == payload
    assert has_permission(Role.ADMIN, Permission.MANAGE_USERS)
    assert has_permission(Role.REVIEWER, Permission.REVIEW_ROWS)
    assert not has_permission(Role.VIEWER, Permission.EXPORT_REPORTS)

    source = tmp_path / "audit.txt"
    source.write_text("invoice data", encoding="utf-8")
    assert len(sha256_file(source)) == 64


def test_v96_database_review_hash_chain_verifies(tmp_path: Path) -> None:
    from datetime import date
    from decimal import Decimal

    from app.core.models import InvoiceRow

    db = AuditDatabase(tmp_path / "audit.sqlite3")
    try:
        engine = InvoiceAuditEngine()
        row = InvoiceRow(
            row_id=1,
            source_file="sample.xlsx",
            sheet_name="Sheet1",
            excel_row_number=1,
            raw_snapshot=["raw"],
            supplier_name="ABC Traders",
            gstin=valid_gstin(),
            invoice_no="INV-1",
            invoice_date=date(2026, 1, 1),
            taxable_value=Decimal("100.00"),
            cgst=Decimal("9.00"),
            sgst=Decimal("9.00"),
            invoice_value=Decimal("118.00"),
            expected_invoice_value=Decimal("118.00"),
            difference_amount=Decimal("0.00"),
            mismatch_reason="BALANCED_OR_ROUNDING",
            audit_status="REVIEW_REQUIRED",
            include_in_totals=False,
            review_required=True,
            review_decision="PENDING_REVIEW",
        )
        result = engine.build_result_from_rows([row], 1, 1)
        dataset_id = db.save_result("chain", result.summary.to_dict(), result.rows)
        db.update_review_decision(dataset_id, 1, "ACCEPTED_MANUAL", True, "ACCEPTED_WARNING_MANUAL", "📌", False, "checked")
        ok, problems = db.verify_review_decision_chain(dataset_id)
        assert ok is True
        assert problems == []
    finally:
        db.close()
