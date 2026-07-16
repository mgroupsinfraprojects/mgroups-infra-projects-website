from __future__ import annotations

from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout


class EmptyState(QFrame):
    def __init__(self, title: str, message: str, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("EmptyState")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        title_label = QLabel(title)
        title_label.setObjectName("SectionTitle")
        message_label = QLabel(message)
        message_label.setObjectName("MutedText")
        message_label.setWordWrap(True)
        layout.addWidget(title_label)
        layout.addWidget(message_label)
