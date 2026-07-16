from decimal import Decimal
from pathlib import Path

import pytest

from app.core.audit_engine import InvoiceAuditEngine, classify_gst_mismatch_details
from app.core.config import AuditConfig
from app.core.models import AuditSummary, InvoiceRow


def test_audit_summary_has_no_row_review_methods():
    summary = AuditSummary()
    assert not hasattr(summary, "append_audit_note")
    assert not hasattr(summary, "apply_review_decision")


def test_invoice_row_apply_review_decision_validates_state():
    row = InvoiceRow(row_id=1, source_file="f.xlsx", sheet_name="S", excel_row_number=1, raw_snapshot=[])
    row.apply_review_decision(True, "ACCEPTED_MANUAL", "VALID", "✅")
    assert row.include_in_totals is True
    assert row.review_required is False
    row.review_required = True
    with pytest.raises(ValueError):
        row.validate_state()


def test_zero_rated_credit_note_is_low_severity_and_included():
    detail = classify_gst_mismatch_details(
        invoice_value=Decimal("-100.00"),
        expected_value=Decimal("0.00"),
        taxable=Decimal("0.00"),
        gst_total=Decimal("0.00"),
    )
    assert detail["reason"] == "CREDIT_NOTE_ZERO_RATED"
    assert detail["severity"] == "LOW"
    assert detail["review"] is False
    assert detail["include"] is True


def test_gst_portal_csv_with_metadata_rows_processes(tmp_path: Path):
    csv_path = tmp_path / "IMS_B2B_sample.csv"
    csv_path.write_text(
        "Goods and Services Tax - IMS\n"
        "Taxable inward supplies received from registered persons\n"
        "GSTIN of Supplier,Trade/Legal name,Invoice Number,Invoice type,Invoice Date,Invoice Value,Place of supply,Reverse Charge,Taxable Value,Integrated Tax,Central Tax,State/UT Tax,Cess\n"
        "33AABCU9603R1ZU,ALAMPATA,INV-001,Regular,01/01/2026,1180.00,Tamil Nadu,N,1000.00,0.00,90.00,90.00,0.00\n",
        encoding="utf-8-sig",
    )
    result = InvoiceAuditEngine(AuditConfig()).process_files([csv_path])
    assert result.summary.row_coverage_status == "MATCHED"
    assert result.summary.amount_reconciliation_status == "MATCHED"
    assert any(row.audit_status == "VALID" for row in result.rows)
    assert result.summary.final_approved_rows == 1


def test_pdf_rejected_with_specific_status(tmp_path: Path):
    pdf_path = tmp_path / "GSTR3B.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fake")
    result = InvoiceAuditEngine(AuditConfig()).process_files([pdf_path])
    assert result.rows[0].audit_status == "ERROR_UNSUPPORTED_FILE_TYPE"
    assert "PDF import is not supported" in result.rows[0].audit_notes


def test_encoding_fallback_logs_warning(tmp_path: Path, monkeypatch, caplog):
    path = tmp_path / "bad.csv"
    path.write_bytes(b"x,y\n1,2\n")
    engine = InvoiceAuditEngine(AuditConfig())

    real_open = Path.open

    def raising_open(self, *args, **kwargs):
        if self == path and "encoding" in kwargs:
            raise UnicodeError("forced failure")
        return real_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", raising_open)
    with caplog.at_level("WARNING"):
        assert engine._detect_csv_encoding(path) == "utf-8-sig"
    assert "CSV encoding detection failed" in caplog.text
