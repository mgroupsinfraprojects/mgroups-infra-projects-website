# Compatibility labels: config/app_identity.json | Application Identity & Navigation | Theme & Display Settings | Audit Rules & GSTIN Lists
from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.core.branding import DEFAULT_NAVIGATION_LABELS
from app.core.review_thresholds import load_review_thresholds
from app.ui.theme_manager import DEFAULT_DENSITY, DEFAULT_FONT_SIZE, DEFAULT_THEME, THEMES


WINDOW_SIZE_OPTIONS = [
    "Compact 1280 x 720",
    "Normal 1366 x 768",
    "Large 1440 x 850",
    "Wide 1600 x 900",
    "Fit screen",
]


def _section(title: str, help_text: str | None = None) -> QGroupBox:
    box = QGroupBox(title)
    box.setObjectName("SettingsSection")
    layout = QVBoxLayout(box)
    layout.setContentsMargins(14, 18, 14, 14)
    layout.setSpacing(10)
    if help_text:
        note = QLabel(help_text)
        note.setObjectName("MutedText")
        note.setWordWrap(True)
        layout.addWidget(note)
    return box


def _page() -> tuple[QWidget, QVBoxLayout]:
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(14, 14, 14, 14)
    layout.setSpacing(12)
    return page, layout


def _add_branding_controls(window, layout: QVBoxLayout) -> None:
    box = _section(
        "Company / Navigation Names",
        "Change company branding and sidebar labels. These values are saved locally and apply immediately.",
    )
    form = QFormLayout()
    branding = window.branding
    window.app_name_edit = QLineEdit(branding.app_name)
    window.window_title_edit = QLineEdit(branding.window_title)
    window.sidebar_title_edit = QLineEdit(branding.sidebar_title)
    window.sidebar_subtitle_edit = QLineEdit(branding.sidebar_subtitle)
    form.addRow("Software short name", window.app_name_edit)
    form.addRow("Window title", window.window_title_edit)
    form.addRow("Sidebar title", window.sidebar_title_edit)
    form.addRow("Sidebar subtitle", window.sidebar_subtitle_edit)
    box.layout().addLayout(form)

    nav_grid = QGridLayout()
    nav_grid.setHorizontalSpacing(10)
    nav_grid.setVerticalSpacing(8)
    window.navigation_label_edits = {}
    for row, key in enumerate(DEFAULT_NAVIGATION_LABELS):
        label = QLabel(key.replace("_", " ").title())
        edit = QLineEdit(branding.nav_label(key))
        edit.setPlaceholderText(DEFAULT_NAVIGATION_LABELS[key])
        window.navigation_label_edits[key] = edit
        nav_grid.addWidget(label, row // 2, (row % 2) * 2)
        nav_grid.addWidget(edit, row // 2, (row % 2) * 2 + 1)
    box.layout().addLayout(nav_grid)
    layout.addWidget(box)


def _add_theme_controls(window, layout: QVBoxLayout) -> None:
    box = _section(
        "Appearance",
        "Use safe professional presets. Background, cards, sidebar, and text are controlled together so the interface does not become unreadable.",
    )
    preset_note = QLabel(
        "Recommended: Professional Dark or Professional Light. Use Custom Brand only for a controlled accent colour, not separate random colours."
    )
    preset_note.setObjectName("SummaryCards")
    preset_note.setWordWrap(True)
    box.layout().addWidget(preset_note)

    form = QFormLayout()
    window.theme_combo = QComboBox()
    safe_themes = ["Professional Dark", "Professional Light", "Professional Blue", "Audit High Contrast", "Custom Theme"]
    window.theme_combo.addItems([theme for theme in safe_themes if theme in THEMES])
    saved_theme = window.settings.value("display/theme", DEFAULT_THEME, type=str)
    window.theme_combo.setCurrentText(saved_theme if saved_theme in safe_themes else DEFAULT_THEME)
    window.font_size_spin = QSpinBox()
    window.font_size_spin.setRange(10, 18)
    window.font_size_spin.setSingleStep(1)
    window.font_size_spin.setValue(max(10, window.settings.value("display/font_size", DEFAULT_FONT_SIZE, type=int)))
    window.density_combo = QComboBox()
    window.density_combo.addItems(["Compact", "Comfortable", "Large"])
    window.density_combo.setCurrentText(window.settings.value("display/density", DEFAULT_DENSITY, type=str))
    window.window_size_combo = QComboBox()
    window.window_size_combo.addItems(WINDOW_SIZE_OPTIONS)
    window.window_size_combo.setCurrentText(window.settings.value("display/window_size", "Normal 1366 x 768", type=str) or "Normal 1366 x 768")

    # Hidden technical fields remain for compatibility, but only safe accent pickers are shown.
    window.primary_color_edit = QLineEdit(window.settings.value("display/custom_primary", "#2563eb", type=str))
    window.sidebar_color_edit = QLineEdit(window.settings.value("display/custom_sidebar", "#0f172a", type=str))
    window.background_color_edit = QLineEdit(window.settings.value("display/custom_background", "#f5f7fb", type=str))
    window.card_color_edit = QLineEdit(window.settings.value("display/custom_card", "#ffffff", type=str))
    window.text_color_edit = QLineEdit(window.settings.value("display/custom_text", "#111827", type=str))
    for hidden in [window.background_color_edit, window.card_color_edit, window.text_color_edit]:
        hidden.setVisible(False)

    form.addRow("Theme preset", window.theme_combo)
    form.addRow("Font size", window.font_size_spin)
    form.addRow("Display density", window.density_combo)
    form.addRow("Window size", window.window_size_combo)
    form.addRow("Brand accent", window._color_row(window.primary_color_edit))
    form.addRow("Sidebar accent", window._color_row(window.sidebar_color_edit))
    box.layout().addLayout(form)
    layout.addWidget(box)


def _add_feature_controls(window, layout: QVBoxLayout) -> None:
    box = _section(
        "Feature Visibility / Admin Permissions",
        "Admin can show/hide main modules and choose which sub-features are visible to users. Start and Settings always remain visible.",
    )
    window.feature_visibility_checks = {}
    window.feature_option_checks = {}
    feature_rows = [
        ("dashboard", "Dashboard", ["Search panel", "Totals cards", "Charts", "Supplier drill-down", "Hide fix section"]),
        ("review", "Fix Issues", ["GST/value errors", "Missing GSTIN/date/invoice", "Duplicate tab", "Edit row", "Approve button", "Reject button", "Ignore button"]),
        ("suppliers", "Suppliers", ["Supplier search suggestions", "Multi-select suppliers", "Invoice-level details", "High-value supplier filter"]),
        ("reconciliation", "Proof", ["Row coverage proof", "Amount cross-check", "Technical details", "GSTR-2A/2B import"]),
        ("exports", "Export", ["Draft report", "Final report", "Excel evidence", "Quality gate summary"]),
    ]
    for key, title, options in feature_rows:
        feature_box = QGroupBox(title)
        feature_box.setObjectName("SettingsSubSection")
        feature_layout = QVBoxLayout(feature_box)
        feature_layout.setContentsMargins(12, 14, 12, 12)
        main_check = QCheckBox(f"Show {title} in sidebar")
        main_check.setChecked(window.settings.value(f"features/{key}", True, type=bool))
        window.feature_visibility_checks[key] = main_check
        feature_layout.addWidget(main_check)
        hint = QLabel("Recommended: keep enabled for normal audit workflow." if key in {"dashboard", "review", "exports"} else "Optional support module; hide if not needed by the user role.")
        hint.setObjectName("MutedText")
        hint.setWordWrap(True)
        feature_layout.addWidget(hint)
        for option in options:
            opt_key = f"{key}/{option.lower().replace(' ', '_').replace('/', '_')}"
            opt_check = QCheckBox(option)
            opt_check.setChecked(window.settings.value(f"feature_options/{opt_key}", True, type=bool))
            window.feature_option_checks[opt_key] = opt_check
            feature_layout.addWidget(opt_check)
        box.layout().addWidget(feature_box)
    layout.addWidget(box)


def _add_audit_controls(window, layout: QVBoxLayout) -> None:
    box = _section(
        "Audit Rules / Review Thresholds",
        "Control what becomes a real review item. Small amount differences stay trace-only unless identity, date, invoice, GSTIN, or duplicate rules fail.",
    )
    thresholds = load_review_thresholds()
    threshold_form = QFormLayout()
    window.critical_amount_spin = QSpinBox()
    window.critical_amount_spin.setRange(0, 10000000)
    window.critical_amount_spin.setSingleStep(100)
    window.critical_amount_spin.setValue(int(thresholds["critical_amount"]))
    window.advisory_amount_spin = QSpinBox()
    window.advisory_amount_spin.setRange(0, 10000000)
    window.advisory_amount_spin.setSingleStep(50)
    window.advisory_amount_spin.setValue(int(thresholds["advisory_amount"]))
    window.ignore_amount_spin = QSpinBox()
    window.ignore_amount_spin.setRange(0, 1000000)
    window.ignore_amount_spin.setSingleStep(10)
    window.ignore_amount_spin.setValue(int(thresholds["ignore_amount"]))
    window.critical_percent_spin = QSpinBox()
    window.critical_percent_spin.setRange(0, 100)
    window.critical_percent_spin.setSingleStep(1)
    window.critical_percent_spin.setValue(int(thresholds["critical_percent"]))
    window.gst_critical_amount_spin = QSpinBox()
    window.gst_critical_amount_spin.setRange(0, 10000000)
    window.gst_critical_amount_spin.setSingleStep(50)
    window.gst_critical_amount_spin.setValue(int(thresholds.get("gst_critical_amount", thresholds["critical_amount"])))
    window.duplicate_min_amount_spin = QSpinBox()
    window.duplicate_min_amount_spin.setRange(0, 10000000)
    window.duplicate_min_amount_spin.setSingleStep(100)
    window.duplicate_min_amount_spin.setValue(int(thresholds.get("duplicate_min_amount", 100)))
    window.high_value_supplier_spin = QSpinBox()
    window.high_value_supplier_spin.setRange(0, 100000000)
    window.high_value_supplier_spin.setSingleStep(10000)
    window.high_value_supplier_spin.setValue(int(thresholds["high_value_supplier"]))
    threshold_form.addRow("Critical invoice-value difference ≥ ₹", window.critical_amount_spin)
    threshold_form.addRow("Advisory difference starts at ₹", window.advisory_amount_spin)
    threshold_form.addRow("Ignore tiny difference below ₹", window.ignore_amount_spin)
    threshold_form.addRow("Critical GST component difference ≥ ₹", window.gst_critical_amount_spin)
    threshold_form.addRow("Duplicate review minimum value ≥ ₹", window.duplicate_min_amount_spin)
    threshold_form.addRow("Critical percentage difference ≥ %", window.critical_percent_spin)
    threshold_form.addRow("High-value supplier threshold ₹", window.high_value_supplier_spin)
    box.layout().addLayout(threshold_form)
    threshold_note = QLabel(
        "Only real important rows go to Fix Issues. Always reviewed: GSTIN error, supplier missing, invoice/date missing, large value/GST difference above range, and meaningful duplicate supplier invoice."
    )
    threshold_note.setObjectName("MutedText")
    threshold_note.setWordWrap(True)
    box.layout().addWidget(threshold_note)

    window.ignored_gstins_edit = QTextEdit()
    window.ignored_gstins_edit.setMinimumHeight(100)
    window.ignored_gstins_edit.setPlaceholderText("Optional: one GSTIN per line to exclude from dashboard totals.")
    window.ignored_gstins_edit.setPlainText(window.settings.value("audit/ignored_gstins", "", type=str))
    window.self_gstins_edit = QTextEdit()
    window.self_gstins_edit.setMinimumHeight(100)
    window.self_gstins_edit.setPlaceholderText("Optional: your own GSTIN(s), one per line.")
    window.self_gstins_edit.setPlainText(window.settings.value("audit/self_gstins", "", type=str))
    box.layout().addWidget(QLabel("Ignored GSTINs / Exclusion List"))
    box.layout().addWidget(window.ignored_gstins_edit)
    box.layout().addWidget(QLabel("Your GSTINs / Self-Invoice Detection"))
    box.layout().addWidget(window.self_gstins_edit)
    layout.addWidget(box)


def build_settings_tab(window) -> None:
    tab = QWidget()
    root = QVBoxLayout(tab)
    root.setContentsMargins(18, 18, 18, 18)
    root.setSpacing(12)
    title = QLabel("Admin Settings")
    title.setObjectName("PageTitle")
    note = QLabel("Configure branding, appearance, visible features, and audit rules without changing Python code.")
    note.setObjectName("MutedText")
    note.setWordWrap(True)
    root.addWidget(title)
    root.addWidget(note)

    tabs = QTabWidget()
    tabs.setObjectName("SettingsTabs")
    general, general_layout = _page()
    interface, interface_layout = _page()
    features, features_layout = _page()
    rules, rules_layout = _page()
    _add_branding_controls(window, general_layout)
    _add_theme_controls(window, interface_layout)
    _add_feature_controls(window, features_layout)
    _add_audit_controls(window, rules_layout)
    for layout in [general_layout, interface_layout, features_layout, rules_layout]:
        layout.addStretch(1)
    tabs.addTab(general, "Branding")
    tabs.addTab(interface, "Appearance")
    tabs.addTab(features, "Features")
    tabs.addTab(rules, "Audit Rules")
    root.addWidget(tabs, 1)

    btn_row = QHBoxLayout()
    apply_btn = QPushButton("Apply Settings")
    apply_btn.setObjectName("PrimaryActionButton")
    reset_btn = QPushButton("Reset Default")
    reset_btn.setObjectName("SecondaryButton")
    apply_btn.clicked.connect(lambda: window.apply_display_settings(save=True))
    reset_btn.clicked.connect(window.reset_display_settings)
    btn_row.addWidget(apply_btn)
    btn_row.addWidget(reset_btn)
    btn_row.addStretch(1)
    root.addLayout(btn_row)
    window.tabs.addTab(tab, window.branding.nav_label("settings"))
