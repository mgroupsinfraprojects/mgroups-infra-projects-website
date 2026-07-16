from pathlib import Path

import pandas as pd

from app.core.audit_engine import InvoiceAuditEngine
from web_portal.audit_service import WebAuditService


def test_gstr_header_bands_are_not_invoice_review_rows(tmp_path: Path) -> None:
    path = tmp_path / "gstr2b_like.csv"
    pd.DataFrame([
        ["GSTIN of Supplier", "Trade/Legal name", "Invoice number", "Invoice date", "Taxable Value", "CGST", "SGST", "IGST", "Invoice Value"],
        ["Invoice type", "Invoice date", "Invoice value", "Place of supply", "Supply attract Reverse charge", "Taxable value", "Integrated Tax", "Source", "IRN"],
        ["33ABCDE1234F1Z7", "ABC Traders", "INV-1", "01-10-2025", 100, 9, 9, 0, 118],
    ]).to_csv(path, index=False, header=False)

    result = InvoiceAuditEngine().process_files([str(path)])

    assert result.summary.final_approved_rows == 1
    assert result.summary.review_required_rows == 0
    assert any(row.audit_status in {"SKIPPED_HEADER_OR_SUPPORT_ROW", "SKIPPED_HEADER_OR_TITLE"} for row in result.rows)

    service = WebAuditService(runtime_dir=tmp_path / "runtime")
    session = service.create_audit([(path.name, path.read_bytes())], actor="admin", role="admin")
    payload = service.result_payload(session)

    assert payload["summary"]["review_rows"] == 0
    assert payload["review_rows"] == []
    assert payload["approved_preview"][0]["supplier_name"] in {"Abc", "Abc Traders"}
    assert payload["approved_preview"][0]["gstin"] == "33ABCDE1234F1Z7"
    assert payload["approved_preview"][0]["invoice_no"] == "INV-1"
    assert payload["approved_preview"][0]["invoice_value"] == "118.00"
