from pathlib import Path

import pandas as pd

from web_portal.audit_service import WebAuditService
from web_portal.server import LOCAL_USER_PAYLOAD


def test_v11_13_web_has_no_login_permissions_needed() -> None:
    assert LOCAL_USER_PAYLOAD["authenticated"] is True
    assert LOCAL_USER_PAYLOAD["permissions"]["upload"] is True
    assert LOCAL_USER_PAYLOAD["permissions"]["review"] is True
    assert LOCAL_USER_PAYLOAD["permissions"]["export"] is True


def test_v11_13_web_strict_invoice_rows_exclude_header_support_rows(tmp_path: Path) -> None:
    path = tmp_path / "mixed_gstr2b.csv"
    pd.DataFrame([
        ["GSTIN of Supplier", "Trade/Legal name", "Invoice number", "Invoice date", "Taxable Value", "CGST", "SGST", "IGST", "Invoice Value"],
        ["Invoice type", "Invoice date", "Invoice value", "Place of supply", "Supply attract Reverse charge", "Taxable value", "Integrated Tax", "Source", "IRN"],
        ["ITC Availability", "Reason", "Applicable % of Tax Rate", "Source", "IRN", "", "", "", ""],
        ["33ABCDE1234F1Z7", "ABC Traders", "INV-1", "01-10-2025", 1000, 90, 90, 0, 1180],
        ["33ABCDE1234F1Z7", "ABC Traders", "INV-2", "02-10-2025", 2000, 180, 180, 0, 2360],
        ["No GSTIN", "Missing invoice no", "", "", 100, 9, 9, 0, 118],
    ]).to_csv(path, index=False, header=False)

    service = WebAuditService(tmp_path / "runtime")
    session = service.create_audit([(path.name, path.read_bytes())])
    payload = service.result_payload(session)

    assert payload["summary"]["web_invoice_rows"] == 2
    assert payload["summary"]["approved_rows"] >= 1
    assert payload["summary"]["detected_invoice_value"] == "3,540.00"
    assert all(row["gstin"] == "33ABCDE1234F1Z7" for row in payload["invoice_rows"])
    assert all(row["invoice_no"] in {"INV-1", "INV-2"} for row in payload["invoice_rows"])
    assert all(row["supplier_name"] == "ABC Traders" for row in payload["review_rows"])
    assert payload["months"]
    assert payload["suppliers"]
