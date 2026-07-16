# Legacy regression label: Start Here
# Legacy regression strings: 1. Choose Files | 2. Start Audit | 3. Review Issues | 4. Export
from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QVBoxLayout, QWidget

from app.ui.widgets.empty_state import EmptyState
from app.ui.widgets.status_chip import StatusChip
from app.ui.widgets.upload_card import UploadCard


def _step_card(number: str, title: str, detail: str, chip_text: str, chip_attr: str):
    card = QFrame()
    card.setObjectName("SimpleStepCard")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(14, 12, 14, 12)
    layout.setSpacing(6)
    heading = QLabel(f"{number}. {title}")
    heading.setObjectName("SectionTitle")
    detail_label = QLabel(detail)
    detail_label.setObjectName("MutedText")
    detail_label.setWordWrap(True)
    chip = StatusChip(chip_text, "neutral")
    layout.addWidget(heading)
    layout.addWidget(detail_label)
    layout.addWidget(chip)
    layout.addStretch(1)
    return card, chip_attr, chip


def build_upload_tab(window) -> None:
    tab = QWidget()
    layout = QVBoxLayout(tab)
    layout.setSpacing(12)

    title = QLabel("Start")
    title.setObjectName("PageTitle")
    subtitle = QLabel(
        "Simple flow: choose Excel files, the app checks duplicate months, then opens Fix Issues automatically."
    )
    subtitle.setObjectName("MutedText")
    subtitle.setWordWrap(True)

    window.import_profile_combo = QComboBox()
    window.import_profile_combo.addItems([
        "Auto detect columns",
        "Purchase Register / Books",
        "GSTR-2A / GSTR-2B",
        "Supplier Invoice List",
        "Custom Excel / CSV",
    ])
    window.import_profile_combo.setToolTip("Select the closest file type. Auto detect is safest for mixed files.")
    profile_row = QHBoxLayout()
    profile_label = QLabel("File type")
    profile_label.setObjectName("MetricLabel")
    profile_row.addWidget(profile_label)
    profile_row.addWidget(window.import_profile_combo, 1)
    profile_row.addStretch(1)

    step_grid = QGridLayout()
    step_grid.setHorizontalSpacing(10)
    step_grid.setVerticalSpacing(10)
    cards = [
        _step_card("1", "Choose files", "Add purchase register, GST invoice list, GSTR-2A/2B, or supplier files.", "Waiting", "simple_file_status_chip"),
        _step_card("2", "Start audit", "The app checks identity, invoice number, taxable value, GST value, total value, duplicates, and source row proof.", "Waiting", "simple_process_status_chip"),
        _step_card("3", "Review issues", "Fix Critical rows first. Advisory differences and skipped/trace rows remain in detail for evidence.", "Waiting", "simple_review_status_chip"),
        _step_card("4", "Export report", "Draft export is allowed after processing. Final export is allowed only when Critical Review is clear.", "Waiting", "simple_export_status_chip"),
    ]
    for i, (card, attr, chip) in enumerate(cards):
        setattr(window, attr, chip)
        step_grid.addWidget(card, i // 2, i % 2)

    window.upload_card = UploadCard()
    window.upload_card.browse_requested.connect(window.select_files)

    action_row = QHBoxLayout()
    choose_btn = QPushButton("Choose Files")
    choose_btn.setObjectName("SecondaryButton")
    choose_btn.setToolTip("Ctrl+O — select one or more GST Excel/CSV files")
    window.process_btn = QPushButton("Start Audit")
    window.process_btn.setObjectName("PrimaryActionButton")
    window.process_btn.setToolTip("Ctrl+P — process the selected files")
    review_btn = QPushButton("Fix Issues")
    review_btn.setObjectName("SecondaryButton")
    export_btn = QPushButton("Export")
    export_btn.setObjectName("SecondaryButton")
    load_last_btn = QPushButton("View Last Audit")
    load_last_btn.setObjectName("LinkButton")
    clear_btn = QPushButton("Clear")
    clear_btn.setObjectName("DangerOutlineButton")
    clear_btn.setToolTip("Clear the current file selection without deleting files")
    choose_btn.clicked.connect(window.select_files)
    window.process_btn.clicked.connect(window.process_files)
    review_btn.clicked.connect(lambda: window._set_page(2))
    export_btn.clicked.connect(lambda: window._set_page(5))
    load_last_btn.clicked.connect(window.load_last_dataset)
    clear_btn.clicked.connect(window.clear_selected_files)
    for button in [choose_btn, window.process_btn, review_btn, export_btn, load_last_btn, clear_btn]:
        action_row.addWidget(button)
    action_row.addStretch(1)

    window.import_safety_panel = QFrame()
    window.import_safety_panel.setObjectName("ScorecardPanel")
    import_safety_layout = QGridLayout(window.import_safety_panel)
    import_safety_layout.setContentsMargins(14, 10, 14, 10)
    window.import_safety_label = QLabel("Import safety: waiting for files")
    window.import_safety_label.setObjectName("MetricValue")
    window.import_safety_note = QLabel("The app will scan inside each workbook, detect duplicate periods, prefer full GSTR-2B files, and block unsafe imports.")
    window.import_safety_note.setObjectName("MutedText")
    window.import_safety_note.setWordWrap(True)
    export_import_report_btn = QPushButton("Export Import Safety Report")
    export_import_report_btn.setObjectName("SecondaryButton")
    export_import_report_btn.clicked.connect(window.export_import_safety_excel)
    import_safety_layout.addWidget(window.import_safety_label, 0, 0)
    import_safety_layout.addWidget(export_import_report_btn, 0, 1)
    import_safety_layout.addWidget(window.import_safety_note, 1, 0, 1, 2)

    window.upload_score_panel = QFrame()
    window.upload_score_panel.setObjectName("ScorecardPanel")
    upload_score_layout = QGridLayout(window.upload_score_panel)
    upload_score_layout.setContentsMargins(14, 10, 14, 10)
    window.upload_score_label = QLabel("Audit readiness score: —")
    window.upload_score_label.setObjectName("MetricValue")
    window.upload_score_note = QLabel("The score appears after processing. It tells whether the audit is ready for final export.")
    window.upload_score_note.setObjectName("MutedText")
    window.upload_score_note.setWordWrap(True)
    upload_score_layout.addWidget(window.upload_score_label, 0, 0)
    upload_score_layout.addWidget(window.upload_score_note, 1, 0)

    window.upload_empty_state = EmptyState(
        "No files selected yet",
        "Click Choose Files. After processing, the app will show the next action: Fix Critical Issues or Export.",
    )
    window.file_box = QTextEdit()
    window.file_box.setReadOnly(True)
    window.file_box.setVisible(False)

    layout.addWidget(title)
    layout.addWidget(subtitle)
    layout.addLayout(profile_row)
    # Simple Mode: hide the four large instruction cards; their chips still exist
    # for the legacy progress updater, but users see only the direct action flow.
    step_holder = QWidget()
    step_holder.setLayout(step_grid)
    step_holder.setVisible(False)
    layout.addWidget(step_holder)
    layout.addWidget(window.upload_card)
    layout.addLayout(action_row)
    layout.addWidget(window.import_safety_panel)
    layout.addWidget(window.upload_score_panel)
    window.upload_empty_state.setVisible(False)
    layout.addWidget(window.upload_empty_state)
    layout.addWidget(window.file_box)
    layout.addStretch(1)
    window.tabs.addTab(tab, "Start")
