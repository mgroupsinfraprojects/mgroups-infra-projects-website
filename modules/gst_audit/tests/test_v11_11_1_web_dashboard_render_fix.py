from __future__ import annotations

import json
import re
from http import HTTPStatus
from pathlib import Path

from web_portal.server import json_for_script
from web_portal.audit_service import WebAuditService
from web_portal.auth import WebAuthManager

ROOT = Path(__file__).resolve().parents[1]


def test_json_for_script_is_valid_json_not_html_escaped() -> None:
    payload = {"has_result": True, "summary": {"invoice_value": "41,300.00"}, "text": "A&B <GST>"}
    rendered = json_for_script(payload)

    assert "&quot;" not in rendered
    assert "&#34;" not in rendered
    assert "\\u003c" in rendered
    assert json.loads(rendered)["summary"]["invoice_value"] == "41,300.00"


def test_premium_index_payload_can_be_parsed_after_upload(tmp_path: Path) -> None:
    service = WebAuditService(tmp_path / "runtime")
    auth = WebAuthManager(tmp_path / "auth")
    admin = auth.authenticate("admin", "admin123")
    sample = ROOT / "sample_data" / "01_balanced_invoices.xlsx"
    session = service.create_audit([(sample.name, sample.read_bytes())], actor="admin", role="admin")
    payload = service.dashboard(session.session_id, auth.public_user_payload(admin))
    script_json = json_for_script(payload)
    parsed = json.loads(script_json)

    assert parsed["has_result"] is True
    assert parsed["summary"]["invoice_value"] != "0.00"
    assert parsed["months"]
    assert parsed["suppliers"]
