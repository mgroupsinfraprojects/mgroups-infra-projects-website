from __future__ import annotations

from pathlib import Path

from web_portal.audit_service import WebAuditError, WebAuditService
from web_portal.server import parse_multipart

ROOT = Path(__file__).resolve().parents[1]


def test_web_service_processes_sample_and_populates_dashboard(tmp_path: Path) -> None:
    service = WebAuditService(tmp_path / "runtime")
    sample = ROOT / "sample_data" / "01_balanced_invoices.xlsx"
    session = service.create_audit([(sample.name, sample.read_bytes())])

    payload = service.result_payload(session)
    summary = payload["summary"]

    assert payload["has_result"] is True
    assert summary["files_processed"] == 1
    assert summary["raw_rows_read"] > 0
    assert summary["approved_rows"] > 0
    assert summary["invoice_value"] != "0.00"
    assert summary["taxable_value"] != "0.00"
    assert summary["total_gst"] != "0.00"
    assert payload["suppliers"]
    assert payload["months"]


def test_web_service_exports_verified_excel(tmp_path: Path) -> None:
    service = WebAuditService(tmp_path / "runtime")
    sample = ROOT / "sample_data" / "01_balanced_invoices.xlsx"
    session = service.create_audit([(sample.name, sample.read_bytes())])

    export_path = service.export_session(session.session_id)

    assert export_path.exists()
    assert export_path.suffix == ".xlsx"
    assert export_path.stat().st_size > 0


def test_web_service_rejects_unsupported_upload(tmp_path: Path) -> None:
    service = WebAuditService(tmp_path / "runtime")

    try:
        service.create_audit([("bad.pdf", b"%PDF-1.7")])
    except WebAuditError as exc:
        assert "Unsupported file type" in str(exc)
    else:  # pragma: no cover - assertion path
        raise AssertionError("Unsupported file type was accepted")


def test_multipart_parser_extracts_multiple_files() -> None:
    boundary = "----GSTAuditBoundary"
    body = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="files"; filename="one.csv"\r\n'
        "Content-Type: text/csv\r\n\r\n"
        "a,b\n1,2\r\n"
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="files"; filename="two.csv"\r\n'
        "Content-Type: text/csv\r\n\r\n"
        "c,d\n3,4\r\n"
        f"--{boundary}--\r\n"
    ).encode("utf-8")

    fields, files = parse_multipart(body, f"multipart/form-data; boundary={boundary}")

    assert fields == {}
    assert [name for name, _ in files] == ["one.csv", "two.csv"]
    assert files[0][1].startswith(b"a,b")
