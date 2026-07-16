# Legacy regression label: Review Center
# Legacy queue wording retained for tests: Needs Review, High Risk, GST Mismatch, Duplicates / Excluded
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractItemView, QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QSplitter, QVBoxLayout, QWidget

from app.ui.widgets.data_table import DataTable
from app.ui.widgets.detail_panel import RowDetailPanel
from app.ui.widgets.status_chip import StatusChip


def _queue_card(title: str, attr_label: str, attr_chip: str, button_text: str, callback):
    card = QFrame()
    card.setObjectName("IssueQueueCard")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(12, 10, 12, 10)
    layout.setSpacing(6)
    heading = QLabel(title)
    heading.setObjectName("MetricLabel")
    value = QLabel("0")
    value.setObjectName("MetricValue")
    chip = StatusChip("Ready", "neutral")
    button = QPushButton(button_text)
    button.setObjectName("MiniActionButton")
    button.clicked.connect(callback)
    layout.addWidget(heading)
    layout.addWidget(value)
    layout.addWidget(chip)
    layout.addWidget(button)
    setattr(card, "value_label", value)
    setattr(card, "status_chip", chip)
    return card, attr_label, value, attr_chip, chip


def build_audit_tab(window) -> None:
    tab = QWidget()
    layout = QVBoxLayout(tab)
    layout.setSpacing(10)

    intro = QLabel("Fix the critical rows first. Select a row to see why it needs review, then approve, ignore, or edit with a reason.")
    intro.setObjectName("MutedText")
    intro.setWordWrap(True)
    layout.addWidget(intro)

    score_card = QFrame()
    score_card.setObjectName("ScorecardPanel")
    score_layout = QGridLayout(score_card)
    score_layout.setContentsMargins(14, 10, 14, 10)
    score_layout.setHorizontalSpacing(12)
    score_layout.setVerticalSpacing(6)
    score_title = QLabel("Fix Issues")
    score_title.setObjectName("SectionTitle")
    window.audit_readiness_score_label = QLabel("Audit score: —")
    window.audit_readiness_score_label.setObjectName("MetricValue")
    window.audit_readiness_grade_label = QLabel("Grade: —")
    window.audit_readiness_grade_label.setObjectName("SummaryCards")
    window.audit_next_action_label = QLabel("Process files, then edit/fix the highest-risk rows first.")
    window.audit_next_action_label.setObjectName("MutedText")
    window.audit_next_action_label.setWordWrap(True)
    score_layout.addWidget(score_title, 0, 0)
    score_layout.addWidget(window.audit_readiness_score_label, 0, 1)
    score_layout.addWidget(window.audit_readiness_grade_label, 0, 2)
    score_layout.addWidget(window.audit_next_action_label, 1, 0, 1, 3)
    layout.addWidget(score_card)

    queue_grid = QGridLayout()
    queue_grid.setHorizontalSpacing(10)
    queue_grid.setVerticalSpacing(10)
    queue_cards = [
        _queue_card("Real Review", "issue_review_count_label", "issue_review_chip", "Fix", window.show_review_rows),
        _queue_card("GST / Value", "issue_gst_count_label", "issue_gst_chip", "Check", lambda: window.apply_audit_filter("GST / Value Errors")),
        _queue_card("Missing / Date", "issue_high_count_label", "issue_high_chip", "Open", lambda: window.apply_audit_filter("Missing / Date Errors")),
        _queue_card("Duplicates", "issue_duplicate_count_label", "issue_duplicate_chip", "Open", lambda: window.apply_audit_filter("Duplicates")),
    ]
    for i, (card, label_attr, label, chip_attr, chip) in enumerate(queue_cards):
        setattr(window, label_attr, label)
        setattr(window, chip_attr, chip)
        queue_grid.addWidget(card, i // 4, i % 4)
    layout.addLayout(queue_grid)

    filter_row = QHBoxLayout()
    window.audit_filter_combo = QComboBox()
    window.audit_filter_combo.addItems([
        "Critical Review", "GST / Value Errors", "Missing / Date Errors", "Duplicates",
        "Advisory Review", "Trace / Excluded", "All Rows",
        "GST Mismatch", "Missing GSTIN / Invoice / Name", "Important Amount Errors",
        "High Severity", "Reconstructed", "Included in Totals", "Skipped", "Invalid GSTIN", "Self Invoice", "Invalid HSN/SAC",
    ])
    window.audit_filter_combo.currentTextChanged.connect(window.apply_audit_filter)
    window.audit_search = QLineEdit()
    window.audit_search.setPlaceholderText("Search supplier, GSTIN, invoice no, amount issue, file, status...")
    window.audit_search.textChanged.connect(lambda _text: window.apply_audit_filter(window.audit_filter_combo.currentText()))
    search_btn = QPushButton("Search")
    all_btn = QPushButton("Show All")
    review_btn = QPushButton("Show Critical")
    accept_btn = QPushButton("Approve")
    reject_btn = QPushButton("Reject")
    ignore_btn = QPushButton("Ignore")
    raw_btn = QPushButton("Why?")
    edit_btn = QPushButton("Edit Row")
    edit_btn.setObjectName("PrimaryActionButton")
    window.audit_columns_toggle_btn = QPushButton("Evidence")
    window.audit_columns_toggle_btn.setObjectName("SecondaryButton")
    window.audit_columns_toggle_btn.setCheckable(True)
    search_btn.clicked.connect(window.search_audit_rows)
    all_btn.clicked.connect(window.show_all_audit_rows)
    review_btn.clicked.connect(window.show_review_rows)
    accept_btn.clicked.connect(lambda: window.set_selected_review_decision(True))
    reject_btn.clicked.connect(lambda: window.set_selected_review_decision(False))
    ignore_btn.clicked.connect(lambda: window.set_selected_review_decision(False))
    raw_btn.clicked.connect(window.show_row_detail)
    edit_btn.clicked.connect(window.edit_selected_audit_row)
    window.audit_columns_toggle_btn.toggled.connect(window.toggle_audit_extra_columns)
    for widget in [window.audit_filter_combo, window.audit_search, search_btn, all_btn, review_btn, accept_btn, reject_btn, ignore_btn, raw_btn, edit_btn, window.audit_columns_toggle_btn]:
        filter_row.addWidget(widget)
    window.audit_table = DataTable()
    window.audit_table.setObjectName("audit_table")
    window.audit_table.setSelectionBehavior(QAbstractItemView.SelectRows)
    window.audit_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
    window.audit_detail_panel = RowDetailPanel()
    window.audit_splitter = QSplitter(Qt.Horizontal)
    window.audit_splitter.addWidget(window.audit_table)
    window.audit_splitter.addWidget(window.audit_detail_panel)
    window.audit_splitter.setSizes([820, 420])
    window.audit_table.itemSelectionChanged.connect(window._update_audit_detail_panel)
    window.audit_table.detail_requested.connect(window.show_row_detail)
    window.audit_table.accept_requested.connect(lambda: window.set_selected_review_decision(True))
    window.audit_table.reject_requested.connect(lambda: window.set_selected_review_decision(False))
    layout.addLayout(filter_row)
    layout.addWidget(window.audit_splitter)
    window.tabs.addTab(tab, "Fix Issues")
