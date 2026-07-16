"""Logical frontend widgets boundary.

The concrete PySide6 widgets remain under :mod:`app.ui.widgets`.  This facade is
lazy so source-package checks can import it without requiring a GUI runtime.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORTS = {
    "DataTable": "app.ui.widgets.data_table",
    "DataTableModel": "app.ui.widgets.data_table",
    "EmptyState": "app.ui.widgets.empty_state",
    "FilterValueDialog": "app.ui.widgets.guided_search_picker",
    "GuidedSearchPicker": "app.ui.widgets.guided_search_picker",
    "LoadingOverlay": "app.ui.widgets.loading_overlay",
    "MetricCard": "app.ui.widgets.metric_card",
    "RowDetailPanel": "app.ui.widgets.detail_panel",
    "SearchableMultiSelect": "app.ui.widgets.guided_filter",
    "SearchByValueMultiSelect": "app.ui.widgets.guided_filter",
    "StatusCard": "app.ui.widgets.status_card",
    "StatusChip": "app.ui.widgets.status_chip",
    "Toast": "app.ui.widgets.toast",
    "UploadCard": "app.ui.widgets.upload_card",
}

__all__ = list(_EXPORTS)


def __getattr__(name: str) -> Any:
    module_name = _EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(name)
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value
