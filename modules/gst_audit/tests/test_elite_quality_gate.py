from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd

from app.core.audit_engine import InvoiceAuditEngine
from app.core.exporter import export_verified_excel
from app.core.gstin import calculate_gstin_checksum
from app.core.models import InvoiceRow
from app.core.quality_gate import quality_gate_dataframe, quality_gate_score, quality_gate_status


def _valid_gstin(prefix: str = "33ABCDE1234F1Z") -> str:
    return prefix + calculate_gstin_checksum(prefix)


def _row(row_id: int = 1, *, include: bool = True, review: bool = False, status: str = "VALID", severity: str = "LOW") -> InvoiceRow:
    row = InvoiceRow(
        row_id=row_id,
        source_file="client_purchase_register.xlsx",
        sheet_name="B2B",
        excel_row_number=row_id + 1,
        raw_snapshot=["raw"],
        supplier_name="ABC Traders",
        gstin=_valid_gstin(),
        invoice_no=f"INV-{row_id}",
        invoice_date=date(2026, 1, 1),
        taxable_value=Decimal("100.00"),
        cgst=Decimal("9.00"),
        sgst=Decimal("9.00"),
        invoice_value=Decimal("118.00"),
        expected_invoice_value=Decimal("118.00"),
        difference_amount=Decimal("0.00"),
        mismatch_reason="BALANCED_OR_ROUNDING",
        audit_status=status,
        audit_severity=severity,
        review_required=review,
        include_in_totals=include,
        review_decision="ACCEPTED_AUTO" if include else "PENDING_REVIEW",
    )
    row.detected_snapshot = {"gstin": row.gstin, "invoice_no": row.invoice_no}
    row.final_snapshot = dict(row.detected_snapshot)
    return row


def test_quality_gate_ready_for_clean_result():
    result = InvoiceAuditEngine().build_result_from_rows([_row(1)], 1, 1)
    df = quality_gate_dataframe(result)
    assert set(df["status"]) == {"PASS"}
    assert quality_gate_status(result) == "READY_TO_LOCK"
    assert quality_gate_score(result) == 100


def test_quality_gate_warns_for_open_review_rows():
    review_row = _row(2, include=False, review=True, status="REVIEW_REQUIRED", severity="HIGH")
    result = InvoiceAuditEngine().build_result_from_rows([_row(1), review_row], 1, 1)
    df = quality_gate_dataframe(result)
    assert "WARN" in set(df["status"])
    assert quality_gate_status(result) == "REVIEW_REQUIRED"
    assert 0 < quality_gate_score(result) < 100


def test_export_includes_quality_gate_and_unique_signoff_fields(tmp_path: Path):
    result = InvoiceAuditEngine().build_result_from_rows([_row(1)], 1, 1)
    output = export_verified_excel(result, tmp_path / "verified_quality_gate.xlsx")
    sheets = pd.ExcelFile(output).sheet_names
    assert "Quality Gate" in sheets

    cover = pd.read_excel(output, sheet_name="Cover Sheet", header=1)
    assert "Quality gate score" in set(cover["field"])

    signoff = pd.read_excel(output, sheet_name="Sign Off", header=1)
    fields = signoff["sign_off_field"].tolist()
    assert fields.count("GSTIN") == 1
