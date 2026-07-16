"""Logical frontend views boundary.

The production UI uses builder functions under :mod:`app.ui.views`.  This module
is intentionally lazy so importing the logical architecture facade does not
require PySide6 on headless test/release machines.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORTS = {
    "build_audit_tab": "app.ui.views.audit_view",
    "build_dashboard_tab": "app.ui.views.dashboard_view",
    "build_export_tab": "app.ui.views.export_view",
    "build_reconciliation_tab": "app.ui.views.reconciliation_view",
    "build_settings_tab": "app.ui.views.settings_view",
    "build_supplier_tab": "app.ui.views.supplier_view",
    "build_upload_tab": "app.ui.views.upload_view",
}

__all__ = list(_EXPORTS)


def __getattr__(name: str) -> Any:
    module_name = _EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(name)
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value
