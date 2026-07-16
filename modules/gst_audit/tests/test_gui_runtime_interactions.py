from __future__ import annotations

import os

import pytest

PySide6 = pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from app.ui.widgets.data_table import DataTable
from app.ui.widgets.guided_filter import SearchByValueMultiSelect


def test_datatable_model_maps_sorted_view_row_to_source_row(qtbot):
    table = DataTable()
    qtbot.addWidget(table)
    table.set_data(["Supplier", "Status", "Amount"], [["B", "VALID", "2"], ["A", "VALID", "1"]], status_column=1)
    table.model().sort(0, Qt.AscendingOrder)
    assert table.model().data(table.model().index(0, 0), Qt.DisplayRole) == "A"
    assert table.source_row_for_view_row(0) == 1


def test_guided_filter_typing_shows_inline_suggestions(qtbot):
    widget = SearchByValueMultiSelect()
    qtbot.addWidget(widget)
    widget.set_field_options("company", {"RR ROOFING": 3, "ABC TRADERS": 1, "RRM SUPPLIERS": 2})
    widget.search_edit.setFocus()
    qtbot.keyClicks(widget.search_edit, "RR")
    qtbot.waitUntil(lambda: widget._inline_popup.isVisible(), timeout=1000)
    assert widget._inline_popup.list_widget.count() >= 1
