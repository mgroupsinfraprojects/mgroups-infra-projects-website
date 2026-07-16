from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication, QTableView


@dataclass(frozen=True)
class DisplayProfile:
    widget_padding: int
    button_padding_y: int
    button_padding_x: int
    table_row_height: int
    border_radius: int


DENSITY_PROFILES = {
    "Compact": DisplayProfile(4, 6, 10, 24, 8),
    "Comfortable": DisplayProfile(6, 9, 15, 32, 12),
    "Large": DisplayProfile(8, 12, 20, 40, 14),
}

THEMES = {
    "System Default": {},
    "Professional Light": {
        "bg": "#F5F7FB",
        "panel": "#FFFFFF",
        "panel_alt": "#EEF2F7",
        "text": "#0F172A",
        "muted": "#64748B",
        "border": "#D7DEE8",
        "primary": "#2563EB",
        "primary_hover": "#1D4ED8",
        "header_bg": "#EAF1FF",
        "header_text": "#0F172A",
        "selection": "#DBEAFE",
        "summary_bg": "#FFFFFF",
        "summary_text": "#0F172A",
        "input_bg": "#FFFFFF",
        "sidebar_bg": "#0F172A",
        "sidebar_text": "#E5E7EB",
        "success": "#16A34A",
        "warning": "#D97706",
        "error": "#DC2626",
    },
    "Professional Dark": {
        "bg": "#0B1120",
        "panel": "#111827",
        "panel_alt": "#1E293B",
        "text": "#F8FAFC",
        "muted": "#94A3B8",
        "border": "#334155",
        "primary": "#3B82F6",
        "primary_hover": "#60A5FA",
        "header_bg": "#1E293B",
        "header_text": "#F8FAFC",
        "selection": "#1D4ED8",
        "summary_bg": "#111827",
        "summary_text": "#F8FAFC",
        "input_bg": "#0F172A",
        "sidebar_bg": "#020617",
        "sidebar_text": "#E2E8F0",
        "success": "#22C55E",
        "warning": "#F59E0B",
        "error": "#EF4444",
    },
    "Professional Blue": {
        "bg": "#EEF4FF",
        "panel": "#FFFFFF",
        "panel_alt": "#E0EDFF",
        "text": "#0F172A",
        "muted": "#475569",
        "border": "#B8C7DF",
        "primary": "#1D4ED8",
        "primary_hover": "#1E40AF",
        "header_bg": "#DBEAFE",
        "header_text": "#0F172A",
        "selection": "#BFDBFE",
        "summary_bg": "#FFFFFF",
        "summary_text": "#0F172A",
        "input_bg": "#FFFFFF",
        "sidebar_bg": "#0F2F66",
        "sidebar_text": "#FFFFFF",
        "success": "#15803D",
        "warning": "#B45309",
        "error": "#B91C1C",
    },
    "Audit High Contrast": {
        "bg": "#000000",
        "panel": "#101010",
        "panel_alt": "#1A1A1A",
        "text": "#FFFFFF",
        "muted": "#FFFFFF",
        "border": "#FFFFFF",
        "primary": "#FFCC00",
        "primary_hover": "#FFE066",
        "header_bg": "#FFFFFF",
        "header_text": "#000000",
        "selection": "#333300",
        "summary_bg": "#101010",
        "summary_text": "#FFFFFF",
        "input_bg": "#000000",
        "sidebar_bg": "#000000",
        "sidebar_text": "#FFFFFF",
        "success": "#00FF66",
        "warning": "#FFCC00",
        "error": "#FF4444",
    },
    "Custom Theme": {
        "bg": "#F5F7FB",
        "panel": "#FFFFFF",
        "panel_alt": "#EEF2FF",
        "text": "#111827",
        "muted": "#4B5563",
        "border": "#D1D5DB",
        "primary": "#2563EB",
        "primary_hover": "#1D4ED8",
        "header_bg": "#111827",
        "header_text": "#FFFFFF",
        "selection": "#DBEAFE",
        "summary_bg": "#FFFFFF",
        "summary_text": "#111827",
        "input_bg": "#FFFFFF",
        "sidebar_bg": "#0F172A",
        "sidebar_text": "#E5E7EB",
        "success": "#16A34A",
        "warning": "#D97706",
        "error": "#DC2626",
    },
}

DEFAULT_THEME = "Professional Dark"
DEFAULT_DENSITY = "Comfortable"
DEFAULT_FONT_SIZE = 10


def detect_system_theme_name() -> str:
    app = QApplication.instance()
    if app is None:
        return "Professional Light"
    palette = app.palette()
    try:
        window_role = QPalette.ColorRole.Window
    except AttributeError:
        window_role = QPalette.Window
    color = palette.color(window_role)
    return "Professional Dark" if color.lightness() < 128 else "Professional Light"


def resolve_theme_name(theme_name: str) -> str:
    return detect_system_theme_name() if theme_name == "System Default" else theme_name


def build_stylesheet(theme_name: str, font_size: int, density_name: str, custom_colors: dict[str, str] | None = None) -> str:
    theme_name = resolve_theme_name(theme_name)
    theme = dict(THEMES.get(theme_name, THEMES["Professional Light"]))
    if theme_name == "Custom Theme" and custom_colors:
        for key, value in custom_colors.items():
            if value:
                theme[key] = value
    density = DENSITY_PROFILES.get(density_name, DENSITY_PROFILES[DEFAULT_DENSITY])
    theme.setdefault("sidebar_bg", theme.get("header_bg", "#111827"))
    theme.setdefault("sidebar_text", theme.get("header_text", "#FFFFFF"))
    theme.setdefault("success", "#22C55E")
    theme.setdefault("warning", "#F59E0B")
    theme.setdefault("error", "#EF4444")
    return f"""
    QWidget {{
        font-family: "Segoe UI Variable", "Segoe UI", Arial, sans-serif;
        font-size: {font_size}pt;
        background: {theme['bg']};
        color: {theme['text']};
    }}
    QMainWindow {{ background: {theme['bg']}; }}
    QFrame#AppSidebar {{
        background: {theme['sidebar_bg']};
        border: 1px solid {theme['border']};
        border-radius: {density.border_radius + 8}px;
    }}
    QLabel#BrandTitle {{
        color: {theme['sidebar_text']};
        font-size: {font_size + 9}pt;
        font-weight: 800;
        background: transparent;
    }}
    QLabel#BrandSubtitle {{
        color: {theme['muted']};
        background: transparent;
        font-size: {font_size - 1}pt;
    }}
    QPushButton#NavButton {{
        background: transparent;
        color: {theme['sidebar_text']};
        border: 0px;
        border-radius: {density.border_radius + 2}px;
        padding: {density.button_padding_y + 4}px {density.button_padding_x}px;
        text-align: left;
        font-weight: 650;
    }}
    QPushButton#NavButton:hover {{ background: rgba(59, 130, 246, 0.20); }}
    QPushButton#NavButton:checked {{
        background: {theme['primary']};
        color: white;
        border-left: 4px solid white;
    }}
    QTabWidget::pane {{
        border: 1px solid {theme['border']};
        background: {theme['panel']};
        border-radius: {density.border_radius + 8}px;
    }}
    QPushButton {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {theme['primary']}, stop:1 {theme['primary_hover']});
        color: white;
        border: 1px solid {theme['primary']};
        border-radius: {density.border_radius + 1}px;
        padding: {density.button_padding_y + 2}px {density.button_padding_x + 5}px;
        font-weight: 800;
    }}
    QPushButton:hover {{ background: {theme['primary_hover']}; }}
    QPushButton:pressed {{ background: {theme['primary']}; }}
    QPushButton:disabled {{ background: {theme['border']}; color: {theme['muted']}; }}
    QLineEdit, QTextEdit, QComboBox, QSpinBox, QDateEdit, QTableWidget, QTableView {{
        background: {theme['input_bg']};
        color: {theme['text']};
        border: 1px solid {theme['border']};
        border-radius: {density.border_radius + 1}px;
        padding: {density.widget_padding + 2}px;
        selection-background-color: {theme['selection']};
    }}
    QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus, QDateEdit:focus {{
        border: 1px solid {theme['primary']};
    }}

    QScrollBar:vertical {{
        background: transparent;
        width: 10px;
        margin: 2px 2px 2px 2px;
        border: 0px;
    }}
    QScrollBar::handle:vertical {{
        background: #CBD5E1;
        border-radius: 5px;
        min-height: 42px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: #94A3B8;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
        border: 0px;
        background: transparent;
    }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        background: transparent;
    }}
    QScrollBar:horizontal {{
        background: transparent;
        height: 10px;
        margin: 2px 2px 2px 2px;
        border: 0px;
    }}
    QScrollBar::handle:horizontal {{
        background: #CBD5E1;
        border-radius: 5px;
        min-width: 42px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: #94A3B8;
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0px;
        border: 0px;
        background: transparent;
    }}
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
        background: transparent;
    }}
    QPushButton#ModernComboButton {{
        background: {theme['input_bg']};
        color: {theme['text']};
        border: 1px solid {theme['border']};
        border-radius: {density.border_radius + 1}px;
        padding: {density.widget_padding + 2}px 12px;
        text-align: left;
        font-weight: 650;
    }}
    QPushButton#ModernComboButton:hover {{
        border: 1px solid {theme['primary']};
        background: {theme['panel']};
    }}
    QFrame#ModernComboPopup {{
        background: {theme['panel']};
        border: 1px solid {theme['border']};
        border-radius: {density.border_radius + 8}px;
    }}
    QFrame#ModernComboRow {{
        background: {theme['panel']};
        border: 1px solid transparent;
        border-radius: {density.border_radius + 4}px;
    }}
    QFrame#ModernComboRow:hover {{
        background: #F8FAFC;
        border: 1px solid #DBEAFE;
    }}
    QFrame#ModernComboRow[selected="true"] {{
        background: #EFF6FF;
        border: 1px solid #BFDBFE;
    }}
    QLabel#ModernComboRowText {{
        color: {theme['text']};
        font-weight: 650;
    }}
    QLabel#ModernComboCheck {{
        color: {theme['primary']};
        font-weight: 900;
    }}
    QComboBox QAbstractItemView {{
        background: {theme['panel']};
        color: {theme['text']};
        selection-background-color: {theme['selection']};
    }}
    QTableWidget, QTableView {{
        background: {theme['panel']};
        border: 1px solid {theme['border']};
        gridline-color: {theme['panel_alt']};
        alternate-background-color: {theme['summary_bg']};
        border-radius: {density.border_radius + 6}px;
        outline: 0;
    }}
    QTableWidget::item, QTableView::item {{
        padding: {density.widget_padding + 7}px;
        border-bottom: 1px solid {theme['panel_alt']};
    }}
    QTableWidget::item:hover, QTableView::item:hover {{
        background: {theme['summary_bg']};
    }}
    QTableWidget::item:selected, QTableView::item:selected {{
        background: {theme['selection']};
        color: {theme['text']};
    }}
    QTableCornerButton::section {{
        background: {theme['header_bg']};
        border: 0px;
    }}
    QHeaderView::section {{
        background: #EAF2FF;
        color: {theme['text']};
        padding: {density.widget_padding + 5}px;
        border: 0px;
        border-bottom: 1px solid {theme['border']};
        font-weight: 800;
    }}
    QLabel {{ color: {theme['text']}; background: transparent; }}
    QLabel#PageTitle {{
        font-size: {font_size + 13}pt;
        font-weight: 850;
        color: {theme['text']};
    }}
    QLabel#SectionTitle {{
        font-size: {font_size + 4}pt;
        font-weight: 800;
        color: {theme['text']};
    }}
    QLabel#MutedText {{ color: {theme['muted']}; }}
    QLabel#SummaryCards, QFrame#EmptyState {{
        background: {theme['summary_bg']};
        color: {theme['summary_text']};
        border: 1px solid {theme['border']};
        border-radius: {density.border_radius + 8}px;
        padding: {density.widget_padding + 10}px;
        font-size: {font_size + 1}pt;
        font-weight: 650;
    }}
    QFrame#MetricCard {{
        background: {theme['panel']};
        border: 1px solid {theme['border']};
        border-radius: {density.border_radius + 12}px;
    }}
    QFrame#MetricCard:hover {{
        border: 1px solid {theme['primary']};
        background: {theme['panel_alt']};
    }}
    QScrollArea#DashboardScrollArea {{
        background: {theme['bg']};
        border: 0px;
    }}
    QWidget#DashboardContent {{
        background: {theme['bg']};
    }}
    QFrame#ChartsSection {{
        background: transparent;
        border: 0px;
    }}
    QSplitter#DashboardDrilldownSplitter {{
        background: transparent;
        border: 0px;
    }}
    QFrame#DashboardFilterPanel, QFrame#AuditStatusPanel, QFrame#NextActionCard, QGroupBox#SettingsSection {{
        background: {theme['panel']};
        border: 1px solid {theme['border']};
        border-radius: {density.border_radius + 12}px;
        margin-top: 10px;
        font-weight: 800;
    }}
    QGroupBox#SettingsSection::title {{
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 8px;
        color: {theme['primary']};
        background: {theme['panel']};
    }}
    QScrollArea#SettingsScrollArea, QWidget#SettingsContent {{
        background: {theme['bg']};
        border: 0px;
    }}
    QFrame#NextActionCard {{
        border-left: 5px solid {theme['primary']};
    }}
    QLabel#SummaryTextInline {{
        color: {theme['text']};
        font-weight: 650;
        background: transparent;
    }}
    QLabel#ActiveFilterChips {{
        background: {theme['panel']};
        color: {theme['text']};
        border: 1px solid {theme['border']};
        border-radius: {density.border_radius + 5}px;
        padding: 7px 10px;
        font-weight: 650;
    }}
    QLabel#ModeHelpText {{
        background: {theme['panel']};
        color: {theme['text']};
        border: 1px solid {theme['border']};
        border-radius: {density.border_radius + 6}px;
        padding: 7px 10px;
        font-weight: 650;
    }}

    QFrame#GuidedSelectCard {{
        background: {theme['summary_bg']};
        border: 1px solid {theme['border']};
        border-radius: {density.border_radius + 10}px;
    }}
    QFrame#CompactSearchSelector {{
        background: transparent;
        border: 0px;
    }}
    QLabel#CompactFilterStatus {{
        color: {theme['muted']};
        font-size: {font_size - 2}pt;
        font-weight: 650;
        padding-left: 2px;
    }}
    QFrame#GuidedValueBox {{
        background: {theme['input_bg']};
        border: 1px solid {theme['border']};
        border-radius: {density.border_radius + 4}px;
    }}
    QFrame#GuidedValueBox[focused="true"] {{
        background: {theme['panel']};
        border: 1px solid {theme['primary']};
    }}
    QLineEdit#GuidedSearchInput {{
        background: transparent;
        color: {theme['text']};
        border: 0px;
        border-radius: 0px;
        padding: 0px 10px;
        font-weight: 650;
        selection-background-color: {theme['selection']};
    }}
    QLineEdit#GuidedSearchInput:focus {{
        border: 0px;
        background: transparent;
    }}
    QDialog#FilterPopupPanel {{
        background: {theme['panel']};
        border: 1px solid #BBD0F6;
        border-radius: {density.border_radius + 10}px;
    }}
    QLineEdit#FilterPopupSearch {{
        background: {theme['summary_bg']};
        border: 1px solid {theme['border']};
        border-radius: {density.border_radius + 6}px;
        padding: 8px 12px;
        font-weight: 650;
    }}
    QLineEdit#FilterPopupSearch:focus {{
        border: 1px solid {theme['primary']};
        background: {theme['panel']};
    }}
    QFrame#FilterPopupActionRow {{
        background: #F8FBFF;
        border: 1px solid {theme['border']};
        border-radius: {density.border_radius + 6}px;
    }}
    QFrame#FilterPopupFooter {{
        background: {theme['panel']};
        border-top: 1px solid {theme['border']};
        border-left: 0px;
        border-right: 0px;
        border-bottom: 0px;
    }}
    QScrollArea#FilterPopupScroll {{
        background: {theme['panel']};
        border: 0px;
    }}
    QScrollArea#FilterPopupScroll > QWidget,
    QScrollArea#FilterPopupScroll QWidget#qt_scrollarea_viewport,
    QWidget#FilterPopupScrollContent {{
        background: {theme['panel']};
        border: 0px;
    }}
    QFrame#FilterOptionRow {{
        background: {theme['panel']};
        border: 1px solid {theme['border']};
        border-radius: {density.border_radius + 6}px;
    }}
    QFrame#FilterOptionRow:hover {{
        background: {theme['summary_bg']};
        border: 1px solid {theme['primary']};
    }}
    QFrame#FilterOptionRow[focused="true"] {{
        background: #EFF6FF;
        border: 1px solid {theme['primary']};
    }}
    QFrame#FilterOptionRow[checked="true"] {{
        background: #F8FBFF;
        border: 1px solid #93C5FD;
    }}
    QCheckBox#FilterOptionCheckbox::indicator {{
        width: 18px;
        height: 18px;
        border: 1px solid {theme['border']};
        border-radius: 6px;
        background: {theme['panel']};
    }}
    QCheckBox#FilterOptionCheckbox::indicator:checked {{
        border-color: {theme['primary']};
        background: {theme['primary']};
    }}
    QLabel#FilterOptionName {{
        color: {theme['text']};
        font-weight: 650;
        background: transparent;
    }}
    QLabel#FilterPopupGroupLabel {{
        color: {theme['muted']};
        background: transparent;
        padding: 6px 4px 2px 4px;
        font-size: {font_size - 3}pt;
        font-weight: 850;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }}
    QLabel#FilterOptionCount, QLabel#FilterPopupCount {{
        color: {theme['muted']};
        background: {theme['panel']};
        border: 1px solid {theme['border']};
        border-radius: 9999px;
        padding: 3px 8px;
        font-size: {font_size - 3}pt;
        font-weight: 750;
    }}
    QLabel#FilterPopupStatus {{
        color: {theme['muted']};
        font-weight: 750;
    }}
    QLabel#FilterPopupEmpty {{
        color: {theme['muted']};
        background: #F8FBFF;
        border: 1px dashed {theme['border']};
        border-radius: {density.border_radius + 6}px;
        padding: 14px 12px;
        font-weight: 650;
    }}
    QFrame#InlineSuggestionPopup {{
        background: {theme['panel']};
        border: 1px solid {theme['primary']};
        border-radius: {density.border_radius + 8}px;
    }}
    QListWidget#InlineSuggestionList {{
        background: {theme['panel']};
        border: 0px;
        outline: 0px;
        font-weight: 650;
    }}
    QListWidget#InlineSuggestionList::item {{
        padding: 8px 10px;
        border-radius: {density.border_radius + 4}px;
    }}
    QListWidget#InlineSuggestionList::item:hover,
    QListWidget#InlineSuggestionList::item:selected {{
        background: {theme['selection']};
        color: {theme['primary']};
    }}
    QPushButton#SuggestionOpenFullButton {{
        background: {theme['summary_bg']};
        color: {theme['primary']};
        border: 1px solid {theme['border']};
        border-radius: {density.border_radius + 4}px;
        padding: 8px 12px;
        font-size: {font_size - 1}pt;
        font-weight: 800;
    }}
    QPushButton#SuggestionOpenFullButton:hover {{
        border: 1px solid {theme['primary']};
        background: {theme['selection']};
    }}
    QPushButton#FilterPopupGhostButton {{
        background: {theme['panel']};
        color: {theme['text']};
        border: 1px solid {theme['border']};
        border-radius: {density.border_radius + 4}px;
        padding: 8px 14px;
        font-size: {font_size - 1}pt;
        font-weight: 800;
        min-width: 72px;
    }}
    QPushButton#FilterPopupApplyButton {{
        background: {theme['primary']};
        color: white;
        border: 1px solid {theme['primary']};
        border-radius: {density.border_radius + 4}px;
        padding: 8px 14px;
        font-size: {font_size - 1}pt;
        font-weight: 800;
        min-width: 72px;
    }}
    QPushButton#FilterPopupGhostButton:hover {{
        border: 1px solid {theme['primary']};
        color: {theme['primary']};
    }}
    QPushButton#FilterPopupApplyButton:hover {{
        background: {theme['primary_hover']};
        border: 1px solid {theme['primary_hover']};
    }}
    QPushButton#PickerDropButton {{
        background: transparent;
        color: {theme['text']};
        border: 0px;
        border-left: 1px solid {theme['border']};
        border-radius: 0px;
        padding: 0px;
        font-size: {font_size + 1}pt;
        font-weight: 850;
        min-width: 36px;
        max-width: 38px;
    }}
    QPushButton#PickerDropButton:hover {{
        background: {theme['selection']};
        border-left: 1px solid #BFDBFE;
        color: {theme['primary']};
    }}
    QPushButton#PickerDropButton:pressed {{
        background: #DBEAFE;
        color: {theme['primary']};
    }}
    QListWidget#GuidedSuggestionList {{
        background: {theme['panel']};
        border: 1px solid {theme['border']};
        border-radius: {density.border_radius + 4}px;
        padding: 4px;
        outline: 0px;
    }}
    QListWidget#GuidedSuggestionList::item {{
        padding: 7px 6px;
        border-radius: {density.border_radius + 2}px;
    }}
    QListWidget#GuidedSuggestionList::item:hover {{
        background: {theme['selection']};
    }}
    QPushButton#MiniActionButton {{
        background: {theme['panel']};
        color: {theme['text']};
        border: 1px solid {theme['border']};
        border-radius: 9999px;
        padding: 5px 10px;
        font-size: {font_size - 2}pt;
        font-weight: 800;
        min-height: 20px;
    }}
    QPushButton#MiniActionButton:hover {{
        border: 1px solid {theme['primary']};
        color: {theme['primary']};
    }}
    QPushButton#SelectedFilterChip {{
        background: #EFF6FF;
        color: {theme['primary']};
        border: 1px solid #BFDBFE;
        border-radius: 9999px;
        padding: 3px 8px;
        font-size: {font_size - 2}pt;
        font-weight: 800;
        min-height: 18px;
    }}
    QPushButton#SelectedFilterChip:hover {{
        background: #DBEAFE;
        border: 1px solid {theme['primary']};
    }}
    QLabel#EmptyChipHint {{
        color: {theme['muted']};
        font-size: {font_size - 2}pt;
        font-weight: 650;
    }}

    QFrame#QuickAccessPanel {{
        background: {theme['summary_bg']};
        border: 1px solid {theme['border']};
        border-radius: {density.border_radius + 8}px;
    }}
    QLabel#TinyLabel {{
        color: {theme['muted']};
        font-size: {font_size - 1}pt;
        font-weight: 850;
        letter-spacing: 0.04em;
        min-width: 82px;
    }}
    QScrollArea#ChipScroll {{
        background: transparent;
        border: 0px;
    }}
    QWidget#ChipBar {{
        background: transparent;
        border: 0px;
    }}
    QPushButton#QuickFilterChip {{
        background: {theme['panel']};
        color: {theme['text']};
        border: 1px solid {theme['border']};
        border-radius: 9999px;
        padding: 5px 10px;
        font-weight: 750;
        min-height: 20px;
    }}
    QPushButton#QuickFilterChip:hover {{
        border: 1px solid {theme['primary']};
        background: {theme['summary_bg']};
    }}
    QPushButton#QuickFilterChip:checked {{
        background: {theme['primary']};
        color: white;
        border: 1px solid {theme['primary']};
    }}

    QWidget#DashboardFilterBody {{
        background: {theme['summary_bg']};
        border: 1px solid {theme['border']};
        border-radius: {density.border_radius + 8}px;
    }}
    QTextEdit#DashboardDetailPanel, QTextBrowser#DashboardDetailPanel {{
        background: {theme['panel']};
        border: 1px solid {theme['border']};
        border-radius: {density.border_radius + 8}px;
        padding: {density.widget_padding + 8}px;
        font-family: "Segoe UI", Consolas, monospace;
    }}
    QLabel#MetricLabel {{ color: {theme['muted']}; font-size: {font_size}pt; font-weight: 750; }}
    QLabel#MetricValue {{ color: {theme['text']}; font-size: {font_size + 12}pt; font-weight: 900; }}
    QLabel#MetricSubtext {{ color: {theme['muted']}; font-size: {font_size - 1}pt; }}
    QLabel#MetricDelta {{ color: {theme['success']}; font-size: {font_size - 1}pt; font-weight: 850; }}
    QFrame#UploadCard {{
        background: {theme['panel']};
        border: 2px dashed {theme['primary']};
        border-radius: {density.border_radius + 10}px;
    }}
    QLabel#UploadTitle {{
        color: {theme['text']};
        font-size: {font_size + 7}pt;
        font-weight: 850;
    }}
    QFrame#DetailPanel {{
        background: {theme['panel']};
        border: 1px solid {theme['border']};
        border-radius: {density.border_radius + 8}px;
    }}
    QLabel#StatusChip {{
        border-radius: 9999px;
        padding: 6px 16px;
        font-weight: 850;
        background: {theme['panel_alt']};
        color: {theme['text']};
        border: 1px solid {theme['border']};
    }}
    QLabel#StatusChip[variant="success"] {{ background: {theme['success']}; color: white; border: 1px solid {theme['success']}; }}
    QLabel#StatusChip[variant="warning"] {{ background: {theme['warning']}; color: #111827; border: 1px solid {theme['warning']}; }}
    QLabel#StatusChip[variant="error"], QLabel#StatusChip[variant="danger"] {{ background: {theme['error']}; color: white; border: 1px solid {theme['error']}; }}
    QLabel#StatusChip[variant="info"] {{ background: {theme['primary']}; color: white; border: 1px solid {theme['primary']}; }}
    QLabel#StatusChip[variant="neutral"] {{ background: {theme['panel_alt']}; color: {theme['text']}; border: 1px solid {theme['border']}; }}
    QLabel#Toast {{
        background: {theme['primary']};
        color: white;
        border-radius: {density.border_radius + 4}px;
        padding: 10px 14px;
        font-weight: 800;
    }}

    QFrame#ReconciliationCard {{
        background: {theme['panel']};
        border: 1px solid {theme['border']};
        border-radius: {density.border_radius + 8}px;
    }}
    QPushButton#SecondaryButton, QPushButton#LinkButton, QPushButton#DangerOutlineButton {{
        background: {theme['panel']};
        color: {theme['text']};
        border: 1px solid {theme['border']};
        border-radius: {density.border_radius + 1}px;
        padding: {density.button_padding_y + 2}px {density.button_padding_x + 5}px;
        font-weight: 800;
    }}
    QPushButton#SecondaryButton:hover, QPushButton#LinkButton:hover {{
        border: 1px solid {theme['primary']};
        color: {theme['primary']};
        background: {theme['selection']};
    }}
    QPushButton#DangerOutlineButton {{
        color: {theme['error']};
        border: 1px solid {theme['error']};
    }}
    QPushButton#DangerOutlineButton:hover {{
        background: {theme['error']};
        color: white;
    }}
    QPushButton#PrimaryActionButton {{
        font-weight: 900;
        min-height: 34px;
    }}
    QDialog#BulkReviewDialog {{
        background: {theme['panel']};
        color: {theme['text']};
    }}
    QRadioButton {{
        background: transparent;
        color: {theme['text']};
        font-weight: 650;
        padding: 4px;
    }}
    QFrame#LoadingOverlay {{
        background: rgba(15, 23, 42, 0.88);
        border-radius: {density.border_radius + 8}px;
    }}
    """


def apply_theme(theme_name: str, font_size: int, density_name: str, custom_colors: dict[str, str] | None = None) -> None:
    app = QApplication.instance()
    if app is not None:
        app.setStyleSheet(build_stylesheet(theme_name, font_size, density_name, custom_colors=custom_colors))


def table_row_height(density_name: str) -> int:
    density = DENSITY_PROFILES.get(density_name, DENSITY_PROFILES[DEFAULT_DENSITY])
    return density.table_row_height


def apply_table_display(table: QTableView, density_name: str) -> None:
    table.setAlternatingRowColors(True)
    table.verticalHeader().setDefaultSectionSize(table_row_height(density_name))
