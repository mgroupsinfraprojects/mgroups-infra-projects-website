from __future__ import annotations

from typing import Any

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, Signal
from PySide6.QtGui import QAction, QColor
from PySide6.QtWidgets import QApplication, QAbstractItemView, QHeaderView, QMenu, QTableView


class DataTableModel(QAbstractTableModel):
    """Lightweight, virtual table model for audit/report grids.

    The previous widget-backed table created one QTableWidgetItem for every cell.
    This model keeps plain Python values and lets Qt request visible cells only,
    which is materially safer for large invoice datasets.
    """

    STATUS_COLORS = {
        "VALID": QColor(22, 163, 74, 28),
        "APPROVED": QColor(22, 163, 74, 28),
        "REVIEW_REQUIRED": QColor(245, 158, 11, 32),
        "WARNING": QColor(245, 158, 11, 32),
        "GST_MISMATCH": QColor(245, 158, 11, 32),
        "INVALID": QColor(239, 68, 68, 34),
        "ERROR": QColor(239, 68, 68, 34),
        "SKIPPED": QColor(100, 116, 139, 24),
        "DUPLICATE": QColor(100, 116, 139, 24),
    }

    def __init__(self) -> None:
        super().__init__()
        self._headers: list[str] = []
        self._rows: list[list[str]] = []
        self._source_rows: list[int] = []
        self._status_column = -1

    def set_rows(self, headers: list[str], rows: list[list[Any]], status_column: int = -1) -> None:
        self.beginResetModel()
        self._headers = [str(header) for header in headers]
        self._rows = [["" if value is None else str(value) for value in row] for row in rows]
        self._source_rows = list(range(len(self._rows)))
        self._status_column = status_column
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802 - Qt override
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802 - Qt override
        return 0 if parent.isValid() else len(self._headers)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid() or index.row() >= len(self._rows) or index.column() >= len(self._headers):
            return None
        if role in {Qt.DisplayRole, Qt.ToolTipRole}:
            return self._rows[index.row()][index.column()]
        if role == Qt.BackgroundRole and self._status_column >= 0:
            status = self._rows[index.row()][self._status_column].upper()
            for key, color in self.STATUS_COLORS.items():
                if key in status:
                    return color
        if role == Qt.TextAlignmentRole:
            return Qt.AlignVCenter | Qt.AlignLeft
        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole) -> Any:  # noqa: N802 - Qt override
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal and 0 <= section < len(self._headers):
            return self._headers[section]
        if orientation == Qt.Vertical:
            return str(section + 1)
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.NoItemFlags
        return Qt.ItemIsSelectable | Qt.ItemIsEnabled

    def sort(self, column: int, order: Qt.SortOrder = Qt.AscendingOrder) -> None:
        if column < 0 or column >= len(self._headers):
            return
        reverse = order == Qt.DescendingOrder

        def key_fn(pair: tuple[list[str], int]) -> tuple[int, Any]:
            value = pair[0][column]
            text = str(value).strip()
            money_text = text.replace("₹", "").replace(",", "").replace("%", "")
            try:
                return (0, float(money_text))
            except ValueError:
                return (1, text.lower())

        pairs = list(zip(self._rows, self._source_rows))
        self.layoutAboutToBeChanged.emit()
        pairs.sort(key=key_fn, reverse=reverse)
        self._rows = [row for row, _source in pairs]
        self._source_rows = [source for _row, source in pairs]
        self.layoutChanged.emit()

    def source_row_for_view_row(self, view_row: int) -> int:
        if 0 <= view_row < len(self._source_rows):
            return self._source_rows[view_row]
        return -1

    def cell_text(self, row: int, column: int) -> str:
        if 0 <= row < len(self._rows) and 0 <= column < len(self._headers):
            return self._rows[row][column]
        return ""


class DataTable(QTableView):
    """Reusable virtual audit table.

    Uses QTableView + QAbstractTableModel instead of QTableWidget so large audit
    datasets do not allocate one widget item per cell.
    """

    accept_requested = Signal()
    reject_requested = Signal()
    detail_requested = Signal()
    itemSelectionChanged = Signal()

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._model = DataTableModel()
        self.setModel(self._model)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setSortingEnabled(True)
        self.setShowGrid(False)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._open_context_menu)
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setHighlightSections(False)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(36)
        if self.selectionModel() is not None:
            self.selectionModel().selectionChanged.connect(lambda *_args: self.itemSelectionChanged.emit())

    def set_data(self, headers: list[str], rows: list[list[Any]], status_column: int = -1) -> None:
        sorting = self.isSortingEnabled()
        self.setSortingEnabled(False)
        self._model.set_rows(headers, rows, status_column=status_column)
        self.setSortingEnabled(sorting)

    def columnCount(self) -> int:  # compatibility with previous table helper code
        return self._model.columnCount()

    def rowCount(self) -> int:  # compatibility with previous table helper code
        return self._model.rowCount()

    def currentRow(self) -> int:  # compatibility with previous QTableWidget call sites
        index = self.currentIndex()
        return index.row() if index.isValid() else -1

    def source_row_for_view_row(self, view_row: int) -> int:
        return self._model.source_row_for_view_row(view_row)

    def apply_status_formatting(self, status_column: int = 1) -> None:
        # Formatting is model-backed through Qt.BackgroundRole. This method is
        # retained as an API compatibility no-op for older call sites.
        self._model._status_column = status_column
        if self._model.rowCount() > 0 and self._model.columnCount() > 0:
            top_left = self._model.index(0, 0)
            bottom_right = self._model.index(self._model.rowCount() - 1, self._model.columnCount() - 1)
            self._model.dataChanged.emit(top_left, bottom_right, [Qt.BackgroundRole])

    def _open_context_menu(self, position) -> None:
        menu = QMenu(self)
        copy_cell = QAction("Copy Cell", self)
        copy_row = QAction("Copy Row", self)
        view_detail = QAction("View Raw / Detected / Final", self)
        accept = QAction("Accept Selected", self)
        reject = QAction("Reject Selected", self)
        copy_cell.triggered.connect(self.copy_current_cell)
        copy_row.triggered.connect(self.copy_current_row)
        view_detail.triggered.connect(self.detail_requested.emit)
        accept.triggered.connect(self.accept_requested.emit)
        reject.triggered.connect(self.reject_requested.emit)
        menu.addAction(copy_cell)
        menu.addAction(copy_row)
        menu.addSeparator()
        menu.addAction(view_detail)
        menu.addAction(accept)
        menu.addAction(reject)
        menu.exec(self.viewport().mapToGlobal(position))

    def copy_current_cell(self) -> None:
        index = self.currentIndex()
        if index.isValid():
            QApplication.clipboard().setText(self._model.cell_text(index.row(), index.column()))

    def copy_current_row(self) -> None:
        row = self.currentRow()
        if row < 0:
            return
        values = [self._model.cell_text(row, col) for col in range(self.columnCount())]
        QApplication.clipboard().setText("\t".join(values))
