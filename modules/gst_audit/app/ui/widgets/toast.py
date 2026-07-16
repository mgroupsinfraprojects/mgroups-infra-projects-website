from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QLabel, QWidget


class Toast(QLabel):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Toast")
        self.hide()

    def show_message(self, message: str, timeout_ms: int = 3000) -> None:
        self.setText(message)
        self.adjustSize()
        self.show()
        QTimer.singleShot(timeout_ms, self.hide)
