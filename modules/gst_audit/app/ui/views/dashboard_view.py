# Legacy dashboard issue labels: Review rows, High risk, GST mismatch, Duplicates / skipped
from __future__ import annotations

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QScrollArea,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTextBrowser,
    QVBoxLayout,
    QSizePolicy,
    QWidget,
)

from app.ui.widgets.chart_panel import SimpleBarChart
from app.ui.widgets.status_chip import StatusChip
from app.ui.widgets.data_table import DataTable
from app.ui.widgets.guided_filter import SearchByValueMultiSelect
from app.ui.widgets.modern_combo import ModernComboButton


DASHBOARD_MODES = [
    "Overview",
    "Review Focus",
    "Supplier Focus",
    "GSTIN Focus",
    "Tax Mismatch",
    "Monthly Trend",
    "Advanced Custom",
]


MODE_HELP = {
    "Overview": "Best default view: totals, monthly value, suppliers, status and mismatch summary.",
    "Review Focus": "Shows only rows needing decisions and groups them by mismatch reason.",
    "Supplier Focus": "Ranks supplier/company totals and prepares the table for supplier drill-down.",
    "GSTIN Focus": "Groups by GSTIN so you can check supplier tax identity and totals.",
    "Tax Mismatch": "Prioritises GST formula mismatch amount and exception reasons.",
    "Monthly Trend": "Shows month-wise movement with a line chart.",
    "Advanced Custom": "Unlocks all filters and chart settings for expert analysis.",
}


def build_dashboard_tab(window) -> None:
    """Build the accountant dashboard page.

    The dashboard now exposes selectable work modes for normal users. Expert
    controls still exist, but they stay hidden until needed so the page does not
    feel like a technical form.
    """
    tab = QWidget()
    outer_layout = QVBoxLayout(tab)
    outer_layout.setContentsMargins(0, 0, 0, 0)
    outer_layout.setSpacing(0)

    scroll = QScrollArea()
    scroll.setObjectName("DashboardScrollArea")
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    content = QWidget()
    content.setObjectName("DashboardContent")
    layout = QVBoxLayout(content)
    layout.setContentsMargins(18, 18, 18, 18)
    layout.setSpacing(14)

    title = QLabel("Dashboard")
    title.setObjectName("PageTitle")
    hint = QLabel(
        "Simple dashboard: search, totals, and charts only. Click any total card or chart bar to open details."
    )
    hint.setObjectName("MutedText")
    hint.setWordWrap(True)


    # Decision-first top area. This is intentionally small and child-readable:
    # Status -> What to fix -> Export safety. Charts stay secondary.
    decision_grid = QGridLayout()
    decision_grid.setHorizontalSpacing(12)
    decision_grid.setVerticalSpacing(12)

    window.dashboard_decision_card = QFrame()
    window.dashboard_decision_card.setObjectName("DashboardDecisionCard")
    decision_layout = QVBoxLayout(window.dashboard_decision_card)
    decision_layout.setContentsMargins(16, 14, 16, 14)
    decision_layout.setSpacing(8)
    decision_header = QHBoxLayout()
    decision_title = QLabel("Audit status")
    decision_title.setObjectName("MetricLabel")
    window.dashboard_decision_chip = StatusChip("No data", "neutral")
    decision_header.addWidget(decision_title)
    decision_header.addStretch(1)
    decision_header.addWidget(window.dashboard_decision_chip)
    decision_layout.addLayout(decision_header)
    window.dashboard_decision_status_label = QLabel("Choose files and start audit.")
    window.dashboard_decision_status_label.setObjectName("DashboardDecisionTitle")
    window.dashboard_decision_status_label.setWordWrap(True)
    decision_layout.addWidget(window.dashboard_decision_status_label)
    window.dashboard_decision_instruction_label = QLabel("Simple path: Choose Files → Start Audit → Review Issues → Export.")
    window.dashboard_decision_instruction_label.setObjectName("DashboardDecisionText")
    window.dashboard_decision_instruction_label.setWordWrap(True)
    decision_layout.addWidget(window.dashboard_decision_instruction_label)
    decision_buttons = QHBoxLayout()
    window.dashboard_decision_primary_btn = QPushButton("Review Issues")
    window.dashboard_decision_primary_btn.setObjectName("PrimaryActionButton")
    window.dashboard_decision_primary_btn.clicked.connect(window._dashboard_next_action_primary)
    window.dashboard_decision_export_btn = QPushButton("Export")
    window.dashboard_decision_export_btn.setObjectName("SecondaryButton")
    window.dashboard_decision_export_btn.clicked.connect(lambda: window._set_page(5))
    decision_buttons.addWidget(window.dashboard_decision_primary_btn)
    decision_buttons.addWidget(window.dashboard_decision_export_btn)
    decision_buttons.addStretch(1)
    decision_layout.addLayout(decision_buttons)
    decision_grid.addWidget(window.dashboard_decision_card, 0, 0, 2, 1)

    window.dashboard_totals_card = QFrame()
    window.dashboard_totals_card.setObjectName("DashboardMiniPanel")
    totals_layout = QGridLayout(window.dashboard_totals_card)
    totals_layout.setContentsMargins(14, 12, 14, 12)
    totals_layout.setHorizontalSpacing(12)
    totals_layout.setVerticalSpacing(6)
    totals_title = QLabel("Official vs visible totals")
    totals_title.setObjectName("MetricLabel")
    totals_layout.addWidget(totals_title, 0, 0, 1, 2)
    window.dashboard_official_invoice_label = QLabel("Official: —")
    window.dashboard_visible_invoice_label = QLabel("Visible: —")
    window.dashboard_official_review_label = QLabel("Official review: —")
    window.dashboard_visible_review_label = QLabel("Visible review: —")
    for idx, label in enumerate([
        window.dashboard_official_invoice_label,
        window.dashboard_visible_invoice_label,
        window.dashboard_official_review_label,
        window.dashboard_visible_review_label,
    ], start=1):
        label.setObjectName("DashboardMiniText")
        label.setWordWrap(True)
        totals_layout.addWidget(label, (idx + 1) // 2, (idx - 1) % 2)
    decision_grid.addWidget(window.dashboard_totals_card, 0, 1)

    window.dashboard_quality_card = QFrame()
    window.dashboard_quality_card.setObjectName("DashboardMiniPanel")
    quality_layout = QGridLayout(window.dashboard_quality_card)
    quality_layout.setContentsMargins(14, 12, 14, 12)
    quality_layout.setHorizontalSpacing(10)
    quality_layout.setVerticalSpacing(6)
    quality_title = QLabel("Quality Gate before export")
    quality_title.setObjectName("MetricLabel")
    quality_layout.addWidget(quality_title, 0, 0, 1, 4)
    window.dashboard_quality_score_label = QLabel("Score: —")
    window.dashboard_quality_score_label.setObjectName("DashboardMiniText")
    quality_layout.addWidget(window.dashboard_quality_score_label, 1, 0)
    window.dashboard_gate_row_chip = StatusChip("Rows", "neutral")
    window.dashboard_gate_amount_chip = StatusChip("Amount", "neutral")
    window.dashboard_gate_review_chip = StatusChip("Review", "neutral")
    window.dashboard_gate_lock_chip = StatusChip("Export", "neutral")
    for idx, chip in enumerate([
        window.dashboard_gate_row_chip,
        window.dashboard_gate_amount_chip,
        window.dashboard_gate_review_chip,
        window.dashboard_gate_lock_chip,
    ]):
        quality_layout.addWidget(chip, 1, idx + 1)
    window.dashboard_quality_note_label = QLabel("Process files to calculate export safety.")
    window.dashboard_quality_note_label.setObjectName("DashboardMiniText")
    window.dashboard_quality_note_label.setWordWrap(True)
    quality_layout.addWidget(window.dashboard_quality_note_label, 2, 0, 1, 5)
    decision_grid.addWidget(window.dashboard_quality_card, 1, 1)

    window.dashboard_scorecard_panel = QFrame()
    window.dashboard_scorecard_panel.setObjectName("ScorecardPanel")
    score_layout = QGridLayout(window.dashboard_scorecard_panel)
    score_layout.setContentsMargins(14, 12, 14, 12)
    score_layout.setHorizontalSpacing(10)
    score_layout.setVerticalSpacing(6)
    score_title = QLabel("Audit Readiness Score")
    score_title.setObjectName("MetricLabel")
    window.dashboard_readiness_score_label = QLabel("—/100")
    window.dashboard_readiness_score_label.setObjectName("MetricValue")
    window.dashboard_readiness_grade_label = QLabel("Grade: —")
    window.dashboard_readiness_grade_label.setObjectName("SummaryCards")
    window.dashboard_score_formula_label = QLabel("Score is based on row coverage, amount match, critical rows, advisory rows, trace rows, and final-export readiness.")
    window.dashboard_score_formula_label.setObjectName("MutedText")
    window.dashboard_score_formula_label.setWordWrap(True)
    window.dashboard_score_next_label = QLabel("Next: process files to calculate the score.")
    window.dashboard_score_next_label.setObjectName("DashboardMiniText")
    window.dashboard_score_next_label.setWordWrap(True)
    score_layout.addWidget(score_title, 0, 0)
    score_layout.addWidget(window.dashboard_readiness_score_label, 0, 1)
    score_layout.addWidget(window.dashboard_readiness_grade_label, 0, 2)
    score_layout.addWidget(window.dashboard_score_formula_label, 1, 0, 1, 3)
    score_layout.addWidget(window.dashboard_score_next_label, 2, 0, 1, 3)
    decision_grid.addWidget(window.dashboard_scorecard_panel, 2, 0, 1, 2)

    window.dashboard_issue_panel = QFrame()
    window.dashboard_issue_panel.setObjectName("DashboardIssuePanel")
    issue_layout = QGridLayout(window.dashboard_issue_panel)
    issue_layout.setContentsMargins(14, 12, 14, 12)
    issue_layout.setHorizontalSpacing(10)
    issue_layout.setVerticalSpacing(8)
    issue_title = QLabel("Fix first")
    issue_title.setObjectName("SectionTitle")
    issue_layout.addWidget(issue_title, 0, 0, 1, 4)

    def add_issue_card(col: int, title_text: str, value_attr: str, chip_attr: str, button_text: str, callback) -> None:
        card = QFrame()
        card.setObjectName("DashboardIssueCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(10, 8, 10, 8)
        card_layout.setSpacing(5)
        card_title = QLabel(title_text)
        card_title.setObjectName("MetricLabel")
        value_label = QLabel("0")
        value_label.setObjectName("DashboardIssueNumber")
        chip = StatusChip("Waiting", "neutral")
        button = QPushButton(button_text)
        button.setObjectName("LinkButton")
        button.clicked.connect(callback)
        setattr(window, value_attr, value_label)
        setattr(window, chip_attr, chip)
        card_layout.addWidget(card_title)
        card_layout.addWidget(value_label)
        card_layout.addWidget(chip)
        card_layout.addWidget(button)
        issue_layout.addWidget(card, 1, col)

    add_issue_card(0, "Critical review", "dashboard_issue_review_label", "dashboard_issue_review_chip", "Open", window._dashboard_open_review_queue)
    add_issue_card(1, "Missing identity", "dashboard_issue_high_label", "dashboard_issue_high_chip", "Open", window._dashboard_open_high_risk)
    add_issue_card(2, "GST / amount error", "dashboard_issue_gst_label", "dashboard_issue_gst_chip", "Open", window._dashboard_open_tax_mismatch)
    add_issue_card(3, "Trace only", "dashboard_issue_excluded_label", "dashboard_issue_excluded_chip", "Trace", window._dashboard_open_excluded_rows)

    # Core controls owned by MainWindow/controller
    window.dashboard_search_field_combo = QComboBox()
    window.dashboard_search_field_combo.addItems([
        "Auto / Any Field",
        "Company / Supplier",
        "GSTIN",
        "Invoice Number",
        "Month",
        "Source File",
        "Status / Issue",
    ])
    window.dashboard_search_field_combo.setToolTip(
        "Choose exactly what the search box should match. Use Auto for broad search."
    )
    window.dashboard_filter_text = QLineEdit()
    window.dashboard_filter_text.setPlaceholderText(
        "Legacy global search kept for saved views and chart drill-down."
    )
    window.dashboard_filter_text.setVisible(False)
    window.dashboard_search_field_combo.setVisible(False)

    window.dashboard_search_selector = SearchByValueMultiSelect()

    window.dashboard_mode_combo = ModernComboButton()
    window.dashboard_mode_combo.addItems(DASHBOARD_MODES)
    window.dashboard_mode_combo.setToolTip("Choose the dashboard workflow. Advanced Custom unlocks all manual filters.")

    window.dashboard_status_combo = QComboBox()
    window.dashboard_status_combo.addItems([
        "All Rows", "Approved", "Critical Review", "GST Mismatch", "Advisory Review", "High Severity", "Trace / Excluded",
    ])
    window.dashboard_group_combo = QComboBox()
    window.dashboard_group_combo.addItems(["Month", "Supplier", "GSTIN", "Source File", "Audit Status", "Mismatch Reason", "HSN/SAC"])
    window.dashboard_metric_combo = QComboBox()
    window.dashboard_metric_combo.addItems(["Invoice Value", "Taxable Value", "Total GST", "Invoice Count", "Review Rows", "Mismatch Amount"])
    window.dashboard_chart_mode_combo = QComboBox()
    window.dashboard_chart_mode_combo.addItems(["Bar", "Line", "Donut"])
    window.dashboard_date_enabled = QCheckBox("Use date range")
    window.dashboard_from_date = QDateEdit()
    window.dashboard_from_date.setCalendarPopup(True)
    window.dashboard_from_date.setDisplayFormat("dd-MM-yyyy")
    window.dashboard_from_date.setDate(QDate.currentDate().addMonths(-12))
    window.dashboard_to_date = QDateEdit()
    window.dashboard_to_date.setCalendarPopup(True)
    window.dashboard_to_date.setDisplayFormat("dd-MM-yyyy")
    window.dashboard_to_date.setDate(QDate.currentDate())
    window.dashboard_saved_view_combo = QComboBox()
    window.dashboard_saved_view_combo.addItem("Saved views...")
    window._load_dashboard_saved_view_names()
    window.dashboard_limit_spin = QSpinBox()
    window.dashboard_limit_spin.setRange(5, 50)
    window.dashboard_limit_spin.setValue(12)
    window.dashboard_limit_spin.setToolTip("Maximum groups shown in each chart")
    window.dashboard_limit_spin.setMinimumWidth(96)

    apply_filter = QPushButton("Apply View")
    clear_filter = QPushButton("Clear")
    save_view_btn = QPushButton("Save View")
    delete_view_btn = QPushButton("Delete View")
    export_pdf_btn = QPushButton("Export Dashboard PDF")
    filter_toggle_btn = QPushButton("Advanced Filters")
    filter_toggle_btn.setCheckable(True)

    for control in [
        window.dashboard_mode_combo,
        window.dashboard_status_combo,
        window.dashboard_group_combo,
        window.dashboard_metric_combo,
        window.dashboard_chart_mode_combo,
        window.dashboard_saved_view_combo,
        window.dashboard_from_date,
        window.dashboard_to_date,
    ]:
        control.setMinimumHeight(36)
    for button in [apply_filter, clear_filter, save_view_btn, delete_view_btn, export_pdf_btn, filter_toggle_btn]:
        button.setMinimumHeight(36)

    apply_filter.clicked.connect(window.apply_dashboard_filter)
    clear_filter.clicked.connect(window.clear_dashboard_filter)
    save_view_btn.clicked.connect(window.save_dashboard_view)
    delete_view_btn.clicked.connect(window.delete_dashboard_view)
    export_pdf_btn.clicked.connect(window.export_dashboard_pdf)
    window.dashboard_filter_text.returnPressed.connect(window.apply_dashboard_filter)
    window.dashboard_search_field_combo.currentTextChanged.connect(window.update_dashboard_search_placeholder)
    window.dashboard_search_field_combo.currentTextChanged.connect(lambda _text: window.apply_dashboard_filter())
    window.dashboard_search_selector.selection_changed.connect(window.apply_dashboard_filter)
    window.dashboard_mode_combo.currentTextChanged.connect(window.apply_dashboard_mode)
    window.dashboard_status_combo.currentTextChanged.connect(lambda _text: window.apply_dashboard_filter())
    window.dashboard_group_combo.currentTextChanged.connect(lambda _text: window.apply_dashboard_filter())
    window.dashboard_metric_combo.currentTextChanged.connect(lambda _text: window.apply_dashboard_filter())
    window.dashboard_chart_mode_combo.currentTextChanged.connect(lambda _text: window.apply_dashboard_filter())
    window.dashboard_limit_spin.valueChanged.connect(lambda _value: window.apply_dashboard_filter())
    window.dashboard_date_enabled.toggled.connect(lambda _checked: window.apply_dashboard_filter())
    window.dashboard_from_date.dateChanged.connect(lambda _date: window.apply_dashboard_filter())
    window.dashboard_to_date.dateChanged.connect(lambda _date: window.apply_dashboard_filter())
    window.dashboard_saved_view_combo.currentTextChanged.connect(window._apply_saved_dashboard_view)

    # Cleaner start panel: mode + search are visible; expert filters are hidden by default.
    filter_panel = QFrame()
    filter_panel.setObjectName("DashboardFilterPanel")
    filter_panel_layout = QVBoxLayout(filter_panel)
    filter_panel_layout.setContentsMargins(12, 6, 12, 6)
    filter_panel_layout.setSpacing(5)

    header = QHBoxLayout()
    filter_title = QLabel("Search and view")
    filter_title.setObjectName("SectionTitle")
    header.addWidget(filter_title)
    header.addStretch(1)
    header.addWidget(filter_toggle_btn)
    filter_panel_layout.addLayout(header)

    search_guide = QLabel("Choose a field, type/select values, then apply the view.")
    search_guide.setObjectName("SearchGuideText")
    search_guide.setWordWrap(True)
    filter_panel_layout.addWidget(search_guide)

    quick_row = QGridLayout()
    quick_row.setHorizontalSpacing(12)
    quick_row.setVerticalSpacing(6)
    quick_row.setColumnStretch(0, 5)
    quick_row.setColumnStretch(1, 2)
    quick_row.setColumnStretch(2, 1)
    quick_row.addWidget(window.dashboard_search_selector, 0, 0, 1, 1)
    quick_row.addWidget(window._labeled_control("Work mode", window.dashboard_mode_combo), 0, 1, 1, 1)
    quick_buttons = QWidget()
    quick_buttons_layout = QHBoxLayout(quick_buttons)
    quick_buttons_layout.setContentsMargins(0, 15, 0, 0)
    quick_buttons_layout.setSpacing(8)
    quick_buttons_layout.addWidget(apply_filter)
    quick_buttons_layout.addWidget(clear_filter)
    quick_buttons_layout.addStretch(1)
    quick_row.addWidget(quick_buttons, 0, 2, 1, 1)
    filter_panel_layout.addLayout(quick_row)

    window.dashboard_mode_help = QLabel(MODE_HELP["Overview"])
    window.dashboard_mode_help.setObjectName("ModeHelpText")
    window.dashboard_mode_help.setWordWrap(True)
    filter_panel_layout.addWidget(window.dashboard_mode_help)

    # Easy access strip: one-click filters like a modern master dashboard.
    # These filters affect only the visible dashboard/table, not raw data or official totals.
    quick_access_panel = QFrame()
    quick_access_panel.setObjectName("QuickAccessPanel")
    quick_access_layout = QGridLayout(quick_access_panel)
    quick_access_layout.setContentsMargins(10, 6, 10, 6)
    quick_access_layout.setHorizontalSpacing(10)
    quick_access_layout.setVerticalSpacing(4)

    source_title = QLabel("Source files")
    source_title.setObjectName("TinyLabel")
    month_title = QLabel("Months")
    month_title.setObjectName("TinyLabel")
    window.dashboard_source_chip_bar = QWidget()
    window.dashboard_source_chip_bar.setObjectName("ChipBar")
    window.dashboard_source_chip_layout = QHBoxLayout(window.dashboard_source_chip_bar)
    window.dashboard_source_chip_layout.setContentsMargins(0, 0, 0, 0)
    window.dashboard_source_chip_layout.setSpacing(6)
    window.dashboard_month_chip_bar = QWidget()
    window.dashboard_month_chip_bar.setObjectName("ChipBar")
    window.dashboard_month_chip_layout = QHBoxLayout(window.dashboard_month_chip_bar)
    window.dashboard_month_chip_layout.setContentsMargins(0, 0, 0, 0)
    window.dashboard_month_chip_layout.setSpacing(6)

    source_scroll = QScrollArea()
    source_scroll.setObjectName("ChipScroll")
    source_scroll.setWidgetResizable(True)
    source_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    source_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    source_scroll.setWidget(window.dashboard_source_chip_bar)
    source_scroll.setMinimumHeight(32)

    month_scroll = QScrollArea()
    month_scroll.setObjectName("ChipScroll")
    month_scroll.setWidgetResizable(True)
    month_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    month_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    month_scroll.setWidget(window.dashboard_month_chip_bar)
    month_scroll.setMinimumHeight(32)

    quick_access_layout.addWidget(source_title, 0, 0)
    quick_access_layout.addWidget(source_scroll, 0, 1)
    quick_access_layout.addWidget(month_title, 1, 0)
    quick_access_layout.addWidget(month_scroll, 1, 1)
    quick_access_layout.setColumnStretch(1, 1)
    filter_panel_layout.addWidget(quick_access_panel)

    filter_body = QWidget()
    window.dashboard_filter_body = filter_body
    filter_body.setObjectName("DashboardFilterBody")
    filter_layout = QGridLayout(filter_body)
    filter_layout.setContentsMargins(0, 4, 0, 0)
    filter_layout.setHorizontalSpacing(12)
    filter_layout.setVerticalSpacing(10)
    for col in range(4):
        filter_layout.setColumnStretch(col, 1)

    filter_layout.addWidget(window._labeled_control("Status", window.dashboard_status_combo), 0, 0)
    filter_layout.addWidget(window._labeled_control("Group by", window.dashboard_group_combo), 0, 1)
    filter_layout.addWidget(window._labeled_control("Metric", window.dashboard_metric_combo), 0, 2)
    filter_layout.addWidget(window._labeled_control("Chart", window.dashboard_chart_mode_combo), 0, 3)
    filter_layout.addWidget(window._labeled_control("Top N", window.dashboard_limit_spin), 1, 0)
    filter_layout.addWidget(window._labeled_control("Saved view", window.dashboard_saved_view_combo), 1, 1)
    filter_layout.addWidget(window.dashboard_date_enabled, 2, 0)
    filter_layout.addWidget(window._labeled_control("From", window.dashboard_from_date), 2, 1)
    filter_layout.addWidget(window._labeled_control("To", window.dashboard_to_date), 2, 2)

    advanced_buttons = QWidget()
    advanced_buttons_layout = QHBoxLayout(advanced_buttons)
    advanced_buttons_layout.setContentsMargins(0, 0, 0, 0)
    advanced_buttons_layout.setSpacing(8)
    advanced_buttons_layout.addStretch(1)
    for button in [save_view_btn, delete_view_btn, export_pdf_btn]:
        advanced_buttons_layout.addWidget(button)
    filter_layout.addWidget(advanced_buttons, 2, 3)

    filter_body.setVisible(False)
    filter_panel_layout.addWidget(filter_body)

    window.dashboard_active_filters = QLabel("Active view: Overview • All rows")
    window.dashboard_active_filters.setObjectName("ActiveFilterChips")
    window.dashboard_active_filters.setWordWrap(True)
    window.dashboard_active_filters.setMinimumHeight(32)
    filter_panel_layout.addWidget(window.dashboard_active_filters)

    def toggle_filter_body(checked: bool) -> None:
        filter_body.setVisible(checked)
        filter_toggle_btn.setText("Hide Advanced Filters" if checked else "Advanced Filters")
        if checked:
            window.dashboard_mode_combo.setCurrentText("Advanced Custom")

    filter_toggle_btn.toggled.connect(toggle_filter_body)
    window.dashboard_filter_toggle_btn = filter_toggle_btn

    # Metric cards
    window.dashboard_cards_layout = QGridLayout()
    window.dashboard_cards_layout.setHorizontalSpacing(12)
    window.dashboard_cards_layout.setVerticalSpacing(12)
    window.card_invoice, window.card_invoice_value = window._make_metric_card("Invoice Value")
    window.card_taxable, window.card_taxable_value = window._make_metric_card("Taxable Value")
    window.card_gst, window.card_gst_value = window._make_metric_card("Total GST")
    window.card_review, window.card_review_value = window._make_metric_card("Review Rows")
    metric_clicks = [
        (window.card_invoice, "Invoice Value"),
        (window.card_taxable, "Taxable Value"),
        (window.card_gst, "Total GST"),
        (window.card_review, "Review Rows"),
    ]
    for idx, (card, metric_name) in enumerate(metric_clicks):
        card.setMinimumHeight(132)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        card.mousePressEvent = lambda _event, m=metric_name: window.show_dashboard_metric_details(m)
        window.dashboard_cards_layout.addWidget(card, 0, idx)
        window.dashboard_cards_layout.setColumnStretch(idx, 1)

    # Next action card
    window.next_action_card = QFrame()
    window.next_action_card.setObjectName("NextActionCard")
    next_layout = QHBoxLayout(window.next_action_card)
    next_layout.setContentsMargins(14, 12, 14, 12)
    next_text_box = QVBoxLayout()
    next_title = QLabel("Next Action")
    next_title.setObjectName("MetricLabel")
    window.next_action_label = QLabel("Upload and process Excel/CSV files to start the audit.")
    window.next_action_label.setObjectName("NextActionText")
    window.next_action_label.setWordWrap(True)
    next_text_box.addWidget(next_title)
    next_text_box.addWidget(window.next_action_label)
    next_layout.addLayout(next_text_box, 1)
    window.next_action_primary_btn = QPushButton("Review Issues")
    window.next_action_primary_btn.clicked.connect(window._dashboard_next_action_primary)
    next_layout.addWidget(window.next_action_primary_btn)
    export_btn = QPushButton("Export Report")
    export_btn.clicked.connect(lambda: window._set_page(5))
    next_layout.addWidget(export_btn)

    # Status panel
    status_panel = QFrame()
    status_panel.setObjectName("StatusPanel")
    status_layout = QHBoxLayout(status_panel)
    status_layout.setContentsMargins(14, 10, 14, 10)
    window.dashboard_status_chip = StatusChip("No data", "neutral")
    status_layout.addWidget(window.dashboard_status_chip)
    window.summary_label = QLabel("Process files to view official audit status.")
    window.summary_label.setObjectName("SummaryText")
    window.summary_label.setWordWrap(True)
    status_layout.addWidget(window.summary_label, 1)

    # Charts grid: compact by default. Extra diagnostic charts are available, but hidden
    # until the user asks for them so the supplier drill-down table stays reachable on 768p screens.
    window.primary_chart = SimpleBarChart()
    window.primary_chart.point_clicked.connect(lambda label: window._dashboard_chart_clicked(label))
    window.supplier_chart = SimpleBarChart()
    window.supplier_chart.point_clicked.connect(lambda label: window._dashboard_chart_clicked(label, forced_group="Supplier"))
    window.status_breakdown_chart = SimpleBarChart()
    window.status_breakdown_chart.point_clicked.connect(lambda label: window._dashboard_chart_clicked(label, forced_group="Audit Status"))
    window.mismatch_chart = SimpleBarChart()
    window.mismatch_chart.point_clicked.connect(lambda label: window._dashboard_chart_clicked(label, forced_group="Mismatch Reason"))

    for chart in [window.primary_chart, window.supplier_chart, window.status_breakdown_chart, window.mismatch_chart]:
        chart.setMinimumHeight(220)
        chart.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    chart_header = QHBoxLayout()
    chart_title = QLabel("Charts — click a bar for full details")
    chart_title.setObjectName("SectionTitle")
    chart_header.addWidget(chart_title)
    chart_header.addStretch(1)
    window.dashboard_chart_details_btn = QPushButton("Show extra charts")
    window.dashboard_chart_details_btn.setObjectName("SecondaryButton")
    window.dashboard_chart_details_btn.setCheckable(True)
    chart_header.addWidget(window.dashboard_chart_details_btn)

    charts_section = QFrame()
    charts_section.setObjectName("ChartsSection")
    charts_section.setMinimumHeight(250)
    chart_grid = QGridLayout(charts_section)
    chart_grid.setContentsMargins(0, 0, 0, 0)
    chart_grid.setSpacing(14)
    chart_grid.setRowMinimumHeight(0, 220)
    chart_grid.setRowMinimumHeight(1, 220)
    chart_grid.setColumnStretch(0, 1)
    chart_grid.setColumnStretch(1, 1)
    chart_grid.addWidget(window.primary_chart, 0, 0)
    chart_grid.addWidget(window.supplier_chart, 0, 1)
    chart_grid.addWidget(window.status_breakdown_chart, 1, 0)
    chart_grid.addWidget(window.mismatch_chart, 1, 1)
    window.dashboard_extra_charts = [window.status_breakdown_chart, window.mismatch_chart]
    for chart in window.dashboard_extra_charts:
        chart.setVisible(False)

    def toggle_chart_details(checked: bool) -> None:
        for chart in window.dashboard_extra_charts:
            chart.setVisible(checked)
        window.dashboard_chart_details_btn.setText("Hide extra charts" if checked else "Show extra charts")
        charts_section.setMinimumHeight(500 if checked else 250)

    window.dashboard_chart_details_btn.toggled.connect(toggle_chart_details)

    table_title = QLabel("Supplier / GSTIN drill-down — optional detail")
    table_title.setObjectName("SectionTitle")
    window.dashboard_supplier_detail_toggle = QPushButton("Show supplier details")
    window.dashboard_supplier_detail_toggle.setObjectName("SecondaryButton")
    window.dashboard_supplier_detail_toggle.setCheckable(True)
    window.dashboard_table = DataTable()
    window.dashboard_table.setObjectName("dashboard_table")
    window.dashboard_table.setSelectionBehavior(QAbstractItemView.SelectRows)
    window.dashboard_table.setSelectionMode(QAbstractItemView.SingleSelection)
    window.dashboard_table.itemSelectionChanged.connect(window._update_dashboard_detail_panel)
    window.dashboard_detail = QTextBrowser()
    window.dashboard_detail.setReadOnly(True)
    window.dashboard_detail.setObjectName("DashboardDetailPanel")
    window.dashboard_detail.setPlaceholderText("Select a supplier row to see GSTIN, totals, review count, and suggested next step.")
    window.dashboard_table.setMinimumHeight(245)
    window.dashboard_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    window.dashboard_detail.setMinimumWidth(340)
    window.dashboard_detail.setMinimumHeight(245)
    window.dashboard_splitter = QSplitter(Qt.Horizontal)
    window.dashboard_splitter.setObjectName("DashboardDrilldownSplitter")
    window.dashboard_splitter.addWidget(window.dashboard_table)
    window.dashboard_splitter.addWidget(window.dashboard_detail)
    window.dashboard_splitter.setSizes([980, 420])
    window.dashboard_splitter.setMinimumHeight(260)
    window.dashboard_splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    table_title.setVisible(False)
    window.dashboard_splitter.setVisible(False)

    def toggle_supplier_details(checked: bool) -> None:
        table_title.setVisible(checked)
        window.dashboard_splitter.setVisible(checked)
        window.dashboard_supplier_detail_toggle.setText("Hide supplier details" if checked else "Show supplier details")

    window.dashboard_supplier_detail_toggle.toggled.connect(toggle_supplier_details)

    section_row = QHBoxLayout()
    search_btn = QPushButton("Search + Totals")
    analytics_btn = QPushButton("Charts + Suppliers")
    # Dashboard intentionally avoids the full Fix Issues panel. Fix Issues is a
    # separate workflow page; admin can hide/show it from Feature controls.
    fix_btn = QPushButton("Fix Issues")
    fix_btn.setVisible(False)
    window.dashboard_fix_button = fix_btn
    for btn in [search_btn, analytics_btn]:
        btn.setObjectName("SecondaryButton")
        section_row.addWidget(btn)
    section_row.addStretch(1)

    window.dashboard_fix_section = QFrame()
    window.dashboard_fix_section.setObjectName("DashboardSectionPanel")
    fix_layout = QVBoxLayout(window.dashboard_fix_section)
    fix_layout.setContentsMargins(0, 0, 0, 0)
    fix_layout.setSpacing(12)
    fix_layout.addLayout(decision_grid)
    fix_layout.addWidget(window.dashboard_issue_panel)

    window.dashboard_search_section = filter_panel

    window.dashboard_analytics_section = QFrame()
    window.dashboard_analytics_section.setObjectName("DashboardSectionPanel")
    analytics_layout = QVBoxLayout(window.dashboard_analytics_section)
    analytics_layout.setContentsMargins(0, 0, 0, 0)
    analytics_layout.setSpacing(12)
    analytics_layout.addLayout(window.dashboard_cards_layout)
    # Next-action and technical status are intentionally hidden from the default dashboard.
    # Start/Fix/Export pages own workflow decisions; dashboard focuses on search + totals + charts.
    window.next_action_card.setVisible(False)
    status_panel.setVisible(False)
    analytics_layout.addLayout(chart_header)
    analytics_layout.addWidget(charts_section)
    analytics_layout.addWidget(window.dashboard_supplier_detail_toggle)
    analytics_layout.addWidget(table_title)
    analytics_layout.addWidget(window.dashboard_splitter)

    def show_dashboard_section(name: str) -> None:
        # Dashboard modes are simplified: Search is always available, Charts/Totals
        # can be shown with it. The Fix Issues panel is no longer embedded here.
        window.dashboard_fix_section.setVisible(False)
        window.dashboard_search_section.setVisible(True)
        window.dashboard_analytics_section.setVisible(name in {"analytics", "all"})
        search_btn.setChecked(name == "search") if hasattr(search_btn, "setChecked") else None
        analytics_btn.setChecked(name in {"analytics", "all"}) if hasattr(analytics_btn, "setChecked") else None

    search_btn.clicked.connect(lambda: show_dashboard_section("search"))
    analytics_btn.clicked.connect(lambda: show_dashboard_section("analytics"))

    layout.addWidget(title)
    layout.addWidget(hint)
    layout.addLayout(section_row)
    # layout.addWidget(filter_panel)  # legacy regression marker; search is now embedded with totals/charts
    layout.addWidget(window.dashboard_search_section)
    layout.addWidget(window.dashboard_analytics_section)
    # Keep the hidden fix section object for compatibility/tests, but do not show
    # it in the Dashboard. Users should go to the Fix Issues page.
    window.dashboard_fix_section.setVisible(False)
    show_dashboard_section("analytics")
    layout.addStretch(1)

    scroll.setWidget(content)
    outer_layout.addWidget(scroll)
    window.tabs.addTab(tab, "Dashboard")
