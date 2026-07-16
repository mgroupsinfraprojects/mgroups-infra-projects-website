from __future__ import annotations

from decimal import Decimal

from app.core.analytics import chart_points, filter_rows, grouped_chart_points, supplier_summary
from tests.test_core_audit import make_row, valid_gstin


def test_filter_rows_searches_supplier_gstin_and_invoice():
    row = make_row(1)
    row.supplier_name = "ABC Analytics Traders"
    row.invoice_no = "INV-AN-001"
    rows = [row]
    assert filter_rows(rows, query="analytics") == rows
    assert filter_rows(rows, query="INV-AN") == rows
    assert filter_rows(rows, query=row.gstin[-5:]) == rows


def test_supplier_summary_groups_by_gstin_not_display_name_only():
    row1 = make_row(1, invoice="118.00")
    row1.supplier_name = "ABC Traders Pvt Ltd"
    row1.gstin = valid_gstin("33ABCDE1234F1Z")
    row2 = make_row(2, invoice="236.00")
    row2.supplier_name = "ABC Traders Ltd"
    row2.gstin = valid_gstin("29ABCDE1234F1Z")
    summary = supplier_summary([row1, row2])
    assert len(summary) == 2
    assert sum(metric.invoice_value for metric in summary) == Decimal("354.00")


def test_chart_points_respects_metric_selection():
    row = make_row(1, invoice="118.00")
    points = chart_points([row], "Total GST")
    assert points
    assert points[0][1] == Decimal("18.00")


def test_grouped_chart_points_supports_supplier_grouping_and_metric_selection():
    row1 = make_row(1, invoice="118.00")
    row1.supplier_name = "ABC Traders"
    row2 = make_row(2, invoice="236.00")
    row2.supplier_name = "XYZ Traders"

    points = grouped_chart_points([row1, row2], "Invoice Value", "Supplier", limit=10)

    assert points[0] == ("XYZ Traders", Decimal("236.00"))
    assert points[1] == ("ABC Traders", Decimal("118.00"))


def test_grouped_chart_points_supports_status_and_mismatch_amount():
    row = make_row(1, invoice="125.00", include=False, review=True, status="GST_MISMATCH")
    row.difference_amount = Decimal("7.00")
    row.mismatch_reason = "POSSIBLE_FREIGHT_OR_DISCOUNT"

    status_points = grouped_chart_points([row], "Invoice Count", "Audit Status")
    mismatch_points = grouped_chart_points([row], "Mismatch Amount", "Mismatch Reason")

    assert status_points == [("GST_MISMATCH", Decimal("1"))]
    assert mismatch_points == [("POSSIBLE_FREIGHT_OR_DISCOUNT", Decimal("7.00"))]


def test_filter_rows_respects_selected_search_field():
    row = make_row(1)
    row.supplier_name = "Sree Kumaran Traders"
    row.invoice_no = "INV-2026-009"
    row.gstin = valid_gstin("33FNRPK9375P1Z")
    row.audit_status = "VALID"
    rows = [row]

    assert filter_rows(rows, query="Sree", search_field="Company / Supplier") == rows
    assert filter_rows(rows, query="FNRPK", search_field="GSTIN") == rows
    assert filter_rows(rows, query="INV-2026", search_field="Invoice Number") == rows
    assert filter_rows(rows, query="VALID", search_field="Status / Issue") == rows
    assert filter_rows(rows, query="Sree", search_field="GSTIN") == []
