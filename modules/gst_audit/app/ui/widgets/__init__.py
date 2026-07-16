"""Lazy widget exports for optional PySide6 environments.

Importing ``app.ui.widgets`` must not require PySide6. Concrete widget classes
are resolved only when requested by the GUI runtime.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORTS = {
    "MetricCard": "app.ui.widgets.metric_card",
    "StatusCard": "app.ui.widgets.status_card",
    "StatusChip": "app.ui.widgets.status_chip",
    "friendly_status": "app.ui.widgets.status_chip",
    "DataTable": "app.ui.widgets.data_table",
    "DataTableModel": "app.ui.widgets.data_table",
    "EmptyState": "app.ui.widgets.empty_state",
    "FilterValueDialog": "app.ui.widgets.guided_search_picker",
    "GuidedSearchPicker": "app.ui.widgets.guided_search_picker",
    "LoadingOverlay": "app.ui.widgets.loading_overlay",
    "RowDetailPanel": "app.ui.widgets.detail_panel",
    "SearchableMultiSelect": "app.ui.widgets.guided_filter",
    "SearchByValueMultiSelect": "app.ui.widgets.guided_filter",
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
