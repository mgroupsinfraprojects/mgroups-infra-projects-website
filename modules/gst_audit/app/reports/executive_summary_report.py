from __future__ import annotations

from typing import Any


def build_executive_summary_report(dashboard: dict[str, Any]) -> str:
    fix = dashboard.get("gst_fix_first", {})
    value = dashboard.get("invoice_value", {})
    lines = [
        "GST AUDIT EXECUTIVE SUMMARY",
        f"Export blocked: {fix.get('export_blocked')}",
        f"Mandatory review count: {fix.get('mandatory_review_count', 0)}",
        f"Advisory review count: {fix.get('advisory_review_count', 0)}",
        f"Approved invoice count: {value.get('approved_invoice_count', 0)}",
        f"Total invoice value: {value.get('total_invoice_value', '0.00')}",
    ]
    return "\n".join(lines) + "\n"
