from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


class _ModernComboRow(QFrame):
    clicked = Signal(int)

    def __init__(self, index: int, text: str, selected: bool = False, parent=None) -> None:
        super().__init__(parent)
        self.index = index
        self.setObjectName("ModernComboRow")
        self.setProperty("selected", selected)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)
        self.label = QLabel(text)
        self.label.setObjectName("ModernComboRowText")
        self.check = QLabel("✓" if selected else "")
        self.check.setObjectName("ModernComboCheck")
        layout.addWidget(self.label, 1)
        layout.addWidget(self.check, 0, Qt.AlignmentFlag.AlignRight)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.index)
        super().mousePressEvent(event)


class ModernComboPopup(QFrame):
    picked = Signal(int)

    def __init__(self, items: list[tuple[str, object]], current_index: int, parent=None) -> None:
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setObjectName("ModernComboPopup")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)
        max_width = 220
        for index, (text, _data) in enumerate(items):
            row = _ModernComboRow(index, text, index == current_index, self)
            row.clicked.connect(self._pick)
            layout.addWidget(row)
            max_width = max(max_width, len(text) * 8 + 56)
        self.setMinimumWidth(max_width)

    def _pick(self, index: int) -> None:
        self.picked.emit(index)
        self.close()


class ModernComboButton(QPushButton):
    currentIndexChanged = Signal(int)
    currentTextChanged = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("ModernComboButton")
        self._items: list[tuple[str, object]] = []
        self._current_index = -1
        self._popup: ModernComboPopup | None = None
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setCheckable(False)
        self.clicked.connect(self.showPopup)
        self.setMinimumHeight(38)

    def addItem(self, text: str, userData: object | None = None) -> None:  # noqa: N802
        self._items.append((str(text), userData))
        if self._current_index < 0:
            self.setCurrentIndex(0)

    def addItems(self, texts: list[str] | tuple[str, ...]) -> None:  # noqa: N802
        for text in texts:
            self.addItem(str(text), None)

    def clear(self) -> None:
        self._items.clear()
        self._current_index = -1
        self._sync_text()

    def count(self) -> int:
        return len(self._items)

    def currentIndex(self) -> int:  # noqa: N802
        return self._current_index

    def currentText(self) -> str:  # noqa: N802
        if 0 <= self._current_index < len(self._items):
            return self._items[self._current_index][0]
        return ""

    def currentData(self) -> object:  # noqa: N802
        if 0 <= self._current_index < len(self._items):
            data = self._items[self._current_index][1]
            return self._items[self._current_index][0] if data is None else data
        return None

    def setCurrentIndex(self, index: int) -> None:  # noqa: N802
        if not self._items:
            self._current_index = -1
            self._sync_text()
            return
        index = max(0, min(int(index), len(self._items) - 1))
        if index == self._current_index:
            self._sync_text()
            return
        self._current_index = index
        self._sync_text()
        self.currentIndexChanged.emit(index)
        self.currentTextChanged.emit(self.currentText())

    def setCurrentText(self, text: str) -> None:  # noqa: N802
        for index, (label, _data) in enumerate(self._items):
            if label == text:
                self.setCurrentIndex(index)
                return

    def showPopup(self) -> None:  # noqa: N802
        if not self._items:
            return
        if self._popup is not None:
            self._popup.close()
        self._popup = ModernComboPopup(self._items, self._current_index, self)
        self._popup.picked.connect(self.setCurrentIndex)
        width = max(self.width(), self._popup.minimumWidth())
        height = min(360, 8 + len(self._items) * 42)
        self._popup.resize(width, height)
        pos = self.mapToGlobal(self.rect().bottomLeft())
        self._popup.move(pos.x(), pos.y() + 4)
        self._popup.show()

    def _sync_text(self) -> None:
        text = self.currentText() or "Select"
        self.setText(f"{text}   ▾")
