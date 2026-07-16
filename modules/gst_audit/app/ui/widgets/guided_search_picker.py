from __future__ import annotations

from difflib import SequenceMatcher
from typing import Iterable

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


FIELD_DEFS: list[tuple[str, str, str, str]] = [
    ("company", "Company", "Choose company names...", "Type part of the company name or wrong spelling..."),
    ("gstin", "GST No", "Choose GST numbers...", "Type GSTIN fully or partially..."),
    ("invoice", "Invoice No", "Choose invoice numbers...", "Type invoice number fully or partially..."),
    ("month", "Month", "Choose months...", "Type month like Jan, Feb, 2026, Unknown..."),
]


class FilterValueDialog(QDialog):
    def __init__(self, title: str, placeholder: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(380, 420)
        self._options: list[str] = []
        self._option_counts: dict[str, int] = {}
        self._selected: set[str] = set()
        self._visible_values: list[str] = []
        self._updating = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(placeholder)
        self.search_edit.textChanged.connect(self._refresh_visible_items)
        layout.addWidget(self.search_edit)

        self.select_all_box = QCheckBox("Select visible")
        self.select_all_box.toggled.connect(self._toggle_select_visible)
        layout.addWidget(self.select_all_box)

        self.list_widget = QListWidget()
        self.list_widget.itemChanged.connect(self._item_changed)
        layout.addWidget(self.list_widget, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @staticmethod
    def _clean(value: object) -> str:
        return " ".join(str(value or "").strip().split())

    @staticmethod
    def _sort_key(value: str) -> tuple[int, str]:
        return (1 if value == "Unknown" else 0, value.casefold())

    @staticmethod
    def _score(query: str, option: str) -> float:
        query_norm = " ".join(query.casefold().split())
        option_norm = " ".join(option.casefold().split())
        if not query_norm:
            return 1.0
        if query_norm in option_norm:
            return 100.0 - min(option_norm.index(query_norm), 60) / 10
        tokens = [token for token in query_norm.split() if token]
        if tokens and all(token in option_norm for token in tokens):
            return 88.0
        initials = "".join(part[:1] for part in option_norm.split() if part)
        flattened = query_norm.replace(" ", "")
        if flattened and flattened in initials:
            return 82.0
        return SequenceMatcher(None, query_norm, option_norm).ratio() * 80.0

    def set_options(self, values: Iterable[object] | dict[object, int]) -> None:
        if isinstance(values, dict):
            counts = {self._clean(key): int(count) for key, count in values.items() if self._clean(key)}
            options = sorted(counts, key=self._sort_key)
        else:
            counts = {}
            for raw in values:
                value = self._clean(raw)
                if value:
                    counts[value] = counts.get(value, 0) + 1
            options = sorted(counts, key=self._sort_key)
        self._options = options
        self._option_counts = counts
        self._selected = {value for value in self._selected if value in set(self._options)}
        self._refresh_visible_items()

    def set_selected_values(self, values: Iterable[object]) -> None:
        valid = set(self._options)
        self._selected = {self._clean(value) for value in values if self._clean(value) in valid}
        self._refresh_visible_items()

    def selected_values(self) -> list[str]:
        return [value for value in self._options if value in self._selected]

    def _ranked_options(self) -> list[str]:
        query = self.search_edit.text().strip()
        if not query:
            selected = [value for value in self._options if value in self._selected]
            unselected = [value for value in self._options if value not in self._selected]
            return selected + unselected
        ranked: list[tuple[float, str]] = []
        for option in self._options:
            score = self._score(query, option)
            if score >= 32.0:
                ranked.append((score, option))
        ranked.sort(key=lambda item: (-item[0], self._sort_key(item[1])))
        return [option for _score, option in ranked]

    def _refresh_visible_items(self) -> None:
        self._updating = True
        try:
            self.list_widget.clear()
            self._visible_values = self._ranked_options()
            for value in self._visible_values:
                count = self._option_counts.get(value, 0)
                label = f"{value}"
                if count:
                    label += f"  ·  {count} row{'s' if count != 1 else ''}"
                item = QListWidgetItem(label)
                item.setData(Qt.ItemDataRole.UserRole, value)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                item.setCheckState(Qt.CheckState.Checked if value in self._selected else Qt.CheckState.Unchecked)
                self.list_widget.addItem(item)
            if not self._visible_values:
                item = QListWidgetItem("No matching values")
                item.setFlags(Qt.ItemFlag.NoItemFlags)
                self.list_widget.addItem(item)
        finally:
            self._updating = False
        self._sync_select_all_box()

    def _item_changed(self, item: QListWidgetItem) -> None:
        if self._updating:
            return
        value = item.data(Qt.ItemDataRole.UserRole)
        if not value:
            return
        if item.checkState() == Qt.CheckState.Checked:
            self._selected.add(str(value))
        else:
            self._selected.discard(str(value))
        self._sync_select_all_box()

    def _toggle_select_visible(self, checked: bool) -> None:
        if self._updating:
            return
        if not self._visible_values:
            return
        self._updating = True
        try:
            for i in range(self.list_widget.count()):
                item = self.list_widget.item(i)
                value = item.data(Qt.ItemDataRole.UserRole)
                if not value:
                    continue
                item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
                if checked:
                    self._selected.add(str(value))
                else:
                    self._selected.discard(str(value))
        finally:
            self._updating = False
        self._sync_select_all_box()

    def _sync_select_all_box(self) -> None:
        self.select_all_box.blockSignals(True)
        try:
            if not self._visible_values:
                self.select_all_box.setChecked(False)
                self.select_all_box.setEnabled(False)
            else:
                self.select_all_box.setEnabled(True)
                all_selected = all(value in self._selected for value in self._visible_values)
                self.select_all_box.setChecked(all_selected)
        finally:
            self.select_all_box.blockSignals(False)


class GuidedSearchPicker(QFrame):
    selection_changed = Signal()
    field_changed = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("GuidedSearchPicker")
        self._fields = {key: {"title": title, "display": display, "placeholder": placeholder} for key, title, display, placeholder in FIELD_DEFS}
        self._field_options: dict[str, dict[str, int]] = {key: {} for key in self._fields}
        self._field_selected: dict[str, set[str]] = {key: set() for key in self._fields}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        form = QGridLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(6)

        search_by_label = QLabel("Search by")
        search_by_label.setObjectName("TinyLabel")
        form.addWidget(search_by_label, 0, 0)

        enter_value_label = QLabel("Enter value")
        enter_value_label.setObjectName("TinyLabel")
        form.addWidget(enter_value_label, 0, 1)

        self.field_combo = QComboBox()
        for key, title, _display, _placeholder in FIELD_DEFS:
            self.field_combo.addItem(title, key)
        self.field_combo.currentIndexChanged.connect(self._field_changed)
        form.addWidget(self.field_combo, 1, 0)

        value_row = QWidget()
        value_row_layout = QHBoxLayout(value_row)
        value_row_layout.setContentsMargins(0, 0, 0, 0)
        value_row_layout.setSpacing(8)
        self.value_display = QLineEdit()
        self.value_display.setReadOnly(True)
        self.value_display.setPlaceholderText("Choose values...")
        self.value_display.setMinimumHeight(38)
        self.open_btn = QPushButton("Filter options")
        self.open_btn.setMinimumHeight(38)
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setMinimumHeight(38)
        self.open_btn.clicked.connect(self.open_picker)
        self.clear_btn.clicked.connect(self.clear_current_field)
        value_row_layout.addWidget(self.value_display, 1)
        value_row_layout.addWidget(self.open_btn)
        value_row_layout.addWidget(self.clear_btn)
        form.addWidget(value_row, 1, 1)
        form.setColumnStretch(1, 1)

        layout.addLayout(form)

        self.hint_label = QLabel()
        self.hint_label.setObjectName("SearchGuideText")
        self.hint_label.setWordWrap(True)
        layout.addWidget(self.hint_label)

        self.summary_label = QLabel("No guided values selected")
        self.summary_label.setObjectName("ActiveFilterChips")
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)

        self._field_changed()

    def current_field_key(self) -> str:
        return str(self.field_combo.currentData() or "company")

    def current_field_title(self) -> str:
        key = self.current_field_key()
        return str(self._fields.get(key, {}).get("title", "Value"))

    def set_current_field(self, field_key: str) -> None:
        for index in range(self.field_combo.count()):
            if self.field_combo.itemData(index) == field_key:
                self.field_combo.setCurrentIndex(index)
                return

    def set_field_options(self, field_key: str, values: Iterable[object] | dict[object, int]) -> None:
        if isinstance(values, dict):
            clean = {self._clean(key): int(count) for key, count in values.items() if self._clean(key)}
        else:
            clean = {}
            for raw in values:
                value = self._clean(raw)
                if value:
                    clean[value] = clean.get(value, 0) + 1
        self._field_options[field_key] = clean
        self._field_selected[field_key] = {value for value in self._field_selected.get(field_key, set()) if value in set(clean)}
        self._refresh_display()

    def selected_values_for(self, field_key: str) -> list[str]:
        counts = self._field_options.get(field_key, {})
        selected = self._field_selected.get(field_key, set())
        options = sorted(counts, key=FilterValueDialog._sort_key)
        return [value for value in options if value in selected]

    def set_selected_values(self, field_key: str, values: Iterable[object]) -> None:
        valid = set(self._field_options.get(field_key, {}))
        self._field_selected[field_key] = {self._clean(value) for value in values if self._clean(value) in valid}
        self._refresh_display()

    def clear_selection(self, field_key: str | None = None) -> None:
        if field_key is None:
            for key in self._field_selected:
                self._field_selected[key].clear()
        else:
            self._field_selected.setdefault(field_key, set()).clear()
        self._refresh_display()
        self.selection_changed.emit()

    def clear_current_field(self) -> None:
        self.clear_selection(self.current_field_key())

    def open_picker(self) -> None:
        field_key = self.current_field_key()
        field_info = self._fields[field_key]
        dialog = FilterValueDialog(f"Select {field_info['title']}", field_info["placeholder"], self)
        dialog.set_options(self._field_options.get(field_key, {}))
        dialog.set_selected_values(self.selected_values_for(field_key))
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._field_selected[field_key] = set(dialog.selected_values())
            self._refresh_display()
            self.selection_changed.emit()

    def active_summary_text(self) -> str:
        parts = []
        for key, info in self._fields.items():
            selected = self.selected_values_for(key)
            if selected:
                preview = ", ".join(selected[:2])
                if len(preview) > 56:
                    preview = preview[:53] + "…"
                if len(selected) > 2:
                    preview += f" +{len(selected) - 2} more"
                parts.append(f"{info['title']}: {preview}")
        return " | ".join(parts) if parts else "No guided values selected"

    def _field_changed(self) -> None:
        self._refresh_display()
        self.field_changed.emit(self.current_field_key())

    def _refresh_display(self) -> None:
        field_key = self.current_field_key()
        info = self._fields[field_key]
        selected = self.selected_values_for(field_key)
        total = len(self._field_options.get(field_key, {}))
        self.value_display.setPlaceholderText(info["display"])
        self.value_display.setToolTip(info["placeholder"])
        self.open_btn.setText(f"Choose {info['title']}")
        self.hint_label.setText(
            f"Pick {info['title'].lower()} values from the uploaded data. You can search inside the list, use partial text, and select multiple values."
        )
        if not selected:
            self.value_display.clear()
            self.value_display.setPlaceholderText(f"{info['display']} ({total} available)")
        else:
            preview = ", ".join(selected[:3])
            if len(preview) > 72:
                preview = preview[:69] + "…"
            if len(selected) > 3:
                preview += f" +{len(selected) - 3} more"
            self.value_display.setText(preview)
        self.summary_label.setText(self.active_summary_text())

    @staticmethod
    def _clean(value: object) -> str:
        return " ".join(str(value or "").strip().split())
