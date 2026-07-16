"""Readable dashboard layer facade.

This module is import-safe in headless test environments. The real PySide6
builder is imported only when build_dashboard_tab is called.
"""

DASHBOARD_MODES = [
    "Overview",
    "Review Focus",
    "Supplier Focus",
    "GSTIN Focus",
    "Tax Mismatch",
    "Monthly Trend",
    "Advanced Custom",
]

MODE_HELP = {
    "Overview": "Best default view: totals, monthly value, suppliers, status and mismatch summary.",
    "Review Focus": "Shows only rows needing decisions and groups them by mismatch reason.",
    "Supplier Focus": "Ranks supplier/company totals and prepares the table for supplier drill-down.",
    "GSTIN Focus": "Groups by GSTIN so you can check supplier tax identity and totals.",
    "Tax Mismatch": "Prioritises GST formula mismatch amount and exception reasons.",
    "Monthly Trend": "Shows month-wise movement with a line chart.",
    "Advanced Custom": "Unlocks all filters and chart settings for expert analysis.",
}


def build_dashboard_tab(window):
    from app.ui.views.dashboard_view import build_dashboard_tab as _build_dashboard_tab

    return _build_dashboard_tab(window)


__all__ = ["DASHBOARD_MODES", "MODE_HELP", "build_dashboard_tab"]


from app.core.executive_dashboard import build_fix_first_dashboard

__all__ += ["build_fix_first_dashboard"]
