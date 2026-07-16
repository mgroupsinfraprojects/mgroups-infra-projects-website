from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

from app.core.executive_dashboard import build_fix_first_dashboard
from app.core.models import InvoiceRow
from app.core.review_queue_engine import build_review_queue, summarize_review_queue
from app.core.supplier_intelligence import build_supplier_drilldowns
from app.version import APP_VERSION, RELEASE_NAME

ROOT = Path(__file__).resolve().parents[1]


def row(**kwargs) -> InvoiceRow:
    base = dict(row_id=kwargs.pop("row_id", 1), source_file="sample.xlsx", sheet_name="b2b", excel_row_number=2, raw_snapshot=[])
    base.update(kwargs)
    return InvoiceRow(**base)


def test_v10_release_identity_and_docs_are_present() -> None:
    assert APP_VERSION == "11.13.0"
    assert "V10 Perfect Workflow" in RELEASE_NAME
    assert "11.13.0" in (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert (ROOT / "docs" / "V10_PERFECT_WORKFLOW_RELEASE.md").exists()
    assert (ROOT / "docs" / "V10_SCORECARD.md").exists()


def test_v10_review_queue_blocks_only_important_rows() -> None:
    rows = [
        row(
            row_id=1,
            supplier_name="ABC Traders",
            gstin="",
            invoice_no="INV-1",
            review_required=True,
            audit_notes="GSTIN NOT DETECTED",
            invoice_value=Decimal("1000.00"),
        ),
        row(
            row_id=2,
            supplier_name="Small Diff Supplier",
            gstin="33ABCDE1234F1Z5",
            invoice_no="INV-2",
            review_required=True,
            mismatch_reason="MINOR_ROUNDING_OR_DECIMAL_ISSUE",
            difference_amount=Decimal("0.45"),
            invoice_value=Decimal("500.00"),
        ),
        row(
            row_id=3,
            review_required=True,
            audit_status="SKIPPED_EMPTY_ROW",
            mismatch_reason="NO_AMOUNT_DETECTED",
            include_in_totals=False,
        ),
    ]
    queue = build_review_queue(rows)
    summary = summarize_review_queue(queue)
    assert [item.bucket for item in queue[:3]] == ["MANDATORY_REVIEW", "TRACE_ONLY", "MATCHED"]
    assert summary.export_blocked
    assert summary.mandatory_count == 1
    assert summary.trace_only_count == 1
    assert queue[0].issue_type == "GSTIN / tax identity problem"
    assert queue[0].can_block_export


def test_v10_supplier_drilldown_contains_invoice_level_decisions() -> None:
    rows = [
        row(
            row_id=10,
            supplier_name="ABC Traders",
            gstin="33ABCDE1234F1Z5",
            invoice_no="A-1",
            invoice_date=date(2026, 4, 1),
            taxable_value=Decimal("1000.00"),
            cgst=Decimal("90.00"),
            sgst=Decimal("90.00"),
            invoice_value=Decimal("1180.00"),
            include_in_totals=True,
        ),
        row(
            row_id=11,
            supplier_name="ABC Traders",
            gstin="33ABCDE1234F1Z5",
            invoice_no="A-2",
            invoice_date=date(2026, 4, 2),
            review_required=True,
            audit_severity="HIGH",
            mismatch_reason="UNEXPLAINED_GST_MISMATCH",
            difference_amount=Decimal("3000.00"),
            invoice_value=Decimal("2500.00"),
        ),
    ]
    suppliers = build_supplier_drilldowns(rows)
    assert len(suppliers) == 1
    supplier = suppliers[0]
    assert supplier.invoice_count == 2
    assert supplier.approved_invoice_count == 1
    assert supplier.mandatory_review_count == 1
    assert supplier.invoice_value == Decimal("1180.00")
    assert supplier.needs_attention
    assert supplier.invoices[0].bucket == "MANDATORY_REVIEW"


def test_v10_fix_first_dashboard_has_three_separate_lanes() -> None:
    rows = [
        row(
            row_id=20,
            supplier_name="ABC Traders",
            gstin="33ABCDE1234F1Z5",
            invoice_no="A-1",
            taxable_value=Decimal("1000.00"),
            cgst=Decimal("90.00"),
            sgst=Decimal("90.00"),
            invoice_value=Decimal("1180.00"),
            include_in_totals=True,
        ),
        row(
            row_id=21,
            supplier_name="XYZ Ltd",
            gstin="33ABCDE1234F1Z5",
            invoice_no="X-1",
            review_required=True,
            audit_severity="HIGH",
            mismatch_reason="UNEXPLAINED_GST_MISMATCH",
            difference_amount=Decimal("3000.00"),
            invoice_value=Decimal("5000.00"),
        ),
    ]
    payload = build_fix_first_dashboard(rows)
    assert set(payload) == {"gst_fix_first", "search_and_view", "invoice_value", "supplier_sidebar"}
    assert payload["gst_fix_first"]["next_action"] == "Review Critical Issues"
    assert payload["search_and_view"]["status_buckets"]["Mandatory Review"] == 1
    assert payload["invoice_value"]["total_invoice_value"] == "1180.00"
