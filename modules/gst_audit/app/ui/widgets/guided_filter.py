from __future__ import annotations

from difflib import SequenceMatcher
from typing import Iterable

from PySide6.QtCore import QEvent, QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.ui.widgets.modern_combo import ModernComboButton


class _SearchableFilterBase(QFrame):
    """Shared fuzzy-search helpers for dashboard guided filters."""

    selection_changed = Signal()

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
        compact_query = query_norm.replace(" ", "")
        if compact_query and compact_query in initials:
            return 82.0
        return SequenceMatcher(None, query_norm, option_norm).ratio() * 80.0


class SearchableMultiSelect(_SearchableFilterBase):
    """Legacy inline searchable multi-select control for non-exact audit filtering."""

    def __init__(self, title: str, placeholder: str, *, max_visible_items: int = 8, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("GuidedSelectCard")
        self._options: list[str] = []
        self._option_counts: dict[str, int] = {}
        self._selected: set[str] = set()
        self._visible_values: list[str] = []
        self._max_visible_items = max_visible_items
        self._updating = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 9, 10, 10)
        layout.setSpacing(7)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("GuidedSelectTitle")
        self.count_label = QLabel("All")
        self.count_label.setObjectName("GuidedSelectCount")
        header.addWidget(self.title_label)
        header.addStretch(1)
        header.addWidget(self.count_label)
        layout.addLayout(header)

        self.search_edit = QLineEdit()
        self.search_edit.setObjectName("GuidedSearchInput")
        self.search_edit.setPlaceholderText(placeholder)
        self.search_edit.textChanged.connect(self._refresh_visible_items)
        layout.addWidget(self.search_edit)

        self.list_widget = QListWidget()
        self.list_widget.setObjectName("GuidedSuggestionList")
        self.list_widget.setMinimumHeight(128)
        self.list_widget.setMaximumHeight(148)
        self.list_widget.itemChanged.connect(self._item_changed)
        layout.addWidget(self.list_widget)

        action_row = QHBoxLayout()
        action_row.setContentsMargins(0, 0, 0, 0)
        action_row.setSpacing(6)
        self.select_visible_btn = QPushButton("Select visible")
        self.select_visible_btn.setObjectName("MiniActionButton")
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setObjectName("MiniActionButton")
        self.select_visible_btn.clicked.connect(self.select_visible)
        self.clear_btn.clicked.connect(self.clear_selection)
        action_row.addWidget(self.select_visible_btn)
        action_row.addWidget(self.clear_btn)
        action_row.addStretch(1)
        layout.addLayout(action_row)

        self.chip_container = QWidget()
        self.chip_container.setObjectName("SelectedChipContainer")
        self.chip_layout = QHBoxLayout(self.chip_container)
        self.chip_layout.setContentsMargins(0, 0, 0, 0)
        self.chip_layout.setSpacing(5)
        layout.addWidget(self.chip_container)
        self._refresh_chips()

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
        valid = set(self._options)
        self._selected = {value for value in self._selected if value in valid}
        self._refresh_visible_items()
        self._refresh_chips()

    def selected_values(self) -> list[str]:
        return [value for value in self._options if value in self._selected]

    def set_selected_values(self, values: Iterable[object]) -> None:
        valid = set(self._options)
        self._selected = {self._clean(value) for value in values if self._clean(value) in valid}
        self._refresh_visible_items()
        self._refresh_chips()
        self.selection_changed.emit()

    def clear_selection(self) -> None:
        if not self._selected and not self.search_edit.text():
            return
        self._selected.clear()
        self.search_edit.clear()
        self._refresh_visible_items()
        self._refresh_chips()
        self.selection_changed.emit()

    def select_visible(self) -> None:
        if not self._visible_values:
            return
        before = set(self._selected)
        self._selected.update(self._visible_values)
        self._refresh_visible_items()
        self._refresh_chips()
        if self._selected != before:
            self.selection_changed.emit()

    def _ranked_options(self) -> list[str]:
        query = self.search_edit.text().strip()
        if not query:
            selected = [value for value in self._options if value in self._selected]
            unselected = [value for value in self._options if value not in self._selected]
            return selected + unselected[: self._max_visible_items]
        ranked: list[tuple[float, str]] = []
        for option in self._options:
            score = self._score(query, option)
            if score >= 32.0:
                ranked.append((score, option))
        ranked.sort(key=lambda item: (-item[0], self._sort_key(item[1])))
        return [option for _score, option in ranked[: self._max_visible_items]]

    def _refresh_visible_items(self) -> None:
        self._updating = True
        try:
            self.list_widget.clear()
            self._visible_values = self._ranked_options()
            for value in self._visible_values:
                count = self._option_counts.get(value, 0)
                label = f"{value}  ·  {count} row{'s' if count != 1 else ''}" if count else value
                item = QListWidgetItem(label)
                item.setData(Qt.ItemDataRole.UserRole, value)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                item.setCheckState(Qt.CheckState.Checked if value in self._selected else Qt.CheckState.Unchecked)
                self.list_widget.addItem(item)
            if not self._visible_values:
                item = QListWidgetItem("No matching values from uploaded data")
                item.setFlags(Qt.ItemFlag.NoItemFlags)
                self.list_widget.addItem(item)
        finally:
            self._updating = False
        self._refresh_count_label()

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
        self._refresh_chips()
        self._refresh_count_label()
        self.selection_changed.emit()

    def _refresh_count_label(self) -> None:
        selected_count = len(self._selected)
        total = len(self._options)
        self.count_label.setText(f"{selected_count} selected" if selected_count else f"All {total}")

    def _clear_chip_layout(self) -> None:
        while self.chip_layout.count():
            item = self.chip_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _remove_selected_value(self, value: str) -> None:
        if value in self._selected:
            self._selected.remove(value)
            self._refresh_visible_items()
            self._refresh_chips()
            self.selection_changed.emit()

    def _refresh_chips(self) -> None:
        self._clear_chip_layout()
        selected = self.selected_values()
        if not selected:
            label = QLabel("All values allowed")
            label.setObjectName("EmptyChipHint")
            self.chip_layout.addWidget(label)
            self.chip_layout.addStretch(1)
            return
        for value in selected[:3]:
            text = value if len(value) <= 24 else value[:21] + "…"
            chip = QPushButton(f"{text}  ×")
            chip.setObjectName("SelectedFilterChip")
            chip.setToolTip(f"Remove {value}")
            chip.clicked.connect(lambda _checked=False, v=value: self._remove_selected_value(v))
            self.chip_layout.addWidget(chip)
        if len(selected) > 3:
            more = QLabel(f"+{len(selected) - 3} more")
            more.setObjectName("EmptyChipHint")
            self.chip_layout.addWidget(more)
        self.chip_layout.addStretch(1)


class _FilterOptionRow(QFrame):
    toggled = Signal(str, bool)

    def __init__(self, value: str, count: int, checked: bool = False, parent=None) -> None:
        super().__init__(parent)
        self.value = value
        self.count = count
        self.setObjectName("FilterOptionRow")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFixedHeight(38)
        self.setProperty("focused", False)
        self.setToolTip(value)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 5, 12, 5)
        layout.setSpacing(9)

        self.checkbox = QCheckBox()
        self.checkbox.setObjectName("FilterOptionCheckbox")
        self.checkbox.setChecked(checked)
        self.checkbox.toggled.connect(self._emit_toggled)
        layout.addWidget(self.checkbox)

        self.name_label = QLabel(value)
        self.name_label.setObjectName("FilterOptionName")
        self.name_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.name_label.setToolTip(value)
        self.name_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(self.name_label, 1)

        self.count_label = QLabel(f"{count} row{'s' if count != 1 else ''}")
        self.count_label.setObjectName("FilterOptionCount")
        self.count_label.setMinimumWidth(74)
        self.count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.count_label, 0, Qt.AlignmentFlag.AlignRight)

        self._apply_state()

    def set_focused_row(self, focused: bool) -> None:
        self.setProperty("focused", focused)
        self.style().unpolish(self)
        self.style().polish(self)

    def _emit_toggled(self, checked: bool) -> None:
        self._apply_state()
        self.toggled.emit(self.value, checked)

    def _apply_state(self) -> None:
        self.setProperty("checked", self.checkbox.isChecked())
        self.style().unpolish(self)
        self.style().polish(self)

    def set_checked(self, checked: bool) -> None:
        self.checkbox.blockSignals(True)
        self.checkbox.setChecked(checked)
        self.checkbox.blockSignals(False)
        self._apply_state()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.checkbox.setChecked(not self.checkbox.isChecked())
        super().mousePressEvent(event)


class _FloatingValuePicker(QDialog, _SearchableFilterBase):
    """Premium dropdown-like checklist used by SearchByValueMultiSelect.

    v8.7 rule: this popup must be a bounded dropdown, not a full-width overlay.
    The scroll list reserves a fixed footer area so option rows cannot be clipped
    behind the Clear/Apply buttons.
    """

    applied = Signal()
    query_changed = Signal(str)

    MIN_WIDTH = 560
    MAX_WIDTH = 720
    POPUP_HEIGHT = 430
    SEARCH_HEIGHT = 42
    ACTION_ROW_HEIGHT = 38
    FOOTER_HEIGHT = 56
    SCROLL_MAX_HEIGHT = 246

    def __init__(self, placeholder: str, field_label: str = "value", parent=None) -> None:
        QDialog.__init__(self, parent)
        self.field_label = field_label
        self.setObjectName("FilterPopupPanel")
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setModal(True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAutoFillBackground(True)
        # Defensive background styling prevents native/transparent viewport paint
        # artifacts that previously appeared as black blocks in the popup list.
        self.setStyleSheet("QDialog#FilterPopupPanel { background: #ffffff; border: 1px solid #BBD0F6; border-radius: 16px; }")
        self.setMinimumWidth(self.MIN_WIDTH)
        self.setMaximumWidth(self.MAX_WIDTH)
        self.setFixedHeight(self.POPUP_HEIGHT)

        self._options: list[str] = []
        self._counts: dict[str, int] = {}
        self._selected: set[str] = set()
        self._visible_values: list[str] = []
        self._row_widgets: list[_FilterOptionRow] = []
        self._focused_index = -1
        self._current_query = ""
        self._updating = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        self.search_edit = QLineEdit()
        self.search_edit.setObjectName("FilterPopupSearch")
        self.search_edit.setPlaceholderText(f"Type to filter {field_label.lower()} values")
        self.search_edit.setToolTip(placeholder)
        self.search_edit.setFixedHeight(self.SEARCH_HEIGHT)
        self.search_edit.textChanged.connect(self._refresh_visible_items)
        self.search_edit.textEdited.connect(self.query_changed.emit)
        layout.addWidget(self.search_edit)

        self.select_visible_row = QFrame()
        self.select_visible_row.setObjectName("FilterPopupActionRow")
        self.select_visible_row.setFixedHeight(self.ACTION_ROW_HEIGHT)
        select_row_layout = QHBoxLayout(self.select_visible_row)
        select_row_layout.setContentsMargins(12, 5, 12, 5)
        select_row_layout.setSpacing(10)
        self.select_visible_box = QCheckBox()
        self.select_visible_box.setObjectName("FilterOptionCheckbox")
        self.select_visible_box.toggled.connect(self._toggle_visible)
        select_row_layout.addWidget(self.select_visible_box)
        select_label = QLabel("Select all visible")
        select_label.setObjectName("FilterOptionName")
        select_row_layout.addWidget(select_label, 1)
        self.visible_hint = QLabel("")
        self.visible_hint.setObjectName("FilterPopupCount")
        select_row_layout.addWidget(self.visible_hint)
        layout.addWidget(self.select_visible_row)

        self.scroll = QScrollArea()
        self.scroll.setObjectName("FilterPopupScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setAutoFillBackground(True)
        self.scroll.setMaximumHeight(self.SCROLL_MAX_HEIGHT)
        self.scroll.setMinimumHeight(self.SCROLL_MAX_HEIGHT)
        self.scroll.viewport().setAutoFillBackground(True)
        self.scroll.viewport().setStyleSheet("background: #ffffff; border: 0px;")
        self.scroll_content = QWidget()
        self.scroll_content.setObjectName("FilterPopupScrollContent")
        self.scroll_content.setAutoFillBackground(True)
        self.scroll_content.setStyleSheet("QWidget#FilterPopupScrollContent { background: #ffffff; }")
        self.rows_layout = QVBoxLayout(self.scroll_content)
        self.rows_layout.setContentsMargins(0, 0, 0, 0)
        self.rows_layout.setSpacing(4)
        self.rows_layout.addStretch(1)
        self.scroll.setWidget(self.scroll_content)
        layout.addWidget(self.scroll, 1)

        self.footer_frame = QFrame()
        self.footer_frame.setObjectName("FilterPopupFooter")
        self.footer_frame.setFixedHeight(self.FOOTER_HEIGHT)
        footer = QHBoxLayout(self.footer_frame)
        footer.setContentsMargins(4, 8, 4, 4)
        footer.setSpacing(8)
        self.status_label = QLabel("0 selected")
        self.status_label.setObjectName("FilterPopupStatus")
        footer.addWidget(self.status_label)
        footer.addStretch(1)
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setObjectName("FilterPopupGhostButton")
        self.clear_btn.clicked.connect(self._clear_visible)
        self.apply_btn = QPushButton("Apply")
        self.apply_btn.setObjectName("FilterPopupApplyButton")
        self.apply_btn.clicked.connect(self.accept)
        footer.addWidget(self.clear_btn)
        footer.addWidget(self.apply_btn)
        layout.addWidget(self.footer_frame)

    def set_data(self, options: list[str], counts: dict[str, int], selected: set[str], query: str = "") -> None:
        self._options = list(options)
        self._counts = dict(counts)
        self._selected = set(value for value in selected if value in set(options))
        self._current_query = query
        self.search_edit.setText(query)
        self._refresh_visible_items()
        self.search_edit.selectAll()
        self.search_edit.setFocus()

    def selected_values(self) -> list[str]:
        return [value for value in self._options if value in self._selected]

    def current_query(self) -> str:
        return self.search_edit.text().strip()

    def _scored_options(self) -> list[tuple[str, float]]:
        query = self.search_edit.text().strip()
        if not query:
            selected_first = [(value, 100.0) for value in self._options if value in self._selected]
            unselected = [(value, 1.0) for value in self._options if value not in self._selected]
            return selected_first + unselected
        ranked: list[tuple[float, str]] = []
        for option in self._options:
            score = self._score(query, option)
            if score >= 32.0 or option in self._selected:
                ranked.append((score, option))
        ranked.sort(key=lambda item: (-item[0], self._sort_key(item[1])))
        return [(option, score) for score, option in ranked]

    def _grouped_visible_options(self) -> list[tuple[str, list[str]]]:
        query = self.search_edit.text().strip()
        scored = self._scored_options()
        selected_visible = [value for value, _score in scored if value in self._selected]
        unselected_scored = [(value, score) for value, score in scored if value not in self._selected]
        groups: list[tuple[str, list[str]]] = []
        if selected_visible:
            groups.append(("Selected", selected_visible))
        if query:
            best = [value for value, score in unselected_scored if score >= 82.0]
            suggested = [value for value, score in unselected_scored if 32.0 <= score < 82.0]
            if best:
                groups.append(("Best matches", best))
            if suggested:
                groups.append(("Suggested matches", suggested))
        else:
            remaining = [value for value, _score in unselected_scored]
            if remaining:
                groups.append((f"All {self.field_label.lower()} values", remaining))
        return groups

    def _ranked_options(self) -> list[str]:
        return [value for group in self._grouped_visible_options() for value in group[1]]

    def _clear_rows(self) -> None:
        self._row_widgets = []
        self._focused_index = -1
        while self.rows_layout.count() > 1:
            item = self.rows_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _insert_group_label(self, text: str) -> None:
        label = QLabel(text)
        label.setObjectName("FilterPopupGroupLabel")
        self.rows_layout.insertWidget(self.rows_layout.count() - 1, label)

    def _refresh_visible_items(self) -> None:
        groups = self._grouped_visible_options()
        self._visible_values = [value for _label, values in groups for value in values]
        self._clear_rows()
        self._updating = True
        try:
            if not self._visible_values:
                query = self.search_edit.text().strip()
                message = (
                    f'No {self.field_label.lower()} found for "{query}"\n\n'
                    f"Try checking the spelling, searching another field, or clearing this filter."
                    if query else f"No {self.field_label.lower()} values found in uploaded data."
                )
                empty = QLabel(message)
                empty.setObjectName("FilterPopupEmpty")
                empty.setWordWrap(True)
                self.rows_layout.insertWidget(0, empty)
            else:
                for group_label, values in groups:
                    self._insert_group_label(group_label)
                    for value in values:
                        row = _FilterOptionRow(value, self._counts.get(value, 0), value in self._selected)
                        row.setAutoFillBackground(True)
                        row.toggled.connect(self._row_toggled)
                        self._row_widgets.append(row)
                        self.rows_layout.insertWidget(self.rows_layout.count() - 1, row)
                self._set_focused_index(0)
        finally:
            self._updating = False
        self._sync_header_and_status()

    def _row_toggled(self, value: str, checked: bool) -> None:
        if checked:
            self._selected.add(value)
        else:
            self._selected.discard(value)
        self._sync_header_and_status()

    def _clear_visible(self) -> None:
        if self._visible_values:
            for value in list(self._visible_values):
                self._selected.discard(value)
            self._refresh_visible_items()
        else:
            self._selected.clear()
            self._refresh_visible_items()

    def _toggle_visible(self, checked: bool) -> None:
        if self._updating:
            return
        if checked:
            self._selected.update(self._visible_values)
        else:
            for value in self._visible_values:
                self._selected.discard(value)
        self._refresh_visible_items()

    def _sync_header_and_status(self) -> None:
        self.select_visible_box.blockSignals(True)
        try:
            enabled = bool(self._visible_values)
            self.select_visible_box.setEnabled(enabled)
            self.select_visible_box.setChecked(enabled and all(value in self._selected for value in self._visible_values))
        finally:
            self.select_visible_box.blockSignals(False)
        total = len(self._options)
        shown = len(self._visible_values)
        label = self.field_label.lower()
        if self.search_edit.text().strip():
            self.visible_hint.setText(f"{shown} matches from {total}")
        else:
            self.visible_hint.setText(f"{total} {label}s" if not label.endswith("s") else f"{total} {label}")
        count = len(self._selected)
        self.status_label.setText(f"{count} selected" if count else "No values selected")

    def _set_focused_index(self, index: int) -> None:
        if not self._row_widgets:
            self._focused_index = -1
            return
        index = max(0, min(index, len(self._row_widgets) - 1))
        for row_index, row in enumerate(self._row_widgets):
            row.set_focused_row(row_index == index)
        self._focused_index = index
        self._row_widgets[index].setFocus()

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
            return
        if event.key() in {Qt.Key.Key_Return, Qt.Key.Key_Enter}:
            self.accept()
            return
        if event.key() == Qt.Key.Key_Down:
            self._set_focused_index(self._focused_index + 1 if self._focused_index >= 0 else 0)
            return
        if event.key() == Qt.Key.Key_Up:
            self._set_focused_index(self._focused_index - 1 if self._focused_index >= 0 else 0)
            return
        if event.key() == Qt.Key.Key_Space and 0 <= self._focused_index < len(self._row_widgets):
            row = self._row_widgets[self._focused_index]
            row.checkbox.setChecked(not row.checkbox.isChecked())
            return
        if event.key() == Qt.Key.Key_A and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self._selected.update(self._visible_values)
            self._refresh_visible_items()
            return
        super().keyPressEvent(event)


class _InlineSuggestionPopup(QFrame):
    """Small non-modal suggestion popup shown while typing in the Enter value box."""

    picked = Signal(str)
    request_full_list = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setObjectName("InlineSuggestionPopup")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAutoFillBackground(True)
        self.setStyleSheet("QFrame#InlineSuggestionPopup { background: #ffffff; }")
        self._values: list[str] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        self.list_widget = QListWidget()
        self.list_widget.setObjectName("InlineSuggestionList")
        self.list_widget.setFrameShape(QFrame.Shape.NoFrame)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list_widget.itemClicked.connect(self._pick_item)
        self.list_widget.itemActivated.connect(self._pick_item)
        layout.addWidget(self.list_widget)

        self.full_list_btn = QPushButton("Open full selectable list")
        self.full_list_btn.setObjectName("SuggestionOpenFullButton")
        self.full_list_btn.clicked.connect(self._open_full_list)
        layout.addWidget(self.full_list_btn)

    def set_items(self, items: list[tuple[str, int]], field_label: str) -> None:
        self.list_widget.clear()
        self._values = [value for value, _count in items]
        if not items:
            empty = QListWidgetItem(f"No matching {field_label.lower()} values")
            empty.setFlags(Qt.ItemFlag.NoItemFlags)
            self.list_widget.addItem(empty)
        else:
            for value, count in items:
                suffix = f"  ·  {count} row{'s' if count != 1 else ''}" if count else ""
                item = QListWidgetItem(f"{value}{suffix}")
                item.setData(Qt.ItemDataRole.UserRole, value)
                self.list_widget.addItem(item)
        row_count = max(1, min(len(items), 7))
        self.list_widget.setMinimumHeight(row_count * 36)
        self.list_widget.setMaximumHeight(row_count * 42 + 6)

    def show_below(self, anchor: QWidget, width: int) -> None:
        self.resize(max(360, width), min(360, self.sizeHint().height()))
        pos = anchor.mapToGlobal(anchor.rect().bottomLeft())
        self.move(pos.x(), pos.y() + 4)
        self.show()
        anchor.setFocus()

    def first_value(self) -> str:
        return self._values[0] if self._values else ""

    def focus_first(self) -> None:
        if self._values:
            self.list_widget.setCurrentRow(0)
            self.list_widget.setFocus()

    def _pick_item(self, item: QListWidgetItem) -> None:
        value = item.data(Qt.ItemDataRole.UserRole)
        if value:
            self.picked.emit(str(value))
            self.close()

    def _open_full_list(self) -> None:
        self.request_full_list.emit()
        self.close()


class SearchByValueMultiSelect(_SearchableFilterBase):
    """Single guided selector with a unified Enter value input and frameless multi-select popup."""

    FIELD_SPECS = [
        ("company", "Company", "Search or select company..."),
        ("gstin", "GST No", "Search or select GST number..."),
        ("invoice", "Invoice No", "Search or select invoice number..."),
        ("month", "Month", "Search or select month..."),
    ]

    def __init__(self, *, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("CompactSearchSelector")
        self._field_labels = {key: label for key, label, _ in self.FIELD_SPECS}
        self._field_placeholders = {key: placeholder for key, _label, placeholder in self.FIELD_SPECS}
        self._options_by_field: dict[str, list[str]] = {key: [] for key, *_rest in self.FIELD_SPECS}
        self._counts_by_field: dict[str, dict[str, int]] = {key: {} for key, *_rest in self.FIELD_SPECS}
        self._selected_by_field: dict[str, set[str]] = {key: set() for key, *_rest in self.FIELD_SPECS}
        self._query_by_field: dict[str, str] = {key: "" for key, *_rest in self.FIELD_SPECS}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        selector_row = QHBoxLayout()
        selector_row.setContentsMargins(0, 0, 0, 0)
        selector_row.setSpacing(10)

        search_by_box = QWidget()
        search_by_layout = QVBoxLayout(search_by_box)
        search_by_layout.setContentsMargins(0, 0, 0, 0)
        search_by_layout.setSpacing(4)
        search_by_label = QLabel("Search by")
        search_by_label.setObjectName("TinyLabel")
        self.field_combo = ModernComboButton()
        self.field_combo.setMinimumHeight(40)
        self.field_combo.setMinimumWidth(170)
        for key, label, _placeholder in self.FIELD_SPECS:
            self.field_combo.addItem(label, userData=key)
        self.field_combo.currentIndexChanged.connect(self._field_changed)
        search_by_layout.addWidget(search_by_label)
        search_by_layout.addWidget(self.field_combo)

        enter_box = QWidget()
        enter_layout = QVBoxLayout(enter_box)
        enter_layout.setContentsMargins(0, 0, 0, 0)
        enter_layout.setSpacing(4)
        enter_label = QLabel("Enter value")
        enter_label.setObjectName("TinyLabel")
        self.enter_value_frame = QFrame()
        self.enter_value_frame.setObjectName("GuidedValueBox")
        self.enter_value_frame.setMinimumHeight(40)
        self.enter_value_frame.setMaximumHeight(40)
        self.enter_value_frame.setProperty("focused", False)

        enter_input_row = QHBoxLayout(self.enter_value_frame)
        enter_input_row.setContentsMargins(0, 0, 0, 0)
        enter_input_row.setSpacing(0)
        self.search_edit = QLineEdit()
        self.search_edit.setObjectName("GuidedSearchInput")
        self.search_edit.setFrame(False)
        self.search_edit.setMinimumHeight(38)
        self.search_edit.textChanged.connect(self._search_text_changed)
        self.search_edit.textEdited.connect(self._user_search_text_edited)
        self.search_edit.returnPressed.connect(self._accept_inline_suggestion_or_open_picker)
        self.search_edit.installEventFilter(self)
        self.open_picker_btn = QPushButton("▾")
        self.open_picker_btn.setObjectName("PickerDropButton")
        self.open_picker_btn.setToolTip("Open filter options")
        self.open_picker_btn.setFlat(True)
        self.open_picker_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_picker_btn.setMinimumHeight(38)
        self.open_picker_btn.setMaximumHeight(38)
        self.open_picker_btn.setFixedWidth(38)
        self.open_picker_btn.installEventFilter(self)
        self.open_picker_btn.clicked.connect(self.open_picker_dialog)
        enter_input_row.addWidget(self.search_edit, 1)
        enter_input_row.addWidget(self.open_picker_btn, 0)
        enter_layout.addWidget(enter_label)
        enter_layout.addWidget(self.enter_value_frame)

        selector_row.addWidget(search_by_box, 1)
        selector_row.addWidget(enter_box, 4)
        layout.addLayout(selector_row)

        self.status_label = QLabel("0 values available")
        self.status_label.setObjectName("CompactFilterStatus")
        layout.addWidget(self.status_label)

        self.chip_container = QWidget()
        self.chip_layout = QHBoxLayout(self.chip_container)
        self.chip_layout.setContentsMargins(0, 0, 0, 0)
        self.chip_layout.setSpacing(5)
        layout.addWidget(self.chip_container)

        self._inline_popup = _InlineSuggestionPopup(self)
        self._inline_popup.picked.connect(self._select_inline_value)
        self._inline_popup.request_full_list.connect(self.open_picker_dialog)

        self._field_changed()

    def current_field_key(self) -> str:
        data = self.field_combo.currentData()
        return str(data or "company")

    def set_field_options(self, field_key: str, values: Iterable[object] | dict[object, int]) -> None:
        field_key = str(field_key)
        if field_key not in self._options_by_field:
            return
        if isinstance(values, dict):
            counts = {self._clean(key): int(count) for key, count in values.items() if self._clean(key)}
            options = sorted(counts, key=self._sort_key)
        else:
            counts: dict[str, int] = {}
            for raw in values:
                value = self._clean(raw)
                if value:
                    counts[value] = counts.get(value, 0) + 1
            options = sorted(counts, key=self._sort_key)
        self._options_by_field[field_key] = options
        self._counts_by_field[field_key] = counts
        valid = set(options)
        self._selected_by_field[field_key] = {value for value in self._selected_by_field[field_key] if value in valid}
        self._refresh_chips()
        self._refresh_status()
        self._sync_enter_value_display()

    def selected_values(self, field_key: str | None = None) -> list[str]:
        key = field_key or self.current_field_key()
        options = self._options_by_field.get(key, [])
        selected = self._selected_by_field.get(key, set())
        return [value for value in options if value in selected]

    def selected_map(self) -> dict[str, list[str]]:
        return {key: self.selected_values(key) for key in self._options_by_field}

    def set_selected_values(self, field_key: str, values: Iterable[object]) -> None:
        key = str(field_key)
        if key not in self._options_by_field:
            return
        valid = set(self._options_by_field[key])
        self._selected_by_field[key] = {self._clean(value) for value in values if self._clean(value) in valid}
        self._sync_enter_value_display()
        self._refresh_chips()
        self._refresh_status()
        self.selection_changed.emit()

    def clear_selection(self) -> None:
        self._hide_inline_suggestions()
        key = self.current_field_key()
        changed = bool(self._selected_by_field.get(key)) or bool(self._query_by_field.get(key, ""))
        self._selected_by_field[key].clear()
        self._query_by_field[key] = ""
        self._sync_enter_value_display()
        self._refresh_chips()
        self._refresh_status()
        if changed:
            self.selection_changed.emit()

    def clear_all_selections(self) -> None:
        self._hide_inline_suggestions()
        changed = any(self._selected_by_field.values()) or any(self._query_by_field.values())
        for key in self._selected_by_field:
            self._selected_by_field[key].clear()
            self._query_by_field[key] = ""
        self._sync_enter_value_display()
        self._refresh_chips()
        self._refresh_status()
        if changed:
            self.selection_changed.emit()

    def open_picker_dialog(self) -> None:
        self._hide_inline_suggestions()
        key = self.current_field_key()
        old_query = self._query_by_field.get(key, "")
        popup = _FloatingValuePicker(
            self._field_placeholders.get(key, "Search or select value..."),
            self._field_labels.get(key, "value"),
            self,
        )
        popup.query_changed.connect(lambda text, field_key=key: self._mirror_popup_query(field_key, text))
        selected_for_key = self._selected_by_field.get(key, set())
        popup.set_data(
            self._options_by_field.get(key, []),
            self._counts_by_field.get(key, {}),
            selected_for_key,
            "" if selected_for_key else self._query_by_field.get(key, ""),
        )
        # v8.7: keep the picker visually attached to Enter value; never let it become
        # a full-dashboard overlay. The cap prevents the old oversized popup look.
        input_width = self.search_edit.width() + self.open_picker_btn.width()
        width = min(max(_FloatingValuePicker.MIN_WIDTH, input_width), _FloatingValuePicker.MAX_WIDTH)
        popup.setFixedSize(width, _FloatingValuePicker.POPUP_HEIGHT)
        anchor = self.search_edit.mapToGlobal(self.search_edit.rect().bottomLeft())
        popup.move(anchor.x(), anchor.y() + 4)
        if popup.exec() == QDialog.DialogCode.Accepted:
            selected_values = set(popup.selected_values())
            self._selected_by_field[key] = selected_values
            # Do not keep stale internal popup search text after the user has selected explicit values.
            self._query_by_field[key] = "" if selected_values else popup.current_query()
            self._sync_enter_value_display()
            self._refresh_chips()
            self._refresh_status()
            self.selection_changed.emit()
        else:
            # v8.9: popup typing is only preview state until Apply. Cancel must not
            # leave a second hidden query in the main Enter value box.
            self._query_by_field[key] = old_query
            self._sync_enter_value_display()

    def _mirror_popup_query(self, field_key: str, text: str) -> None:
        """Keep the main Enter value box and the full picker search state identical.

        This fixes the confusing two-search-box state where the main input could show
        an old query while the full selectable popup searched with a different query.
        """
        if field_key != self.current_field_key():
            return
        self._query_by_field[field_key] = text.strip()
        self.search_edit.blockSignals(True)
        self.search_edit.setText(text)
        self.search_edit.blockSignals(False)

    def query_text(self, field_key: str | None = None) -> str:
        key = field_key or self.current_field_key()
        return self._query_by_field.get(key, "").strip()

    def query_map(self) -> dict[str, str]:
        return {key: value.strip() for key, value in self._query_by_field.items() if value.strip()}

    def eventFilter(self, watched, event) -> bool:  # noqa: N802
        if watched in {self.search_edit, self.open_picker_btn}:
            if event.type() == QEvent.Type.FocusIn:
                self._set_enter_value_focus(True)
                if watched is self.search_edit:
                    QTimer.singleShot(0, self._show_inline_suggestions)
            elif event.type() == QEvent.Type.FocusOut:
                if not self.search_edit.hasFocus() and not self.open_picker_btn.hasFocus():
                    self._set_enter_value_focus(False)
            elif watched is self.search_edit and event.type() == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Down:
                if self._inline_popup.isVisible():
                    self._inline_popup.focus_first()
                    return True
            elif watched is self.search_edit and event.type() == QEvent.Type.KeyRelease:
                QTimer.singleShot(0, self._show_inline_suggestions)
        return super().eventFilter(watched, event)

    def _set_enter_value_focus(self, focused: bool) -> None:
        if hasattr(self, "enter_value_frame"):
            self.enter_value_frame.setProperty("focused", focused)
            self.enter_value_frame.style().unpolish(self.enter_value_frame)
            self.enter_value_frame.style().polish(self.enter_value_frame)

    def _selection_preview_text(self, key: str) -> str:
        selected = self.selected_values(key)
        if not selected:
            return ""
        preview = ", ".join(selected[:2])
        if len(preview) > 48:
            preview = preview[:45] + "…"
        if len(selected) > 2:
            preview += f" +{len(selected) - 2} more"
        return preview

    def _search_text_changed(self, text: str) -> None:
        current = self.current_field_key()
        selected = self.selected_values(current)
        if selected and text == self._selection_preview_text(current):
            return
        if selected:
            self._selected_by_field[current].clear()
            self._refresh_chips()
            self._refresh_status()
        self._query_by_field[current] = text.strip()

    def _user_search_text_edited(self, text: str) -> None:
        current = self.current_field_key()
        if self.selected_values(current):
            self._selected_by_field[current].clear()
            self._refresh_chips()
            self._refresh_status()
        self._query_by_field[current] = text.strip()
        # v8.9: reopen live suggestions after Qt has committed the edited text.
        # This prevents the first keystroke from opening suggestions while later
        # keystrokes fail because the popup briefly changed focus/state.
        QTimer.singleShot(0, self._show_inline_suggestions)

    def _sync_enter_value_display(self) -> None:
        key = self.current_field_key()
        selected = self.selected_values(key)
        self.search_edit.blockSignals(True)
        self.search_edit.setText(self._selection_preview_text(key) if selected else self._query_by_field.get(key, ""))
        self.search_edit.blockSignals(False)
        self.search_edit.setPlaceholderText(self._field_placeholders.get(key, "Search or select value..."))

    def _ranked_inline_suggestions(self, query: str, *, limit: int = 8) -> list[tuple[str, int]]:
        key = self.current_field_key()
        query = query.strip()
        if not query:
            return []
        ranked: list[tuple[float, str]] = []
        selected = self._selected_by_field.get(key, set())
        for option in self._options_by_field.get(key, []):
            if option in selected:
                continue
            score = self._score(query, option)
            if score >= 32.0:
                ranked.append((score, option))
        ranked.sort(key=lambda item: (-item[0], self._sort_key(item[1])))
        counts = self._counts_by_field.get(key, {})
        return [(value, counts.get(value, 0)) for _score, value in ranked[:limit]]

    def _show_inline_suggestions(self) -> None:
        key = self.current_field_key()
        if self.selected_values(key):
            self._hide_inline_suggestions()
            return
        query = self._query_by_field.get(key, "").strip()
        if not query:
            self._hide_inline_suggestions()
            return
        suggestions = self._ranked_inline_suggestions(query)
        self._inline_popup.set_items(suggestions, self._field_labels.get(key, "value"))
        width = self.search_edit.width() + self.open_picker_btn.width()
        self._inline_popup.show_below(self.search_edit, width)
        self._inline_popup.raise_()

    def _hide_inline_suggestions(self) -> None:
        if hasattr(self, "_inline_popup") and self._inline_popup.isVisible():
            self._inline_popup.hide()

    def _accept_inline_suggestion_or_open_picker(self) -> None:
        if self._inline_popup.isVisible():
            first = self._inline_popup.first_value()
            if first:
                self._select_inline_value(first)
                return
        self.open_picker_dialog()

    def _select_inline_value(self, value: str) -> None:
        key = self.current_field_key()
        if value not in set(self._options_by_field.get(key, [])):
            return
        before = set(self._selected_by_field.get(key, set()))
        self._selected_by_field[key].add(value)
        self._query_by_field[key] = ""
        self._hide_inline_suggestions()
        self._sync_enter_value_display()
        self._refresh_chips()
        self._refresh_status()
        if before != self._selected_by_field[key]:
            self.selection_changed.emit()

    def _field_changed(self) -> None:
        self._hide_inline_suggestions()
        self._sync_enter_value_display()
        self.open_picker_btn.setToolTip(f"Open selectable {self._field_labels.get(self.current_field_key(), 'value').lower()} values")
        self._refresh_chips()
        self._refresh_status()

    def _refresh_status(self) -> None:
        key = self.current_field_key()
        total = len(self._options_by_field.get(key, []))
        selected = len(self._selected_by_field.get(key, set()))
        label = self._field_labels.get(key, "Value")
        if selected:
            self.status_label.setText(f"{selected} {label.lower()} selected · {total} available")
        else:
            self.status_label.setText(f"{total} {label.lower()} values available")
        self.search_edit.setToolTip(self.status_label.text())

    def _clear_chip_layout(self) -> None:
        while self.chip_layout.count():
            item = self.chip_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _remove_selected_value(self, field_key: str, value: str) -> None:
        selected = self._selected_by_field.get(field_key, set())
        if value in selected:
            selected.remove(value)
            self._sync_enter_value_display()
            self._refresh_status()
            self._refresh_chips()
            self.selection_changed.emit()

    def _refresh_chips(self) -> None:
        self._clear_chip_layout()
        total_selected = sum(len(values) for values in self._selected_by_field.values())
        if not total_selected:
            self.chip_layout.addStretch(1)
            return
        rendered = 0
        for field_key, label_text, _placeholder in self.FIELD_SPECS:
            for value in self.selected_values(field_key):
                if rendered >= 4:
                    break
                short_value = value if len(value) <= 20 else value[:17] + "…"
                chip = QPushButton(f"{label_text}: {short_value}  ×")
                chip.setObjectName("SelectedFilterChip")
                chip.setToolTip(f"Remove {value} from {label_text}")
                chip.clicked.connect(lambda _checked=False, fk=field_key, v=value: self._remove_selected_value(fk, v))
                self.chip_layout.addWidget(chip)
                rendered += 1
            if rendered >= 4:
                break
        if total_selected > rendered:
            more = QLabel(f"+{total_selected - rendered} more")
            more.setObjectName("EmptyChipHint")
            self.chip_layout.addWidget(more)
        self.chip_layout.addStretch(1)
