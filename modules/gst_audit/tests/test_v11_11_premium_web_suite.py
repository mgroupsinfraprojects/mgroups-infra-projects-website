from __future__ import annotations

from pathlib import Path

from web_portal.auth import AuthError, WebAuthManager
from web_portal.audit_service import WebAuditService

ROOT = Path(__file__).resolve().parents[1]


def test_premium_web_auth_roles_and_permissions(tmp_path: Path) -> None:
    auth = WebAuthManager(tmp_path / "auth")
    admin = auth.authenticate("admin", "admin123")
    viewer = auth.authenticate("viewer", "view123")

    assert admin.role == "admin"
    assert auth.permissions_for(admin)["audit_log"] is True
    assert auth.permissions_for(viewer)["upload"] is False
    assert auth.permissions_for(viewer)["export"] is True

    try:
        auth.authenticate("admin", "wrong")
    except AuthError as exc:
        assert "Invalid username" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Bad password accepted")


def test_premium_web_payload_has_executive_summary_and_activity_log(tmp_path: Path) -> None:
    service = WebAuditService(tmp_path / "runtime")
    sample = ROOT / "sample_data" / "01_balanced_invoices.xlsx"
    session = service.create_audit([(sample.name, sample.read_bytes())], actor="admin", role="admin")
    payload = service.dashboard(session.session_id, {"authenticated": True, "username": "admin"})

    assert payload["has_result"] is True
    assert "executive" in payload
    assert payload["executive"]["readiness_score"] >= 0
    assert payload["summary"]["readiness_grade"]
    assert payload["activity"]
    assert payload["activity"][0]["event"] == "audit_uploaded"


def test_premium_web_review_export_and_audit_log_csv(tmp_path: Path) -> None:
    service = WebAuditService(tmp_path / "runtime")
    sample = ROOT / "sample_data" / "02_review_and_duplicate_cases.xlsx"
    session = service.create_audit([(sample.name, sample.read_bytes())], actor="auditor", role="auditor")
    review_ids = [row.row_id for row in session.result.rows if row.review_required]
    if review_ids:
        service.apply_decision(session.session_id, review_ids[:1], "approve", actor="auditor", role="auditor")

    export_path = service.export_session(session.session_id, actor="auditor", role="auditor")
    log_path = service.audit_log_csv()

    assert export_path.exists()
    assert log_path.exists()
    text = log_path.read_text(encoding="utf-8")
    assert "audit_uploaded" in text
    assert "export_created" in text
