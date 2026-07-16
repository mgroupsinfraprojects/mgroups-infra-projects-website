from __future__ import annotations

from dataclasses import asdict
from decimal import Decimal
from typing import Iterable, Any

from app.core.models import InvoiceRow
from app.core.review_queue_engine import build_review_queue, summarize_review_queue
from app.core.supplier_intelligence import build_supplier_drilldowns


def _money(value: Decimal) -> str:
    return f"{value:.2f}"


def build_fix_first_dashboard(rows: Iterable[InvoiceRow]) -> dict[str, Any]:
    """Build the V10 decision-first dashboard payload.

    The UI should render this order: GST Fix First -> Search & View -> Invoice Value.
    Charts come after the mandatory queue, not before it.
    """
    row_list = list(rows)
    queue = build_review_queue(row_list, include_non_blocking=True)
    summary = summarize_review_queue(queue)
    suppliers = build_supplier_drilldowns(row_list)

    approved_rows = [row for row in row_list if row.include_in_totals]
    total_taxable = sum((row.taxable_value for row in approved_rows), Decimal("0.00"))
    total_gst = sum((row.igst + row.cgst + row.sgst + row.cess for row in approved_rows), Decimal("0.00"))
    total_invoice = sum((row.invoice_value for row in approved_rows), Decimal("0.00"))

    return {
        "gst_fix_first": {
            "export_blocked": summary.export_blocked,
            "mandatory_review_count": summary.mandatory_count,
            "advisory_review_count": summary.advisory_count,
            "trace_only_count": summary.trace_only_count,
            "blocking_invoice_value": _money(summary.blocking_invoice_value),
            "blocking_difference_value": _money(summary.blocking_difference_value),
            "top_issue_types": list(summary.top_issue_types),
            "next_action": "Review Critical Issues" if summary.export_blocked else "Export Report",
        },
        "search_and_view": {
            "available_filters": [
                "Supplier", "GSTIN", "Invoice Number", "Date", "Amount", "Issue Type", "Status", "Source File"
            ],
            "status_buckets": {
                "Mandatory Review": summary.mandatory_count,
                "Advisory Review": summary.advisory_count,
                "Trace Only": summary.trace_only_count,
                "Approved": summary.approved_count,
                "Matched": summary.matched_count,
            },
        },
        "invoice_value": {
            "approved_invoice_count": len(approved_rows),
            "total_taxable_value": _money(total_taxable),
            "total_gst_value": _money(total_gst),
            "total_invoice_value": _money(total_invoice),
            "top_suppliers": [
                {
                    "supplier_name": supplier.supplier_name,
                    "gstin": supplier.gstin,
                    "invoice_count": supplier.invoice_count,
                    "invoice_value": _money(supplier.invoice_value),
                    "mandatory_review_count": supplier.mandatory_review_count,
                }
                for supplier in suppliers[:10]
            ],
        },
        "supplier_sidebar": [asdict(supplier) | {"invoice_value": _money(supplier.invoice_value)} for supplier in suppliers[:25]],
    }
