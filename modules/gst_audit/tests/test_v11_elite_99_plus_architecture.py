from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from app.audit_trail.event_logger import AuditTrailLogger
from app.audit_trail.tamper_check import verify_audit_trail
from app.core.models import InvoiceRow
from app.einvoice.einvoice_payload_builder import build_einvoice_payload
from app.ewaybill.eway_payload_builder import build_eway_payload
from app.gstn.gsp_client import GspClient, IntegrationNotConfigured
from app.security.permission_matrix import PermissionMatrix
from app.storage.database import Database
from app.storage.review_decision_repo import ReviewDecision, ReviewDecisionRepository
from app.workflow.audit_workflow_controller import AuditWorkflowController
from app.workspace.company_manager import CompanyManager, CompanyProfile


def _row(row_id: int, *, review=False) -> InvoiceRow:
    return InvoiceRow(
        row_id=row_id,
        source_file="sample.xlsx",
        sheet_name="Sheet1",
        excel_row_number=row_id + 1,
        raw_snapshot=[],
        supplier_name="ABC SUPPLIER",
        gstin="29ABCDE1234F1Z5" if not review else "",
        invoice_no=f"INV-{row_id}" if not review else "",
        taxable_value=Decimal("100.00"),
        igst=Decimal("18.00"),
        invoice_value=Decimal("118.00"),
        expected_invoice_value=Decimal("118.00"),
        mismatch_reason="" if not review else "MISSING_CRITICAL_FIELD",
        audit_status="MATCHED" if not review else "REVIEW_REQUIRED",
        audit_severity="LOW" if not review else "CRITICAL",
        review_required=review,
        include_in_totals=not review,
    )


def test_workflow_controller_persists_session_and_classifies_queue(tmp_path: Path) -> None:
    controller = AuditWorkflowController(tmp_path / "audit.sqlite")
    state = controller.start_session(company_id="C1", gstin="29ABCDE1234F1Z5", financial_year="2025-26", period="APR")
    result = controller.classify_review(state, [_row(1), _row(2, review=True)], actor="tester")
    assert result.export_blocked is True
    assert result.dashboard["gst_fix_first"]["mandatory_review_count"] >= 1
    assert controller.sessions is not None
    reopened = controller.sessions.get_session(state.session_id)
    assert reopened is not None
    assert reopened.metadata["export_blocked"] is True


def test_review_decision_requires_reason_and_persists(tmp_path: Path) -> None:
    db = Database(tmp_path / "audit.sqlite"); db.initialize()
    controller = AuditWorkflowController(tmp_path / "audit.sqlite")
    state = controller.start_session()
    repo = ReviewDecisionRepository(controller.db)
    with pytest.raises(ValueError):
        repo.save(ReviewDecision(session_id=state.session_id, row_id=1, decision="APPROVED", actor="u", reason=""))
    rid = repo.save(ReviewDecision(session_id=state.session_id, row_id=1, decision="APPROVED", actor="u", reason="Source checked"))
    assert rid > 0
    assert repo.list_for_session(state.session_id)[0]["reason"] == "Source checked"


def test_audit_trail_hash_chain_detects_tampering(tmp_path: Path) -> None:
    db = Database(tmp_path / "audit.sqlite"); db.initialize()
    logger = AuditTrailLogger(db)
    logger.record("S1", "u", "A", {"x": 1})
    logger.record("S1", "u", "B", {"x": 2})
    ok, errors = verify_audit_trail(db, "S1")
    assert ok and not errors
    with db.connect() as conn:
        conn.execute("UPDATE audit_events SET payload_json='{}' WHERE id=1")
        conn.commit()
    ok, errors = verify_audit_trail(db, "S1")
    assert not ok
    assert errors


def test_statutory_integrations_block_fake_live_actions() -> None:
    client = GspClient()
    assert client.configured is False
    with pytest.raises(IntegrationNotConfigured):
        client.ensure_configured()


def test_einvoice_and_eway_payload_validation() -> None:
    einv = build_einvoice_payload({"supplier_gstin":"29ABCDE1234F1Z5", "recipient_gstin":"33ABCDE1234F1Z5", "invoice_no":"A1", "invoice_date":"2026-04-01", "invoice_value":"118.00"})
    assert einv["schema_status"] == "LOCAL_VALIDATED"
    eway = build_eway_payload({"supplier_gstin":"29ABCDE1234F1Z5", "recipient_gstin":"33ABCDE1234F1Z5", "invoice_no":"A1", "invoice_value":"60000", "from_state":"KA", "to_state":"TN"})
    assert eway["schema_status"] == "LOCAL_VALIDATED"


def test_rbac_and_workspace_contracts() -> None:
    assert PermissionMatrix().allowed("manager", "EXPORT") is True
    assert PermissionMatrix().allowed("viewer", "EXPORT") is False
    mgr = CompanyManager()
    mgr.add_company(CompanyProfile(company_id="C1", legal_name="Client Pvt Ltd", pan="ABCDE1234F", gstins=("29ABCDE1234F1Z5",), financial_years=("2025-26",)))
    assert mgr.get_company("C1") is not None
