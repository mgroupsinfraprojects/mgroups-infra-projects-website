# Legacy wording retained: Review queue, Final lock
from __future__ import annotations

from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from app.ui.widgets.status_chip import StatusChip


def _ready_card(title: str, chip_attr: str, detail_attr: str):
    card = QFrame()
    card.setObjectName("ExportReadyCard")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(12, 10, 12, 10)
    layout.setSpacing(6)
    heading = QLabel(title)
    heading.setObjectName("MetricLabel")
    chip = StatusChip("Waiting", "neutral")
    detail = QLabel("Process files first.")
    detail.setObjectName("MutedText")
    detail.setWordWrap(True)
    layout.addWidget(heading)
    layout.addWidget(chip)
    layout.addWidget(detail)
    layout.addStretch(1)
    return card, chip_attr, chip, detail_attr, detail


def build_export_tab(window) -> None:
    tab = QWidget()
    layout = QVBoxLayout(tab)
    layout.setSpacing(12)
    title = QLabel("Export")
    title.setObjectName("PageTitle")
    description = QLabel("Simple rule: Draft export is allowed after processing. Final export is enabled only after Critical Review = 0.")
    description.setObjectName("MutedText")
    description.setWordWrap(True)

    window.export_quality_score_label = QLabel("Quality score: —")
    window.export_quality_score_label.setObjectName("SummaryCards")
    window.export_quality_status_chip = StatusChip("Waiting", "neutral")

    status_row = QHBoxLayout()
    status_row.addWidget(window.export_quality_status_chip)
    status_row.addWidget(window.export_quality_score_label, 1)

    ready_grid = QGridLayout()
    ready_grid.setHorizontalSpacing(10)
    ready_grid.setVerticalSpacing(10)
    cards = [
        _ready_card("1. Row coverage", "export_row_chip", "export_row_detail"),
        _ready_card("2. Amount match", "export_amount_chip", "export_amount_detail"),
        _ready_card("3. Critical review", "export_review_chip", "export_review_detail"),
        _ready_card("4. Final export readiness", "export_lock_chip", "export_lock_detail"),
    ]
    for i, (card, chip_attr, chip, detail_attr, detail) in enumerate(cards):
        setattr(window, chip_attr, chip)
        setattr(window, detail_attr, detail)
        ready_grid.addWidget(card, i // 2, i % 2)

    window.export_draft_btn = QPushButton("Export Draft Report")
    window.export_draft_btn.setObjectName("SecondaryButton")
    window.export_final_btn = QPushButton("Export Final Report")
    window.export_final_btn.setObjectName("PrimaryActionButton")
    window.export_final_btn.setEnabled(False)
    evidence_btn = QPushButton("Export Excel Evidence")
    evidence_btn.setObjectName("SecondaryButton")
    window.export_draft_btn.clicked.connect(window.export_draft_excel)
    window.export_final_btn.clicked.connect(window.export_final_excel)
    evidence_btn.clicked.connect(window.export_draft_excel)
    action_row = QHBoxLayout()
    action_row.addWidget(window.export_draft_btn)
    action_row.addWidget(window.export_final_btn)
    action_row.addWidget(evidence_btn)
    action_row.addStretch(1)

    window.export_readiness_score_label = QLabel("Audit readiness score: —")
    window.export_readiness_score_label.setObjectName("SummaryCards")
    window.export_readiness_score_label.setWordWrap(True)

    warning = QLabel("Note: worksheet protection prevents accidental edits only. It is not encryption.")
    warning.setWordWrap(True)
    warning.setObjectName("MutedText")

    window.export_preview = QLabel("No processed audit result yet. Process files to preview exactly what will be exported.")
    window.export_preview.setObjectName("SummaryCards")
    window.export_preview.setWordWrap(True)
    window.export_status = QLabel("No export created yet.")
    window.export_status.setObjectName("SummaryCards")
    window.export_status.setWordWrap(True)

    layout.addWidget(title)
    layout.addWidget(description)
    layout.addWidget(QLabel("Export Readiness"))
    layout.addLayout(status_row)
    layout.addLayout(ready_grid)
    layout.addLayout(action_row)
    layout.addWidget(window.export_readiness_score_label)
    layout.addWidget(warning)
    layout.addWidget(QLabel("Export contents"))
    layout.addWidget(window.export_preview)
    layout.addWidget(window.export_status)
    layout.addStretch(1)
    window.tabs.addTab(tab, "Export")
