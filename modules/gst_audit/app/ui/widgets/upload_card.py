from __future__ import annotations

from pathlib import Path
from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)


class UploadCard(QFrame):
    """Simple upload card for normal users.

    The selected-file table is intentionally collapsed by default once files are
    chosen. Accountants usually need the count and readiness first; the full
    file list is still available through Show selected files.
    """

    browse_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("UploadCard")
        self.setAcceptDrops(True)
        self._files: list[str] = []
        self._details_visible = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(10)

        header = QLabel("Add Excel / CSV files")
        header.setObjectName("UploadTitle")
        helper = QLabel("Drop files here or click Browse. The app never changes your original files.")
        helper.setObjectName("MutedText")
        helper.setAlignment(Qt.AlignLeft)
        helper.setWordWrap(True)

        button_row = QHBoxLayout()
        browse = QPushButton("Browse Files")
        browse.setObjectName("PrimaryActionButton")
        browse.clicked.connect(self.browse_requested.emit)
        self.summary_label = QLabel("No files selected")
        self.summary_label.setObjectName("SummaryCards")
        self.summary_label.setWordWrap(True)
        self.toggle_details_btn = QPushButton("Show selected files")
        self.toggle_details_btn.setObjectName("SecondaryButton")
        self.toggle_details_btn.clicked.connect(self.toggle_details)
        self.toggle_details_btn.setVisible(False)

        button_row.addWidget(browse)
        button_row.addWidget(self.summary_label, 1)
        button_row.addWidget(self.toggle_details_btn)

        self.file_table = QTableWidget(0, 4)
        self.file_table.setHorizontalHeaderLabels(["File", "Type", "Size", "Status"])
        self.file_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.file_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.file_table.setObjectName("UploadFileTable")
        self.file_table.setMaximumHeight(180)
        self.file_table.setVisible(False)

        layout.addWidget(header)
        layout.addWidget(helper)
        layout.addLayout(button_row)
        layout.addWidget(self.file_table)

    def toggle_details(self) -> None:
        self._details_visible = not self._details_visible
        self.file_table.setVisible(self._details_visible)
        self.toggle_details_btn.setText("Hide selected files" if self._details_visible else "Show selected files")

    def set_files(self, files: list[str]) -> None:
        self._files = list(files)
        count = len(self._files)
        if count == 0:
            self.summary_label.setText("No files selected")
            self.toggle_details_btn.setVisible(False)
            self._details_visible = False
            self.file_table.setVisible(False)
            self.file_table.setRowCount(0)
            return

        total_size = sum(Path(file).stat().st_size for file in self._files if Path(file).exists())
        suffixes = sorted({Path(file).suffix.upper().lstrip(".") or "FILE" for file in self._files})
        self.summary_label.setText(
            f"{count} file(s) selected · {', '.join(suffixes)} · {self._format_size(total_size)} total · Ready to audit"
        )
        self.toggle_details_btn.setVisible(True)
        self.file_table.setVisible(self._details_visible)
        self.file_table.setRowCount(count)
        for row, file in enumerate(self._files):
            path = Path(file)
            size = path.stat().st_size if path.exists() else 0
            values = [path.name, path.suffix.upper().lstrip("."), self._format_size(size), "Ready"]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.file_table.setItem(row, col, item)
        self.file_table.resizeColumnsToContents()

    @staticmethod
    def _format_size(size: int) -> str:
        if size >= 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        if size >= 1024:
            return f"{size / 1024:.1f} KB"
        return f"{size} B"
