from __future__ import annotations

from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QVBoxLayout, QWidget

from app.ui.widgets.data_table import DataTable
from app.ui.widgets.status_chip import StatusChip


def _make_recon_card(title: str, chip_attr: str, detail_attr: str):
    card = QFrame()
    card.setObjectName("ReconciliationCard")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(12, 10, 12, 10)
    layout.setSpacing(6)
    heading = QLabel(title)
    heading.setObjectName("MetricLabel")
    chip = StatusChip("Not run", "neutral")
    detail = QLabel("Process files to calculate this check.")
    detail.setObjectName("MutedText")
    detail.setWordWrap(True)
    layout.addWidget(heading)
    layout.addWidget(chip)
    layout.addWidget(detail)
    return card, chip, detail, chip_attr, detail_attr


def build_reconciliation_tab(window) -> None:
    tab = QWidget()
    layout = QVBoxLayout(tab)
    layout.setSpacing(12)
    title = QLabel("Proof")
    title.setObjectName("PageTitle")
    note = QLabel(
        "Use this only when you want proof that every imported row and amount agrees with the audit totals. "
        "Optional GSTR-2A/2B matching compares your books against GST portal data; it does not change original audit totals."
    )
    note.setWordWrap(True)
    note.setObjectName("MutedText")

    help_box = QLabel(
        "Simple meaning: Row Coverage = no imported row disappeared. Amount Cross-check = raw invoice value equals approved + review + excluded value. "
        "Dashboard Rule = filters never change official totals."
    )
    help_box.setObjectName("SummaryCards")
    help_box.setWordWrap(True)

    actions = QHBoxLayout()
    import_gstr_btn = QPushButton("Import GSTR-2A / 2B Files")
    clear_gstr_btn = QPushButton("Clear GSTR Reconciliation")
    clear_gstr_btn.setObjectName("SecondaryButton")
    window.recon_details_toggle_btn = QPushButton("Show technical details")
    window.recon_details_toggle_btn.setObjectName("SecondaryButton")
    window.recon_details_toggle_btn.setCheckable(True)
    import_gstr_btn.clicked.connect(window.import_gstr_reconciliation_files)
    clear_gstr_btn.clicked.connect(window.clear_gstr_reconciliation)
    actions.addWidget(import_gstr_btn)
    actions.addWidget(clear_gstr_btn)
    actions.addWidget(window.recon_details_toggle_btn)
    actions.addStretch(1)

    recon_grid = QGridLayout()
    recon_grid.setHorizontalSpacing(12)
    recon_grid.setVerticalSpacing(12)
    cards = [
        _make_recon_card("Row coverage", "recon_row_coverage_chip", "recon_row_coverage_detail"),
        _make_recon_card("Amount cross-check", "recon_amount_chip", "recon_amount_detail"),
        _make_recon_card("Dashboard rule", "recon_dashboard_rule_chip", "recon_dashboard_rule_detail"),
        _make_recon_card("Final status", "recon_final_status_chip", "recon_final_status_detail"),
    ]
    for idx, (card, chip, detail, chip_attr, detail_attr) in enumerate(cards):
        setattr(window, chip_attr, chip)
        setattr(window, detail_attr, detail)
        recon_grid.addWidget(card, idx // 2, idx % 2)

    window.recon_details_panel = QFrame()
    window.recon_details_panel.setObjectName("ReconciliationDetailsPanel")
    details_layout = QVBoxLayout(window.recon_details_panel)
    details_layout.setContentsMargins(0, 0, 0, 0)
    detail_label = QLabel("Detailed reconciliation log")
    detail_label.setObjectName("SectionTitle")
    window.reconciliation_text = QTextEdit()
    window.reconciliation_text.setReadOnly(True)
    window.reconciliation_text.setMaximumHeight(190)
    window.gstr_reconciliation_table = DataTable()
    window.gstr_reconciliation_table.setObjectName("gstr_reconciliation_table")
    details_layout.addWidget(detail_label)
    details_layout.addWidget(window.reconciliation_text)
    details_layout.addWidget(QLabel("GSTR-2A/2B Matching Details"))
    details_layout.addWidget(window.gstr_reconciliation_table)
    window.recon_details_panel.setVisible(False)

    def toggle_details(checked: bool) -> None:
        window.recon_details_panel.setVisible(checked)
        window.recon_details_toggle_btn.setText("Hide technical details" if checked else "Show technical details")

    window.recon_details_toggle_btn.toggled.connect(toggle_details)

    layout.addWidget(title)
    layout.addWidget(note)
    layout.addWidget(help_box)
    layout.addLayout(actions)
    layout.addWidget(QLabel("Audit Reconciliation Summary"))
    layout.addLayout(recon_grid)
    layout.addWidget(window.recon_details_panel, 1)
    window.tabs.addTab(tab, "Proof")
