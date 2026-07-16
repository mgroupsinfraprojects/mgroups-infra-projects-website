from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout


class MetricCard(QFrame):
    """Reusable premium metric card.

    This component is UI-only. It receives already-computed text values from the
    dashboard/controller layer and never recalculates audit totals.
    """

    def __init__(
        self,
        title: str,
        value: str = "—",
        subtitle: str = "",
        delta: str = "",
        accent: str = "",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("MetricCard")
        self.setCursor(Qt.PointingHandCursor)
        if accent:
            self.setProperty("accent", accent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(8)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("MetricLabel")
        self.title_label.setWordWrap(True)
        top_row.addWidget(self.title_label)
        top_row.addStretch(1)
        layout.addLayout(top_row)

        self.value_label = QLabel(value)
        self.value_label.setObjectName("MetricValue")
        self.value_label.setWordWrap(True)
        self.value_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.value_label)

        bottom_row = QHBoxLayout()
        bottom_row.setContentsMargins(0, 0, 0, 0)
        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setObjectName("MetricSubtext")
        self.subtitle_label.setWordWrap(True)
        self.delta_label = QLabel(delta)
        self.delta_label.setObjectName("MetricDelta")
        self.delta_label.setWordWrap(True)
        self.delta_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        bottom_row.addWidget(self.subtitle_label, 1)
        bottom_row.addWidget(self.delta_label, 0)
        layout.addLayout(bottom_row)
        layout.addStretch(1)
        self.delta_label.setVisible(bool(delta))

    def set_value(self, value: str, subtitle: str | None = None, delta: str | None = None) -> None:
        self.value_label.setText(value)
        if subtitle is not None:
            self.subtitle_label.setText(subtitle)
        if delta is not None:
            self.delta_label.setText(delta)
            self.delta_label.setVisible(bool(delta))
