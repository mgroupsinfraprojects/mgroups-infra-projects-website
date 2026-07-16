from __future__ import annotations

from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout


class LoadingOverlay(QFrame):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("LoadingOverlay")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        self.label = QLabel("Processing…")
        self.label.setObjectName("SectionTitle")
        layout.addWidget(self.label)
        self.hide()

    def set_message(self, message: str) -> None:
        self.label.setText(message)
