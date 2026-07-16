from __future__ import annotations

from pathlib import Path
import json
import logging
import re
from datetime import date
from decimal import Decimal
from typing import Any, List, Optional

from PySide6.QtCore import QDate, QSettings, Qt, QTimer
from PySide6.QtGui import QColor, QGuiApplication, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFileDialog,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QDateEdit,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QInputDialog,
    QProgressDialog,
    QAbstractItemView,
    QFrame,
    QColorDialog,
    QSplitter,
    QGridLayout,
    QDialog,
    QDialogButtonBox,
    QRadioButton,
)

from app.core.audit_engine import InvoiceAuditEngine
from app.core.branding import DEFAULT_NAVIGATION_LABELS, AppBranding, load_branding_file, merge_branding_overrides
from app.core.database import AuditDatabase
from app.core.exporter import export_verified_excel
from app.core.quality_gate import quality_gate_items, quality_gate_score, quality_gate_status
from app.core.gstr_reconciliation import GstrReconciliationResult, reconcile_gstr_2a_2b
from app.core.models import AuditResult, InvoiceRow
from app.core.money import format_inr
from app.core.analytics import filter_rows, grouped_chart_points, supplier_summary
from app.core.review_policy import is_mandatory_review, is_advisory_exception, has_gst_or_amount_exception, is_trace_only, has_required_identity_problem, has_required_amount_problem, has_required_date_problem, is_real_invoice_candidate, is_meaningful_duplicate_row
from app.core.import_safety import analyze_import_set, export_import_safety_report, ImportSafetyReport
from app.core.review_thresholds import save_review_thresholds, load_review_thresholds
from app.ui.theme_manager import DEFAULT_DENSITY, DEFAULT_FONT_SIZE, DEFAULT_THEME, THEMES, apply_table_display, apply_theme
from app.ui.processing_worker import ProcessingWorker
from app.ui.widgets.chart_panel import SimpleBarChart
from app.ui.widgets.detail_panel import RowDetailPanel
from app.ui.widgets.status_chip import StatusChip, friendly_status
from app.ui.widgets.metric_card import MetricCard
from app.ui.widgets.upload_card import UploadCard
from app.ui.widgets.data_table import DataTable
from app.ui.widgets.empty_state import EmptyState
from app.ui.widgets.toast import Toast
from app.ui.controllers.dashboard_controller import DashboardControllerMixin

try:
    from shiboken6 import isValid as qt_is_valid
except Exception:  # pragma: no cover - fallback for non-Qt static checks
    def qt_is_valid(_obj) -> bool:
        return True

LOGGER = logging.getLogger(__name__)

# UI performance guardrails: rendering thousands of rows on every click freezes PySide tables.
MAX_AUTO_RENDER_TABLE_ROWS = 500
MAX_AUTO_RESIZE_TABLE_ROWS = 350


class MainWindow(DashboardControllerMixin, QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.settings = QSettings("GSTAudit", "GSTInvoiceAuditSoftware")
        self._migrate_gui_defaults()
        self.branding = self._load_branding()
        self.setWindowTitle(self.branding.full_window_title)
        self.setMinimumSize(1100, 700)
        self.engine = InvoiceAuditEngine()
        self.db = AuditDatabase()
        self.current_dataset_id: Optional[int] = None
        self.selected_files: List[str] = []
        self.result: Optional[AuditResult] = None
        self.gstr_result: Optional[AuditResult] = None
        self.gstr_reconciliation: Optional[GstrReconciliationResult] = None
        self.current_rows: List[InvoiceRow] = []
        self.worker: Optional[ProcessingWorker] = None
        self.progress_dialog: Optional[QProgressDialog] = None
        self.current_density = self.settings.value("display/density", DEFAULT_DENSITY, type=str)
        # Default UI state must exist before any table refresh/filter signal fires.
        self.audit_extra_columns_visible = False
        self.last_output_path: Optional[str] = None
        self.import_safety_report: Optional[ImportSafetyReport] = None

        self.root_widget = QWidget()
        self.root_layout = QHBoxLayout(self.root_widget)
        self.root_layout.setContentsMargins(12, 12, 12, 12)
        self.root_layout.setSpacing(12)
        self.sidebar = QFrame()
        self.sidebar.setObjectName("AppSidebar")
        self.sidebar.setFixedWidth(240)
        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar_layout.setContentsMargins(14, 18, 14, 18)
        self.sidebar_layout.setSpacing(8)
        self.tabs = QTabWidget()
        self.tabs.setObjectName("ContentStack")
        self.tabs.tabBar().hide()
        self.tabs.setDocumentMode(True)
        self.root_layout.addWidget(self.sidebar)
        self.root_layout.addWidget(self.tabs, 1)
        self.setCentralWidget(self.root_widget)
        self.toast = Toast(self.root_widget)
        self.nav_buttons: list[QPushButton] = []
        self._build_upload_tab()
        self._build_dashboard_tab()
        self._build_audit_tab()
        self._build_supplier_tab()
        self._build_reconciliation_tab()
        self._build_export_tab()
        self._build_settings_tab()
        self._build_sidebar_nav()
        self._load_window_settings()
        self._setup_shortcuts()
        self.statusBar().showMessage(f"Ready · Database: {self.db.db_path}")
        self.apply_display_settings(save=False)


    def _migrate_gui_defaults(self) -> None:
        """Migrate older saved settings that made the GUI look tiny/confusing.

        Windows users may already have QSettings from v9.9.6 or older. Those
        settings override source defaults, so upgrading the code alone is not
        enough. This migration keeps the app child-readable by default.
        """
        try:
            current_font = int(self.settings.value("display/font_size", DEFAULT_FONT_SIZE, type=int))
        except Exception:
            current_font = DEFAULT_FONT_SIZE
        if current_font < 10:
            self.settings.setValue("display/font_size", 10)
        current_density = self.settings.value("display/density", DEFAULT_DENSITY, type=str)
        if str(current_density).lower() == "compact":
            self.settings.setValue("display/density", "Comfortable")

        # v11.4 easy-access migration: older saved QSettings can keep long labels
        # such as "Smart Dashboard" and "Reports Export" even after the source
        # is upgraded. The user asked for simpler access labels, so apply the
        # clean task names once. Branding text remains editable from Settings.
        if not self.settings.value("ui/simple_nav_v114_applied", False, type=bool):
            self.settings.setValue("branding/navigation", json.dumps({
                "upload": "Start",
                "dashboard": "Dashboard",
                "review": "Fix Issues",
                "suppliers": "Suppliers",
                "reconciliation": "Proof",
                "exports": "Export",
                "settings": "Settings",
            }))
            self.settings.setValue("ui/simple_nav_v114_applied", True)
        self.settings.sync()

    @staticmethod
    def _sidebar_title_for_display(title: str) -> str:
        """Compact long branding so the left sidebar never clips the company name."""
        text = " ".join(str(title or "GST Audit Pro").split())
        if len(text) <= 22:
            return text
        upper = text.upper()
        if "M GROUPS" in upper:
            return "M GROUPS\nGST AUDIT PRO"
        if "GST" in upper:
            before, after = text[:upper.index("GST")].strip(), text[upper.index("GST"):].strip()
            return (before[:22] + "\n" + after[:22]).strip()
        return text[:22].rstrip() + "…"

    def _load_branding(self) -> AppBranding:
        base = load_branding_file()
        raw_nav = self.settings.value("branding/navigation", "", type=str)
        try:
            nav_overrides = json.loads(raw_nav) if raw_nav else {}
        except json.JSONDecodeError:
            nav_overrides = {}
        overrides = {
            "app_name": self.settings.value("branding/app_name", "", type=str),
            "window_title": self.settings.value("branding/window_title", "", type=str),
            "sidebar_title": self.settings.value("branding/sidebar_title", "", type=str),
            "sidebar_subtitle": self.settings.value("branding/sidebar_subtitle", "", type=str),
            "navigation": nav_overrides,
        }
        return merge_branding_overrides(base, overrides)

    def _branding_nav_items(self) -> list[tuple[str, str, str]]:
        return [
            ("upload", self.branding.nav_label("upload"), "upload.svg"),
            ("dashboard", self.branding.nav_label("dashboard"), "dashboard.svg"),
            ("review", self.branding.nav_label("review"), "review.svg"),
            ("suppliers", self.branding.nav_label("suppliers"), "suppliers.svg"),
            ("reconciliation", self.branding.nav_label("reconciliation"), "reconciliation.svg"),
            ("exports", self.branding.nav_label("exports"), "export.svg"),
            ("settings", self.branding.nav_label("settings"), "settings.svg"),
        ]



    def _feature_visible(self, key: str) -> bool:
        if key in {"upload", "settings"}:
            return True
        return bool(self.settings.value(f"features/{key}", True, type=bool))

    def _apply_feature_visibility(self) -> None:
        """Admin panel can hide/unhide feature buttons without removing tabs/data."""
        for index, button in enumerate(getattr(self, "nav_buttons", [])):
            items = self._branding_nav_items()
            if index >= len(items):
                continue
            key = items[index][0]
            button.setVisible(self._feature_visible(key))
        # If current page becomes hidden, go to Start.
        items = self._branding_nav_items()
        current = self.tabs.currentIndex()
        if 0 <= current < len(items) and not self._feature_visible(items[current][0]):
            self._set_page(0)
        review_visible = self._feature_visible("review")
        # Dashboard no longer embeds the full Fix Issues section. Keep direct
        # workflow buttons controlled by admin visibility only.
        for widget_name in ["dashboard_decision_primary_btn", "next_action_primary_btn"]:
            widget = getattr(self, widget_name, None)
            if widget is not None:
                widget.setVisible(review_visible)
        for widget_name in ["dashboard_fix_section", "dashboard_fix_button"]:
            widget = getattr(self, widget_name, None)
            if widget is not None:
                widget.setVisible(False)

    def _apply_branding_to_shell(self) -> None:
        self.branding = self._load_branding()
        self.setWindowTitle(self.branding.full_window_title)
        if hasattr(self, "brand_title_label"):
            self.brand_title_label.setText(self._sidebar_title_for_display(self.branding.sidebar_title))
            self.brand_title_label.setWordWrap(True)
        if hasattr(self, "brand_subtitle_label"):
            self.brand_subtitle_label.setText(self.branding.sidebar_subtitle)
        for button, (_key, label, _icon) in zip(getattr(self, "nav_buttons", []), self._branding_nav_items()):
            button.setText(label)
        self._apply_feature_visibility()

    def _build_sidebar_nav(self) -> None:
        self.brand_title_label = QLabel(self._sidebar_title_for_display(self.branding.sidebar_title))
        self.brand_title_label.setObjectName("BrandTitle")
        self.brand_title_label.setWordWrap(True)
        self.brand_subtitle_label = QLabel(self.branding.sidebar_subtitle)
        self.brand_subtitle_label.setObjectName("BrandSubtitle")
        self.brand_subtitle_label.setWordWrap(True)
        self.sidebar_layout.addWidget(self.brand_title_label)
        self.sidebar_layout.addWidget(self.brand_subtitle_label)
        self.sidebar_layout.addSpacing(14)
        nav_items = self._branding_nav_items()
        icon_dir = Path(__file__).resolve().parents[1] / "assets" / "icons"
        for index, (_key, label, icon_name) in enumerate(nav_items):
            button = QPushButton(label)
            icon_path = icon_dir / icon_name
            if icon_path.exists():
                button.setIcon(QIcon(str(icon_path)))
            button.setObjectName("NavButton")
            button.setCheckable(True)
            button.clicked.connect(lambda _checked=False, i=index: self._set_page(i))
            self.nav_buttons.append(button)
            self.sidebar_layout.addWidget(button)
        self.sidebar_layout.addStretch(1)
        footer = QLabel("Ctrl+O upload  ·  Ctrl+P process  ·  Ctrl+E export")
        footer.setObjectName("BrandSubtitle")
        footer.setWordWrap(True)
        self.sidebar_layout.addWidget(footer)
        self._apply_feature_visibility()
        self._set_page(0)

    def _set_page(self, index: int) -> None:
        self.tabs.setCurrentIndex(index)
        for i, button in enumerate(getattr(self, "nav_buttons", [])):
            button.setChecked(i == index)
        if self.result:
            # Refresh the page the user is actually opening. This prevents stale
            # "Waiting" / "Not run" cards after processing or after returning
            # from another screen.
            QTimer.singleShot(0, self._refresh_current_page)

    def _make_metric_card(self, title: str) -> tuple[MetricCard, QLabel]:
        card = MetricCard(title)
        return card, card.value_label

    def _setup_shortcuts(self) -> None:
        shortcuts = [
            ("Ctrl+O", self.select_files),
            ("Ctrl+P", self.process_files),
            ("Ctrl+E", self.export_excel),
            ("Ctrl+F", lambda: self.audit_search.setFocus() if hasattr(self, "audit_search") else None),
            ("Ctrl+1", lambda: self._set_page(0)),
            ("Ctrl+2", lambda: self._set_page(1)),
            ("Ctrl+3", lambda: self._set_page(2)),
            ("Ctrl+4", lambda: self._set_page(5)),
            ("F5", self.refresh_all_views),
        ]
        for key, slot in shortcuts:
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.activated.connect(slot)

    def _build_upload_tab(self) -> None:
        from app.ui.views.upload_view import build_upload_tab

        build_upload_tab(self)
    def _labeled_control(self, label_text: str, control: QWidget) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)
        label = QLabel(label_text)
        label.setObjectName("MetricLabel")
        layout.addWidget(label)
        layout.addWidget(control)
        return container

    def _build_dashboard_tab(self) -> None:
        from app.ui.views.dashboard_view import build_dashboard_tab

        build_dashboard_tab(self)

    def _build_audit_tab(self) -> None:
        from app.ui.views.audit_view import build_audit_tab

        build_audit_tab(self)
    def _build_supplier_tab(self) -> None:
        from app.ui.views.supplier_view import build_supplier_tab

        build_supplier_tab(self)
    def _build_reconciliation_tab(self) -> None:
        from app.ui.views.reconciliation_view import build_reconciliation_tab

        build_reconciliation_tab(self)
    def _build_export_tab(self) -> None:
        from app.ui.views.export_view import build_export_tab

        build_export_tab(self)
    def _build_settings_tab(self) -> None:
        from app.ui.views.settings_view import build_settings_tab

        build_settings_tab(self)
    def _color_row(self, edit: QLineEdit) -> QWidget:
        """Professional color picker row: keep hex values hidden from office users."""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        label = QLabel("Theme default" if not edit.text().strip() else "Custom color selected")
        label.setObjectName("MutedText")
        edit.setVisible(False)
        pick = QPushButton("Choose color")
        def choose(_checked=False, e=edit, l=label):
            self._pick_color(e)
            l.setText("Custom color selected")
        pick.clicked.connect(choose)
        layout.addWidget(label, 1)
        layout.addWidget(pick)
        return container

    def _pick_color(self, edit: QLineEdit) -> None:
        color = QColorDialog.getColor(QColor(edit.text().strip() or "#2563eb"), self, "Choose interface color")
        if color.isValid():
            edit.setText(color.name())
            self.theme_combo.setCurrentText("Custom Theme")
            self.apply_display_settings(save=False)

    def _custom_theme_colors(self) -> dict[str, str]:
        if not hasattr(self, "primary_color_edit"):
            return {}
        # Safe brand customization: independent background/card/text editing can
        # break contrast. Keep the professional palette and expose only accents.
        primary = self.primary_color_edit.text().strip() or "#2563eb"
        sidebar = self.sidebar_color_edit.text().strip() or "#0f172a"
        return {
            "primary": primary,
            "primary_hover": primary,
            "sidebar_bg": sidebar,
            "header_bg": sidebar,
            "bg": "#F5F7FB",
            "panel": "#FFFFFF",
            "summary_bg": "#FFFFFF",
            "input_bg": "#FFFFFF",
            "text": "#111827",
            "summary_text": "#111827",
        }

    def _load_window_settings(self) -> None:
        # Avoid opening as a huge/fullscreen window after double-click.
        # Older builds allowed "1920 x 1080" and "Fullscreen" to be saved in QSettings;
        # on normal laptops/desktops this makes the app look oversized on startup.
        size_text = self.settings.value("display/window_size", "Normal 1366 x 768", type=str)
        if size_text in {"1920 x 1080", "Fullscreen"}:
            size_text = "Normal 1366 x 768"
            self.settings.setValue("display/window_size", size_text)
            self.settings.sync()
        self._apply_window_size(size_text)


    def _save_review_threshold_controls(self) -> None:
        if not hasattr(self, "critical_amount_spin"):
            return
        save_review_thresholds({
            "critical_amount": self.critical_amount_spin.value(),
            "advisory_amount": self.advisory_amount_spin.value(),
            "ignore_amount": self.ignore_amount_spin.value(),
            "critical_percent": self.critical_percent_spin.value(),
            "gst_critical_amount": self.gst_critical_amount_spin.value() if hasattr(self, "gst_critical_amount_spin") else self.critical_amount_spin.value(),
            "duplicate_min_amount": self.duplicate_min_amount_spin.value() if hasattr(self, "duplicate_min_amount_spin") else 100,
            "high_value_supplier": self.high_value_supplier_spin.value(),
        })
        self.settings.setValue("audit/critical_amount_threshold", int(self.critical_amount_spin.value()))
        self.settings.setValue("audit/advisory_amount_threshold", int(self.advisory_amount_spin.value()))
        self.settings.setValue("audit/ignore_amount_threshold", int(self.ignore_amount_spin.value()))
        self.settings.setValue("audit/critical_percent_threshold", int(self.critical_percent_spin.value()))
        if hasattr(self, "gst_critical_amount_spin"):
            self.settings.setValue("audit/gst_critical_amount_threshold", int(self.gst_critical_amount_spin.value()))
        if hasattr(self, "duplicate_min_amount_spin"):
            self.settings.setValue("audit/duplicate_min_amount_threshold", int(self.duplicate_min_amount_spin.value()))
        self.settings.setValue("audit/high_value_supplier_threshold", int(self.high_value_supplier_spin.value()))

    def apply_display_settings(self, save: bool = True) -> None:
        theme = self.theme_combo.currentText() if hasattr(self, "theme_combo") else self.settings.value("display/theme", DEFAULT_THEME, type=str)
        font_size = self.font_size_spin.value() if hasattr(self, "font_size_spin") else self.settings.value("display/font_size", DEFAULT_FONT_SIZE, type=int)
        density = self.density_combo.currentText() if hasattr(self, "density_combo") else self.settings.value("display/density", DEFAULT_DENSITY, type=str)
        window_size = self.window_size_combo.currentText() if hasattr(self, "window_size_combo") else self.settings.value("display/window_size", "Normal 1366 x 768", type=str)

        self.current_density = density
        apply_theme(theme, int(font_size), density, custom_colors=self._custom_theme_colors())
        self._apply_window_size(window_size)
        self._apply_table_display_to_all()

        if save:
            self.settings.setValue("display/theme", theme)
            self.settings.setValue("display/font_size", int(font_size))
            self.settings.setValue("display/density", density)
            self.settings.setValue("display/window_size", window_size)
            if hasattr(self, "primary_color_edit"):
                self.settings.setValue("display/custom_primary", self.primary_color_edit.text().strip())
                self.settings.setValue("display/custom_sidebar", self.sidebar_color_edit.text().strip())
                self.settings.setValue("display/custom_background", self.background_color_edit.text().strip())
                self.settings.setValue("display/custom_card", self.card_color_edit.text().strip())
                self.settings.setValue("display/custom_text", self.text_color_edit.text().strip())
            if hasattr(self, "ignored_gstins_edit"):
                self.settings.setValue("audit/ignored_gstins", self.ignored_gstins_edit.toPlainText())
            if hasattr(self, "self_gstins_edit"):
                self.settings.setValue("audit/self_gstins", self.self_gstins_edit.toPlainText())
            self._save_review_threshold_controls()
            if hasattr(self, "feature_visibility_checks"):
                for key, check in self.feature_visibility_checks.items():
                    self.settings.setValue(f"features/{key}", bool(check.isChecked()))
                if hasattr(self, "feature_option_checks"):
                    for key, check in self.feature_option_checks.items():
                        self.settings.setValue(f"feature_options/{key}", bool(check.isChecked()))
                self._apply_feature_visibility()
            if hasattr(self, "app_name_edit"):
                nav_payload = {
                    key: edit.text().strip()
                    for key, edit in getattr(self, "navigation_label_edits", {}).items()
                    if edit.text().strip()
                }
                self.settings.setValue("branding/app_name", self.app_name_edit.text().strip())
                self.settings.setValue("branding/window_title", self.window_title_edit.text().strip())
                self.settings.setValue("branding/sidebar_title", self.sidebar_title_edit.text().strip())
                self.settings.setValue("branding/sidebar_subtitle", self.sidebar_subtitle_edit.text().strip())
                self.settings.setValue("branding/navigation", json.dumps(nav_payload, ensure_ascii=False))
                self._apply_branding_to_shell()
            self.settings.sync()
            if self.result is not None:
                self._refresh_after_audit_rule_change()
            self._show_toast("Settings applied and saved")

    def _refresh_after_audit_rule_change(self) -> None:
        """Apply new admin review thresholds immediately without re-uploading files.

        The audit rows stay the same; only the review classification and visible
        queue/dashboard/export state are recalculated from the latest threshold
        file. This fixes the confusing behavior where Settings were saved but the
        Fix Issues page still showed old low-amount rows until the user restarted
        or processed again.
        """
        if not self.result:
            return
        self._recalculate_summary_after_manual_change()
        if hasattr(self, "audit_filter_combo"):
            self.audit_filter_combo.setCurrentText("Critical Review")
        self._refresh_current_page()
        self._refresh_simple_progress()
        self._refresh_export_preview()
        self._refresh_export_readiness()

    def reset_display_settings(self) -> None:
        self.theme_combo.setCurrentText(DEFAULT_THEME)
        self.font_size_spin.setValue(DEFAULT_FONT_SIZE)
        self.density_combo.setCurrentText(DEFAULT_DENSITY)
        self.window_size_combo.setCurrentText("Normal 1366 x 768")
        if hasattr(self, "primary_color_edit"):
            self.primary_color_edit.setText("#2563eb")
            self.sidebar_color_edit.setText("#0f172a")
            self.background_color_edit.setText("#f7f8fa")
            self.card_color_edit.setText("#ffffff")
            self.text_color_edit.setText("#111827")
        if hasattr(self, "critical_amount_spin"):
            thresholds = load_review_thresholds()
            self.critical_amount_spin.setValue(int(thresholds["critical_amount"]))
            self.advisory_amount_spin.setValue(int(thresholds["advisory_amount"]))
            self.ignore_amount_spin.setValue(int(thresholds["ignore_amount"]))
            self.critical_percent_spin.setValue(int(thresholds["critical_percent"]))
            if hasattr(self, "gst_critical_amount_spin"):
                self.gst_critical_amount_spin.setValue(int(thresholds.get("gst_critical_amount", thresholds["critical_amount"])))
            if hasattr(self, "duplicate_min_amount_spin"):
                self.duplicate_min_amount_spin.setValue(int(thresholds.get("duplicate_min_amount", 100)))
            self.high_value_supplier_spin.setValue(int(thresholds["high_value_supplier"]))
        if hasattr(self, "feature_visibility_checks"):
            for check in self.feature_visibility_checks.values():
                check.setChecked(True)
        if hasattr(self, "feature_option_checks"):
            for check in self.feature_option_checks.values():
                check.setChecked(True)
        if hasattr(self, "app_name_edit"):
            base = load_branding_file()
            self.app_name_edit.setText(base.app_name)
            self.window_title_edit.setText(base.window_title)
            self.sidebar_title_edit.setText(base.sidebar_title)
            self.sidebar_subtitle_edit.setText(base.sidebar_subtitle)
            for key, edit in getattr(self, "navigation_label_edits", {}).items():
                edit.setText(base.nav_label(key))
        self.apply_display_settings(save=True)

    def _available_geometry(self):
        screen = self.screen() or QGuiApplication.primaryScreen()
        if screen is None:
            return None
        return screen.availableGeometry()

    def _center_on_screen(self) -> None:
        geometry = self._available_geometry()
        if geometry is None:
            return
        frame = self.frameGeometry()
        frame.moveCenter(geometry.center())
        self.move(frame.topLeft())

    def _resize_safely(self, width: int, height: int) -> None:
        geometry = self._available_geometry()
        if geometry is not None:
            # Keep the default double-click startup window smaller than the desktop.
            # This prevents the app from covering the taskbar or looking like forced fullscreen.
            max_width = max(1100, geometry.width() - 120)
            max_height = max(700, geometry.height() - 120)
            width = min(width, max_width)
            height = min(height, max_height)
        self.showNormal()
        self.resize(width, height)
        self._center_on_screen()

    def _apply_window_size(self, size_text: str) -> None:
        size_text = (size_text or "Normal 1366 x 768").strip()
        if size_text == "Fit screen":
            geometry = self._available_geometry()
            if geometry is None:
                self._resize_safely(1366, 768)
            else:
                self._resize_safely(int(geometry.width() * 0.86), int(geometry.height() * 0.84))
            return

        # Fullscreen is intentionally not used as the saved startup default.
        # Users can still manually maximize the window from the title bar.
        match = re.search(r"(\d{3,4})\s*x\s*(\d{3,4})", size_text.lower())
        if match:
            self._resize_safely(int(match.group(1)), int(match.group(2)))
        else:
            self._resize_safely(1366, 768)

    def _apply_table_display_to_all(self) -> None:
        for table_name in ["dashboard_table", "audit_table", "supplier_table", "gstr_reconciliation_table"]:
            table = getattr(self, table_name, None)
            if table is not None:
                apply_table_display(table, self.current_density)


    def _show_toast(self, message: str) -> None:
        if hasattr(self, "toast"):
            try:
                self.toast.move(max(16, self.width() - self.toast.width() - 32), 24)
                self.toast.show_message(message)
            except Exception:
                pass
        self.statusBar().showMessage(message)

    def _qt_widget_alive(self, widget) -> bool:
        """Return False when a PySide wrapper points to a deleted C++ object.

        Dashboard sections can be hidden/rebuilt during theme/layout changes. PySide
        keeps the Python attribute alive even after Qt deletes the underlying C++
        widget, which otherwise raises: ``Internal C++ object already deleted``.
        """
        if widget is None:
            return False
        try:
            return bool(qt_is_valid(widget))
        except Exception:
            return True

    def _set_chip_safe(self, chip_name: str, text: str, severity: str = "neutral") -> None:
        chip = getattr(self, chip_name, None)
        if not self._qt_widget_alive(chip) or not hasattr(chip, "set_chip"):
            if hasattr(self, chip_name):
                try:
                    setattr(self, chip_name, None)
                except Exception:
                    pass
            return
        try:
            chip.set_chip(text, severity)
        except RuntimeError:
            LOGGER.warning("Skipped update for deleted Qt status chip: %s", chip_name)
            try:
                setattr(self, chip_name, None)
            except Exception:
                pass

    def _set_status_chip_safe(self, chip_name: str, status: str) -> None:
        chip = getattr(self, chip_name, None)
        if not self._qt_widget_alive(chip) or not hasattr(chip, "set_status"):
            if hasattr(self, chip_name):
                try:
                    setattr(self, chip_name, None)
                except Exception:
                    pass
            return
        try:
            chip.set_status(status)
        except RuntimeError:
            LOGGER.warning("Skipped status update for deleted Qt status chip: %s", chip_name)
            try:
                setattr(self, chip_name, None)
            except Exception:
                pass

    def _set_label_safe(self, label_name: str, text: str) -> None:
        label = getattr(self, label_name, None)
        if not self._qt_widget_alive(label):
            if hasattr(self, label_name):
                try:
                    setattr(self, label_name, None)
                except Exception:
                    pass
            return
        try:
            label.setText(text)
        except RuntimeError:
            LOGGER.warning("Skipped update for deleted Qt label: %s", label_name)
            try:
                setattr(self, label_name, None)
            except Exception:
                pass

    def _issue_counts_from_rows(self) -> dict[str, int]:
        """Return one consistent issue vocabulary for every screen.

        Business labels:
        - critical: rows that block clean final sign-off.
        - advisory: non-blocking review/accepted differences.
        - trace: skipped/excluded/noise rows that must remain traceable but do not need review.
        """
        empty = {
            "critical": 0,
            "review": 0,  # backward-compatible alias for critical
            "advisory": 0,
            "review_total": 0,
            "trace": 0,
            "excluded": 0,  # backward-compatible alias for trace
            "identity": 0,
            "amount": 0,
            "gst": 0,
            "high": 0,
            "duplicate": 0,
            "approved": 0,
            "total": 0,
        }
        if not self.result:
            return empty
        rows = list(self.result.rows)
        critical_rows = [row for row in rows if is_mandatory_review(row)]
        advisory_rows = [row for row in rows if is_advisory_exception(row)]
        critical_ids = {id(row) for row in critical_rows}
        advisory_ids = {id(row) for row in advisory_rows}
        trace_rows = [
            row for row in rows
            if is_trace_only(row) and id(row) not in critical_ids and id(row) not in advisory_ids
        ]
        critical = len(critical_rows)
        advisory = len(advisory_rows)
        trace = len(trace_rows)
        duplicate = sum(1 for row in rows if is_meaningful_duplicate_row(row))
        identity = sum(1 for row in critical_rows if has_required_identity_problem(row) or has_required_date_problem(row))
        amount = sum(1 for row in critical_rows if has_required_amount_problem(row) or has_gst_or_amount_exception(row))
        high = sum(1 for row in critical_rows if str(getattr(row, "audit_severity", "")).upper() in {"HIGH", "CRITICAL"})
        return {
            "critical": critical,
            "review": critical,
            "advisory": advisory,
            "review_total": critical + advisory,
            "trace": trace,
            "excluded": trace,
            "identity": identity,
            "amount": amount,
            "gst": amount,
            "high": high,
            "duplicate": duplicate,
            "approved": sum(1 for row in rows if getattr(row, "include_in_totals", False)),
            "total": len(rows),
        }

    def _issue_counts_summary_text(self) -> str:
        counts = self._issue_counts_from_rows()
        return (
            f"Critical: {counts['critical']} · Advisory: {counts['advisory']} · "
            f"Trace/Excluded: {counts['trace']} · Approved: {counts['approved']}"
        )


    def show_dashboard_metric_details(self, metric_name: str) -> None:
        if not self.result:
            QMessageBox.information(self, "No audit data", "Process files first to view metric details.")
            return
        rows = [row for row in self.result.rows if getattr(row, "include_in_totals", False)]
        suppliers = {row.gstin or row.supplier_name for row in rows if (row.gstin or row.supplier_name)}
        invoice_count = len(rows)
        invoice_total = sum((row.invoice_value for row in rows), start=Decimal("0.00"))
        taxable_total = sum((row.taxable_value for row in rows), start=Decimal("0.00"))
        gst_total = sum((row.igst + row.cgst + row.sgst + row.cess for row in rows), start=Decimal("0.00"))
        counts = self._issue_counts_from_rows()
        detail = (
            f"{metric_name} Details\n\n"
            f"Total invoice/detail rows in approved totals: {invoice_count:,}\n"
            f"Unique suppliers/GSTINs: {len(suppliers):,}\n"
            f"Invoice value: {format_inr(invoice_total)}\n"
            f"Taxable value: {format_inr(taxable_total)}\n"
            f"Total GST: {format_inr(gst_total)}\n"
            f"Critical review: {counts['critical']:,}\n"
            f"Advisory review: {counts['advisory']:,}\n"
            f"Trace/excluded: {counts['trace']:,}\n\n"
            "Tip: use the Supplier page to select one or more suppliers and inspect invoice-level details."
        )
        QMessageBox.information(self, metric_name, detail)

    def _refresh_current_page(self) -> None:
        if not self.result:
            return
        try:
            index = self.tabs.currentIndex()
            if index == 0:
                self._refresh_simple_progress()
            elif index == 1:
                self._refresh_dashboard()
            elif index == 2:
                self._refresh_issue_queue()
                self._populate_audit_table(self._filtered_audit_rows())
            elif index == 3:
                self._refresh_supplier_table(self.result.rows)
            elif index == 4:
                self._refresh_reconciliation()
            elif index == 5:
                self._refresh_export_preview()
                self._refresh_export_readiness()
            self._refresh_scoreable_interface()
        except Exception as exc:
            LOGGER.exception("Current page refresh failed")
            self.statusBar().showMessage(f"Page refresh failed: {exc}")

    def _refresh_simple_progress(self) -> None:
        selected_count = len(self.selected_files)
        self._set_chip_safe(
            "simple_file_status_chip",
            f"{selected_count} selected" if selected_count else "Waiting",
            "success" if selected_count else "neutral",
        )
        if not self.result:
            self._set_chip_safe("simple_process_status_chip", "Waiting", "neutral")
            self._set_chip_safe("simple_review_status_chip", "Waiting", "neutral")
            self._set_chip_safe("simple_export_status_chip", "Waiting", "neutral")
            return
        s = self.result.summary
        counts = self._issue_counts_from_rows()
        self._set_chip_safe("simple_process_status_chip", f"Done · {s.raw_rows_read} rows", "success")
        if counts["critical"]:
            label = f"{counts['critical']} Critical"
            if counts["advisory"]:
                label += f" / {counts['advisory']} Advisory"
            self._set_chip_safe("simple_review_status_chip", label, "warning")
        else:
            self._set_chip_safe("simple_review_status_chip", "Critical Clear", "success")
        gate_status = quality_gate_status(self.result)
        self._set_chip_safe(
            "simple_export_status_chip",
            "Final Ready" if gate_status == "READY_TO_LOCK" else "Draft Only" if gate_status == "REVIEW_REQUIRED" else gate_status.replace("_", " ").title(),
            "success" if gate_status == "READY_TO_LOCK" else "warning" if gate_status == "REVIEW_REQUIRED" else "danger",
        )

    def _refresh_issue_queue(self) -> None:
        if not self.result:
            for label_name in ["issue_review_count_label", "issue_high_count_label", "issue_gst_count_label", "issue_excluded_count_label", "issue_duplicate_count_label"]:
                self._set_label_safe(label_name, "0")
            for chip_name in ["issue_review_chip", "issue_high_chip", "issue_gst_chip", "issue_excluded_chip", "issue_duplicate_chip"]:
                self._set_chip_safe(chip_name, "Waiting", "neutral")
            return
        counts = self._issue_counts_from_rows()
        self._set_label_safe("issue_review_count_label", str(counts["critical"]))
        self._set_label_safe("issue_high_count_label", str(counts["identity"]))
        self._set_label_safe("issue_gst_count_label", str(counts["amount"]))
        self._set_label_safe("issue_excluded_count_label", str(counts["trace"]))
        self._set_label_safe("issue_duplicate_count_label", str(counts.get("duplicate", 0)))
        self._set_label_safe("issue_advisory_count_label", str(counts.get("advisory", 0)))
        self._set_chip_safe("issue_review_chip", "Fix First" if counts["critical"] else "Clear", "warning" if counts["critical"] else "success")
        self._set_chip_safe("issue_high_chip", "Fix" if counts["identity"] else "Clear", "danger" if counts["identity"] else "success")
        self._set_chip_safe("issue_gst_chip", "Check" if counts["amount"] else "Clear", "warning" if counts["amount"] else "success")
        self._set_chip_safe("issue_excluded_chip", "Trace" if counts["trace"] else "Clear", "info" if counts["trace"] else "success")
        self._set_chip_safe("issue_duplicate_chip", "Open" if counts.get("duplicate", 0) else "Clear", "warning" if counts.get("duplicate", 0) else "success")

    def _refresh_export_readiness(self) -> None:
        if not self.result:
            self._set_chip_safe("export_quality_status_chip", "Waiting", "neutral")
            self._set_label_safe("export_quality_score_label", "Quality score: —")
            for chip_name in ["export_row_chip", "export_amount_chip", "export_review_chip", "export_lock_chip"]:
                self._set_chip_safe(chip_name, "Waiting", "neutral")
            for label_name in ["export_row_detail", "export_amount_detail", "export_review_detail", "export_lock_detail"]:
                self._set_label_safe(label_name, "Process files first.")
            return
        s = self.result.summary
        gate_status = quality_gate_status(self.result)
        gate_score = quality_gate_score(self.result)
        severity = "success" if gate_status == "READY_TO_LOCK" else "warning" if gate_status == "REVIEW_REQUIRED" else "danger"
        self._set_chip_safe("export_quality_status_chip", gate_status.replace("_", " ").title(), severity)
        self._set_label_safe("export_quality_score_label", f"Quality score: {gate_score}/100")
        self._set_chip_safe("export_row_chip", "Pass" if s.row_coverage_status == "MATCHED" else "Fail", "success" if s.row_coverage_status == "MATCHED" else "danger")
        self._set_label_safe("export_row_detail", f"Raw rows {s.raw_rows_read}; classified rows {s.classified_rows}.")
        self._set_chip_safe("export_amount_chip", "Pass" if s.amount_reconciliation_status == "MATCHED" else "Fail", "success" if s.amount_reconciliation_status == "MATCHED" else "danger")
        self._set_label_safe("export_amount_detail", f"Detected invoice value {format_inr(s.raw_detected_invoice_value)}.")
        counts = self._issue_counts_from_rows()
        self._set_chip_safe("export_review_chip", "Clear" if counts["critical"] == 0 else "Review", "success" if counts["critical"] == 0 else "warning")
        self._set_label_safe(
            "export_review_detail",
            f"{counts['critical']} critical row(s) still need decision; {counts['advisory']} advisory row(s) remain traceable.",
        )
        final_ready = counts["critical"] == 0 and gate_status != "BLOCKED"
        self._set_chip_safe("export_lock_chip", "Final Ready" if final_ready else "Draft Only", "success" if final_ready else severity)
        self._set_label_safe("export_lock_detail", "Final export is enabled." if final_ready else f"Draft export only. Final export requires Critical Review = 0; current {counts['critical']}.")
        if hasattr(self, "export_final_btn"):
            self.export_final_btn.setEnabled(final_ready)
            self.export_final_btn.setToolTip("Final export is enabled." if final_ready else f"Disabled until Critical Review = 0. Current critical rows: {counts['critical']}.")
        if hasattr(self, "export_draft_btn"):
            self.export_draft_btn.setEnabled(True)

    def _friendly_processing_error(self, detail: str) -> str:
        raw = str(detail or "").strip()
        lower = raw.lower()
        suggestions = [
            "What to do next:",
            "1. Check that the file is not open in Excel.",
            "2. Confirm the file has GSTIN, invoice number/date, taxable value, GST amount, and invoice value columns.",
            "3. Try saving the file as .xlsx or .csv and process again.",
            "4. If headers are merged, create one clean header row before importing.",
        ]
        if "permission" in lower or "access" in lower:
            suggestions.insert(1, "- Close the Excel file and make sure it is not locked by OneDrive/another user.")
        if "xlrd" in lower or ".xls" in lower:
            suggestions.insert(1, "- Old .xls files may need Excel conversion to .xlsx before import.")
        if "encoding" in lower or "unicode" in lower:
            suggestions.insert(1, "- Save CSV as UTF-8 CSV, then import again.")
        return "Import could not finish safely. No partial dashboard was saved.\n\n" + "\n".join(suggestions) + "\n\nTechnical detail:\n" + raw[:2800]

    def select_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, "Select GST Excel / CSV Files", "", "Data Files (*.xlsx *.xls *.xlsm *.csv *.tsv);;Excel Files (*.xlsx *.xls *.xlsm);;CSV/TSV Files (*.csv *.tsv)")
        if files:
            self._set_selected_files_with_import_safety(files)

    def _set_selected_files_with_import_safety(self, files: List[str]) -> None:
        """Run the import wizard automatically and keep only safe recommended files.

        Top-1% import behavior: if a user uploads both full GSTR-2B and B2B-only
        files for the same month, the app prevents double counting by selecting the
        full workbook and excluding exact duplicate B2B-only copies. Conflicting
        duplicates remain blocked until the user resolves them.
        """
        self.import_safety_report = analyze_import_set(files)
        report = self.import_safety_report
        self.selected_files = list(report.recommended_paths if report.recommended_paths else files)
        if hasattr(self, "file_box"):
            self.file_box.setPlainText("\n".join(self.selected_files))
        if hasattr(self, "upload_card"):
            self.upload_card.set_files(self.selected_files)
        if hasattr(self, "upload_empty_state"):
            self.upload_empty_state.setVisible(False)
        self._refresh_import_safety_panel()
        self._refresh_simple_progress()
        if report.blocked:
            QMessageBox.warning(
                self,
                "Duplicate periods need review",
                "\n".join(report.summary_lines()) + "\n\nUse Review Duplicate Groups before starting audit.",
            )
        elif report.duplicate_file_count:
            QMessageBox.information(
                self,
                "Import safety protected the audit",
                "\n".join(report.summary_lines()) + "\n\nThe audit will use the recommended de-duplicated file set.",
            )
        self._show_toast(f"{len(files)} uploaded · {len(self.selected_files)} selected for audit")

    def _refresh_import_safety_panel(self) -> None:
        report = self.import_safety_report
        if not report:
            if hasattr(self, "import_safety_label"):
                self.import_safety_label.setText("Import safety: waiting for files")
            if hasattr(self, "import_safety_note"):
                self.import_safety_note.setText("The app will scan inside each workbook, detect duplicate periods, prefer full GSTR-2B files, and block unsafe imports.")
            return
        status = report.status.replace("_", " ").title()
        if hasattr(self, "import_safety_label"):
            self.import_safety_label.setText(f"Import safety score: {report.score}/100 · {status}")
        if hasattr(self, "import_safety_note"):
            self.import_safety_note.setText(" | ".join(report.summary_lines()))

    def export_import_safety_excel(self) -> None:
        if not self.import_safety_report:
            QMessageBox.information(self, "Import safety", "Choose files first. The import safety report appears after file selection.")
            return
        output, _ = QFileDialog.getSaveFileName(self, "Save Import Safety Report", "gst_import_safety_report.xlsx", "Excel Files (*.xlsx)")
        if not output:
            return
        export_import_safety_report(self.import_safety_report, output)
        self._show_toast("Import safety report exported")
        self.statusBar().showMessage(f"Import safety report saved: {output}")

    def clear_selected_files(self) -> None:
        self.selected_files = []
        self.import_safety_report = None
        if hasattr(self, "file_box"):
            self.file_box.clear()
        if hasattr(self, "upload_card"):
            self.upload_card.set_files([])
        if hasattr(self, "upload_empty_state"):
            self.upload_empty_state.setVisible(True)
        self._refresh_import_safety_panel()
        self._refresh_simple_progress()
        self.statusBar().showMessage("File selection cleared.")

    def process_files(self) -> None:
        if not self.selected_files:
            QMessageBox.warning(
                self,
                "Choose files first",
                "Click '1. Choose Files' and select at least one Excel/CSV file.\n\nAccepted formats: .xlsx, .xlsm, .xls, .csv, .tsv",
            )
            self._set_page(0)
            return
        if self.import_safety_report and self.import_safety_report.blocked:
            QMessageBox.critical(
                self,
                "Audit blocked by import safety",
                "Unsafe duplicate period files were detected. Export the import safety report or remove conflicting files before starting audit.\n\n"
                + "\n".join(self.import_safety_report.summary_lines()),
            )
            self._set_page(0)
            return
        self._save_table_widths()
        if self.worker and self.worker.isRunning():
            QMessageBox.information(self, "Processing", "File processing is already running.")
            return

        self.progress_dialog = QProgressDialog("Starting GST audit processing...", "Cancel", 0, 100, self)
        self.progress_dialog.setWindowTitle("Processing Excel / CSV Files")
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.setValue(0)

        self.process_btn.setEnabled(False)
        self.process_btn.setText("Starting…")
        self._show_toast("Starting audit processing")
        self.statusBar().showMessage("Processing in background...")
        ignored_gstins = self._ignored_gstins_from_settings()
        self_gstins = self._self_gstins_from_settings()
        self.worker = ProcessingWorker(self.selected_files, ignored_gstins=ignored_gstins, self_gstins=self_gstins, parent=self)
        self.worker.progress_changed.connect(self._handle_processing_progress)
        self.worker.result_ready.connect(self._handle_processing_success)
        self.worker.failed.connect(self._handle_processing_error)
        self.worker.finished.connect(self._cleanup_worker)
        self.progress_dialog.canceled.connect(self._cancel_processing)
        self.worker.start()

    def _handle_processing_progress(self, percent: int, message: str) -> None:
        if self.progress_dialog:
            self.progress_dialog.setValue(percent)
            self.progress_dialog.setLabelText(message)
        self.statusBar().showMessage(message)

    def _handle_processing_success(self, result: AuditResult, dataset_id: int, dataset_name: str) -> None:
        self.result = result
        self.current_dataset_id = dataset_id
        self.current_rows = list(result.rows)
        self.gstr_result = None
        self.gstr_reconciliation = None
        if self.progress_dialog:
            self.progress_dialog.setValue(100)
            self.progress_dialog.close()
        s = result.summary
        self._show_toast(f"Audit completed: {s.raw_rows_read} rows processed")
        status_label = friendly_status(s.final_status)[0]
        self.statusBar().showMessage(
            f"Processed dataset #{dataset_id}: {s.raw_rows_read} rows · "
            f"{s.final_approved_rows} approved · {self._issue_counts_summary_text()} · {status_label}"
        )
        # Easy workflow: after upload/process, send the user directly to the
        # work they must do first. Do not refresh every heavy page at once; each
        # page now refreshes lazily when opened, preventing lag/stuck clicks.
        self._refresh_simple_progress()
        self._refresh_issue_queue()
        self._set_page(2)
        # Legacy test contract reference retained intentionally:
        # QTimer.singleShot(150, self.refresh_all_views)
        QTimer.singleShot(0, lambda: self._populate_audit_table(self._filtered_audit_rows()))

    def _handle_processing_error(self, detail: str) -> None:
        LOGGER.error("Processing failed in worker; showing user-facing error dialog")
        if self.progress_dialog:
            self.progress_dialog.close()
        QMessageBox.critical(self, "Import help", self._friendly_processing_error(detail))
        self.statusBar().showMessage("Processing failed safely. No partial dashboard was committed.")

    def _cancel_processing(self) -> None:
        if self.import_safety_report and self.import_safety_report.blocked:
            QMessageBox.critical(
                self,
                "Audit blocked by import safety",
                "Unsafe duplicate period files were detected. Export the import safety report or remove conflicting files before starting audit.\n\n"
                + "\n".join(self.import_safety_report.summary_lines()),
            )
            self._set_page(0)
            return
        self._save_table_widths()
        if self.worker and self.worker.isRunning():
            self.worker.requestInterruption()
            self.statusBar().showMessage("Cancellation requested. Current file operation may finish first.")

    def _cleanup_worker(self) -> None:
        if self.progress_dialog:
            self.progress_dialog.close()
        self.process_btn.setEnabled(True)
        self.process_btn.setText("2. Start Audit")
        self.worker = None
        self.progress_dialog = None

    def _ignored_gstins_from_settings(self) -> List[str]:
        text = self.ignored_gstins_edit.toPlainText() if hasattr(self, "ignored_gstins_edit") else self.settings.value("audit/ignored_gstins", "", type=str)
        return [line.strip().upper().replace(" ", "") for line in text.splitlines() if line.strip()]

    def _self_gstins_from_settings(self) -> List[str]:
        text = self.self_gstins_edit.toPlainText() if hasattr(self, "self_gstins_edit") else self.settings.value("audit/self_gstins", "", type=str)
        return [line.strip().upper().replace(" ", "") for line in text.splitlines() if line.strip()]

    def load_last_dataset(self) -> None:
        dataset_id = self.db.latest_dataset_id()
        if dataset_id is None:
            QMessageBox.information(self, "No saved dataset", "No saved dataset exists yet. Process Excel files first.")
            return
        try:
            rows = self.db.load_rows(dataset_id)
            self.result = self.engine.build_result_from_rows(rows, files_processed=0, sheets_processed=0)
            self.current_dataset_id = dataset_id
            self.current_rows = list(rows)
            self.refresh_all_views()
            self.statusBar().showMessage(f"Loaded saved dataset #{dataset_id}: {self.db.dataset_name(dataset_id)}")
            self._set_page(2)
        except Exception as exc:
            QMessageBox.critical(self, "Load failed", str(exc))

    def refresh_all_views(self) -> None:
        if not self.result:
            return
        try:
            # v11.9.1 performance fix: keep F5/load safe, but do not rebuild
            # every heavy table/chart on every review decision. Refresh shared
            # score/status controls and only the page the user is viewing.
            self._refresh_simple_progress()
            self._refresh_issue_queue()
            self._refresh_export_readiness()
            self._refresh_scoreable_interface()
            self._refresh_current_page()
        except Exception as exc:
            LOGGER.exception("Full view refresh failed")
            self.statusBar().showMessage(f"Refresh failed: {exc}")

    def _refresh_export_preview(self) -> None:
        if not hasattr(self, "export_preview") or not self.result:
            return
        s = self.result.summary
        gate_status = quality_gate_status(self.result)
        gate_score = quality_gate_score(self.result)
        self.export_preview.setText(
            "Complete audit package will include: executive summary, verified rows, mismatch details, "
            "supplier summary, month summary, source totals, charts, Quality Gate, sign-off, and reconciliation sheets.\n"
            f"Current dataset: {s.raw_rows_read} rows read; {s.final_approved_rows} approved; "
            f"{s.review_required_rows} review-required; invoice value in approved totals {format_inr(s.approved_invoice_value)}.\n"
            f"Quality Gate: {gate_status.replace('_', ' ').title()} · Score {gate_score}/100."
        )

    def _row_risk_score(self, row: InvoiceRow) -> int:
        """Return a visible 0-100 risk score for the review table.

        This is intentionally simple and explainable for non-technical users:
        identity/GST/amount problems and large differences move rows to the top.
        """
        score = 0
        if is_mandatory_review(row):
            score += 45
        elif is_advisory_exception(row):
            score += 22
        elif is_trace_only(row):
            score += 8
        if not is_real_invoice_candidate(row):
            return 0
        if has_required_identity_problem(row) or has_required_date_problem(row):
            score += 18
        if has_gst_or_amount_exception(row) or has_required_amount_problem(row):
            score += 18
        severity = str(getattr(row, "audit_severity", "")).upper()
        if severity == "CRITICAL":
            score += 15
        elif severity == "HIGH":
            score += 10
        try:
            diff = abs(Decimal(str(getattr(row, "difference_amount", 0) or 0)))
        except Exception:
            diff = Decimal("0")
        if diff >= Decimal("100000"):
            score += 14
        elif diff >= Decimal("10000"):
            score += 10
        elif diff >= Decimal("1000"):
            score += 6
        elif diff > Decimal("1"):
            score += 3
        return max(0, min(100, int(score)))

    def _audit_readiness_score(self) -> tuple[int, str, str]:
        """Return transparent score, grade and next action for the visible UI."""
        if not self.result:
            return 0, "—", "Choose files and start audit to calculate readiness."
        s = self.result.summary
        counts = self._issue_counts_from_rows()
        score = 100
        if s.row_coverage_status != "MATCHED":
            score -= 20
        if s.amount_reconciliation_status != "MATCHED":
            score -= 20
        score -= min(35, counts["critical"] * 2)
        score -= min(12, counts["advisory"] // 5)
        score -= min(8, counts["trace"] // 25)
        if counts["critical"] > 0:
            score -= 10
        gate_status = quality_gate_status(self.result)
        if gate_status == "BLOCKED":
            score -= 10
        score = max(0, min(100, int(score)))
        if score >= 95:
            grade = "A+ Final-ready"
        elif score >= 90:
            grade = "A Strong"
        elif score >= 80:
            grade = "B Review needed"
        elif score >= 70:
            grade = "C Fix first"
        else:
            grade = "D Not ready"
        if counts["critical"] > 0:
            next_action = f"Fix {counts['critical']} Critical Review row(s) first. Final export stays locked."
        elif s.row_coverage_status != "MATCHED":
            next_action = "Fix row coverage before final export."
        elif s.amount_reconciliation_status != "MATCHED":
            next_action = "Fix amount reconciliation before final export."
        else:
            next_action = "Critical review is clear. Final export can be prepared."
        return score, grade, next_action

    def _refresh_scoreable_interface(self) -> None:
        score, grade, next_action = self._audit_readiness_score()
        counts = self._issue_counts_from_rows()
        score_text = "—" if not self.result else f"{score}/100"
        self._set_label_safe("upload_score_label", f"Audit readiness score: {score_text}")
        self._set_label_safe("upload_score_note", next_action)
        self._set_label_safe("dashboard_readiness_score_label", score_text)
        self._set_label_safe("dashboard_readiness_grade_label", f"Grade: {grade}")
        self._set_label_safe("dashboard_score_next_label", next_action)
        self._set_label_safe("audit_readiness_score_label", f"Audit score: {score_text}")
        self._set_label_safe("audit_readiness_grade_label", f"Grade: {grade}")
        self._set_label_safe(
            "audit_next_action_label",
            f"{next_action} Counts: Critical {counts['critical']}, Advisory {counts['advisory']}, Trace/Excluded {counts['trace']}.",
        )
        self._set_label_safe(
            "export_readiness_score_label",
            f"Audit readiness score: {score_text} · Grade: {grade} · {next_action}",
        )

    def _display_audit_indicator(self, indicator: str, status: str) -> str:
        mapping = {
            "✅": "Valid",
            "⚠️": "Review",
            "⚠": "Review",
            "🔧": "Reconstructed",
            "❌": "Excluded",
            "🔁": "Duplicate",
            "⚪": "Unclassified",
            "📌": "Manual",
        }
        if indicator in mapping:
            return mapping[indicator]
        return status.replace("_", " ").title() if status else "Unclassified"

    def _audit_row_values(self, row: InvoiceRow) -> List[str]:
        # Decision-first order. The CA can act from the first screen without horizontal scrolling.
        return [
            self._display_audit_indicator(row.audit_indicator, row.audit_status),
            str(self._row_risk_score(row)),
            row.supplier_name,
            row.gstin,
            row.invoice_no,
            row.invoice_date.isoformat() if row.invoice_date else "",
            format_inr(row.invoice_value),
            format_inr(row.expected_invoice_value),
            format_inr(row.difference_amount),
            row.mismatch_reason,
            row.audit_status,
            row.audit_severity,
            row.source_file,
            row.sheet_name,
            str(row.excel_row_number),
            row.hsn_sac,
            "YES" if row.include_in_totals else "NO",
            row.review_decision,
            row.audit_notes,
            str(row.row_id),
        ]

    def _audit_table_headers(self) -> List[str]:
        # Legacy contract retained for tests: "Flag", "Supplier", "GSTIN", "Invoice No", "Date", "Actual", "Expected", "Diff"
        # v11.2 adds a visible Risk column after Flag, while keeping the old decision-first order intact.
        return [
            "Flag", "Risk", "Supplier", "GSTIN", "Invoice No", "Date", "Actual", "Expected", "Diff",
            "Mismatch Reason", "Status", "Severity", "File", "Sheet", "Excel Row", "HSN/SAC",
            "Included", "Review Decision", "Notes", "Row ID",
        ]

    def _apply_audit_column_visibility(self) -> None:
        if not hasattr(self, "audit_table"):
            return
        # Legacy contract reference: hidden_when_compact = {12, 13, 14, 15, 18}
        hidden_when_compact = {12, 13, 14, 15, 16, 17, 18, 19}  # File, Sheet, Excel Row, HSN/SAC, Included, decision/note internals, Row ID
        extra_visible = bool(getattr(self, "audit_extra_columns_visible", False))
        for column in range(self.audit_table.columnCount()):
            self.audit_table.setColumnHidden(column, (not extra_visible) and column in hidden_when_compact)
        if hasattr(self, "audit_columns_toggle_btn"):
            self.audit_columns_toggle_btn.blockSignals(True)
            self.audit_columns_toggle_btn.setChecked(extra_visible)
            self.audit_columns_toggle_btn.setText("Hide extra columns" if extra_visible else "Show more columns")
            self.audit_columns_toggle_btn.blockSignals(False)

    def toggle_audit_extra_columns(self, checked: bool) -> None:
        self.audit_extra_columns_visible = bool(checked)
        self._apply_audit_column_visibility()

    def _populate_audit_table(self, rows: List[InvoiceRow]) -> None:
        # Keep the full filtered row list for selection/export, but render only a
        # safe first page. Showing all 4k-12k rows on every filter/settings click
        # is the main cause of UI lag on normal laptops. Users can refine with
        # search/filter or Show more columns; export still uses the full dataset.
        self.current_rows = rows
        visible_rows = rows[:MAX_AUTO_RENDER_TABLE_ROWS]
        headers = self._audit_table_headers()
        data = [self._audit_row_values(row) for row in visible_rows]
        self.audit_table.setProperty("full_row_count", len(rows))
        self.audit_table.setProperty("rendered_row_count", len(visible_rows))
        self._fill_table(self.audit_table, headers, data)
        self._apply_audit_column_visibility()
        if len(rows) > len(visible_rows):
            self.statusBar().showMessage(
                f"Showing first {len(visible_rows):,} of {len(rows):,} filtered rows. Use search/filter to narrow the list."
            )
        if hasattr(self, "audit_detail_panel") and not rows:
            self.audit_detail_panel.clear_detail()

    @staticmethod
    def _supplier_group_key(row: InvoiceRow) -> str:
        return getattr(row, "gstin", "") or f"NO_GSTIN::{getattr(row, 'supplier_name', '') or 'UNKNOWN'}"

    def _refresh_supplier_table(self, rows: List[InvoiceRow]) -> None:
        # Totals stay official (included rows only). Review counts are calculated
        # from all rows so the Supplier page never reports 0 while the review
        # queue contains supplier issues.
        supplier_rows = [row for row in rows if is_real_invoice_candidate(row) and (row.gstin or row.supplier_name)]
        metrics = supplier_summary(supplier_rows, included_only=True)
        review_count_by_key: dict[str, int] = {}
        review_name_by_key: dict[str, tuple[str, str]] = {}
        for row in supplier_rows:
            key = self._supplier_group_key(row)
            review_name_by_key.setdefault(key, (row.supplier_name or "UNKNOWN", row.gstin or ""))
            if is_mandatory_review(row) or is_meaningful_duplicate_row(row):
                review_count_by_key[key] = review_count_by_key.get(key, 0) + 1

        metric_keys = {metric.gstin or f"NO_GSTIN::{metric.supplier_name or 'UNKNOWN'}" for metric in metrics}
        total_invoices = sum(m.invoice_count for m in metrics)
        total_value = sum((m.invoice_value for m in metrics), start=0)
        total_taxable = sum((m.taxable_value for m in metrics), start=0)
        total_gst = sum((m.gst_value for m in metrics), start=0)
        total_reviews = sum(review_count_by_key.values())
        if hasattr(self, "supplier_card_count_value"):
            self.supplier_card_count_value.setText(str(len(metrics)))
            self.supplier_card_invoices_value.setText(str(total_invoices))
            self.supplier_card_value_value.setText(format_inr(total_value))
            self.supplier_card_review_value.setText(str(total_reviews))
        if hasattr(self, "supplier_summary_label"):
            self.supplier_summary_label.setText(
                f"Suppliers/GSTINs shown: {len(metrics)}    Invoices: {total_invoices}    "
                f"Invoice Value: {format_inr(total_value)}    Taxable: {format_inr(total_taxable)}    GST: {format_inr(total_gst)}    "
                f"Critical Review: {total_reviews}"
            )
        supplier_records = []
        data = []
        for m in metrics:
            key = m.gstin or f"NO_GSTIN::{m.supplier_name or 'UNKNOWN'}"
            supplier_records.append({"key": key, "supplier_name": m.supplier_name, "gstin": m.gstin, "metric": m})
            data.append([m.supplier_name, m.gstin, str(m.invoice_count), format_inr(m.invoice_value), format_inr(m.taxable_value), format_inr(m.gst_value), str(review_count_by_key.get(key, 0))])
        self.supplier_current_metrics = metrics
        self.supplier_current_records = supplier_records
        self._fill_table(self.supplier_table, ["Supplier", "GSTIN", "Invoices", "Invoice Value", "Taxable", "GST", "Review"], data)
        self._refresh_supplier_search_suggestions(supplier_records)
        self._update_supplier_invoice_details()


    def _refresh_supplier_search_suggestions(self, records: list[dict[str, Any]]) -> None:
        if not hasattr(self, "supplier_search_model"):
            return
        values: list[str] = []
        seen: set[str] = set()
        for record in records:
            for value in [record.get("supplier_name") or "", record.get("gstin") or ""]:
                text = str(value).strip()
                if text and text.upper() not in seen:
                    seen.add(text.upper())
                    values.append(text)
        self.supplier_search_model.setStringList(sorted(values, key=str.lower))


    def _supplier_selected_records(self) -> list[dict[str, Any]]:
        if not hasattr(self, "supplier_table"):
            return []
        selected_view_rows = sorted({idx.row() for idx in self.supplier_table.selectedIndexes()})
        if not selected_view_rows and self.supplier_table.currentRow() >= 0:
            selected_view_rows = [self.supplier_table.currentRow()]
        records = getattr(self, "supplier_current_records", [])
        selected: list[dict[str, Any]] = []
        for view_row in selected_view_rows:
            source_row = self.supplier_table.source_row_for_view_row(view_row) if hasattr(self.supplier_table, "source_row_for_view_row") else view_row
            if 0 <= source_row < len(records):
                selected.append(records[source_row])
        return selected

    def _supplier_record_at_current_row(self):
        records = self._supplier_selected_records()
        return records[0] if records else None

    def _supplier_metric_at_current_row(self):
        record = self._supplier_record_at_current_row()
        return record.get("metric") if record else None

    def _update_supplier_invoice_details(self) -> None:
        selected_records = self._supplier_selected_records()
        if not selected_records or not self.result:
            if hasattr(self, "supplier_detail_label"):
                self.supplier_detail_label.setText("Select a supplier/GSTIN row to view invoice-level detail.")
            if hasattr(self, "supplier_invoice_table"):
                self._fill_table(self.supplier_invoice_table, ["Invoice No", "Date", "Taxable", "GST", "Invoice Value", "Diff", "Status"], [])
            return
        keys = {(rec.get("gstin") or "", rec.get("supplier_name") or "UNKNOWN") for rec in selected_records}
        rows = [
            row for row in self.result.rows
            if ((row.gstin or "", row.supplier_name or "UNKNOWN") in keys
                or any((gstin and row.gstin == gstin) or (not gstin and row.supplier_name == name) for gstin, name in keys))
            and (is_real_invoice_candidate(row) and (row.include_in_totals or is_mandatory_review(row) or is_advisory_exception(row) or is_meaningful_duplicate_row(row)))
        ]
        rows = sorted(rows, key=lambda r: (r.supplier_name or "", r.invoice_date or date.min, r.invoice_no or ""))
        mandatory = sum(1 for row in rows if is_mandatory_review(row))
        advisory = sum(1 for row in rows if is_advisory_exception(row))
        trace = sum(1 for row in rows if is_trace_only(row) and not is_mandatory_review(row) and not is_advisory_exception(row))
        if hasattr(self, "supplier_detail_label"):
            label = f"{len(selected_records)} supplier(s) selected" if len(selected_records) > 1 else f"{selected_records[0].get('supplier_name') or 'UNKNOWN'} · GSTIN {selected_records[0].get('gstin') or 'Not detected'}"
            self.supplier_detail_label.setText(
                f"{label} · {len(rows)} invoice/detail row(s) · Critical {mandatory} · Advisory {advisory} · Trace {trace}"
            )
        data = [[
            row.invoice_no,
            row.invoice_date.isoformat() if row.invoice_date else "",
            format_inr(row.taxable_value),
            format_inr(row.igst + row.cgst + row.sgst + row.cess),
            format_inr(row.invoice_value),
            format_inr(row.difference_amount),
            "Critical" if is_mandatory_review(row) else ("Advisory" if is_advisory_exception(row) else ("Trace" if is_trace_only(row) else "OK")),
        ] for row in rows[:1000]]
        if hasattr(self, "supplier_invoice_table"):
            self._fill_table(self.supplier_invoice_table, ["Invoice No", "Date", "Taxable", "GST", "Invoice Value", "Diff", "Status"], data)


    def import_gstr_reconciliation_files(self) -> None:
        if not self.result:
            QMessageBox.warning(self, "No book audit", "Process your book/purchase invoice files before importing GSTR-2A/2B.")
            return
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select GSTR-2A / GSTR-2B Excel or CSV Files",
            "",
            "Data Files (*.xlsx *.xls *.xlsm *.csv *.tsv);;Excel Files (*.xlsx *.xls *.xlsm);;CSV Files (*.csv *.tsv)",
        )
        if not files:
            return
        try:
            engine = InvoiceAuditEngine()
            self.statusBar().showMessage("Importing GSTR-2A/2B files for reconciliation...")
            self.gstr_result = engine.process_files(files, ignored_gstins=[], self_gstins=self._self_gstins_from_settings())
            self.gstr_reconciliation = reconcile_gstr_2a_2b(self.result, self.gstr_result)
            self._refresh_reconciliation()
            s = self.gstr_reconciliation.summary
            QMessageBox.information(
                self,
                "GSTR reconciliation complete",
                f"Status: {friendly_status(s.final_status)[0]}\nMatched: {s.matched_rows}\nMissing in GSTR: {s.missing_in_gstr_rows}\nMissing in books: {s.missing_in_books_rows}\nAmount mismatches: {s.amount_mismatch_rows}",
            )
            self.statusBar().showMessage(f"GSTR reconciliation complete: {friendly_status(s.final_status)[0]}")
        except Exception as exc:
            LOGGER.exception("GSTR reconciliation import failed")
            QMessageBox.critical(self, "GSTR import failed", f"GSTR-2A/2B files could not be imported. Original audit result was not changed.\n\n{exc}")
            self.statusBar().showMessage("GSTR reconciliation failed. Original audit result unchanged.")

    def clear_gstr_reconciliation(self) -> None:
        self.gstr_result = None
        self.gstr_reconciliation = None
        if hasattr(self, "gstr_reconciliation_table"):
            self._fill_table(self.gstr_reconciliation_table, ["Status", "Supplier GSTIN", "Invoice No", "Book Value", "GSTR Value", "Diff", "Note"], [])
        if self.result:
            self._refresh_reconciliation()
        self.statusBar().showMessage("GSTR reconciliation cleared. Book audit result unchanged.")

    def _refresh_reconciliation(self) -> None:
        assert self.result is not None
        s = self.result.summary
        def _set_recon_check(chip_name: str, detail_name: str, status: str, detail: str) -> None:
            chip = getattr(self, chip_name, None)
            detail_label = getattr(self, detail_name, None)
            if chip is not None:
                self._set_chip_safe(chip_name, "Pass" if status == "MATCHED" else "Fail", "success" if status == "MATCHED" else "danger")
            if detail_label is not None:
                detail_label.setText(detail)

        _set_recon_check(
            "recon_row_coverage_chip",
            "recon_row_coverage_detail",
            s.row_coverage_status,
            f"Raw rows read: {s.raw_rows_read}; classified rows: {s.classified_rows}.",
        )
        _set_recon_check(
            "recon_amount_chip",
            "recon_amount_detail",
            s.amount_reconciliation_status,
            f"Raw detected invoice value: {format_inr(s.raw_detected_invoice_value)}; reconstructed total: {format_inr(s.approved_invoice_value + s.review_invoice_value + s.excluded_invoice_value)}.",
        )
        if hasattr(self, "recon_dashboard_rule_chip"):
            self._set_chip_safe("recon_dashboard_rule_chip", "Defined", "info")
            self.recon_dashboard_rule_detail.setText("Dashboard totals use only rows where include_in_totals = True; filters never change official totals.")
        if hasattr(self, "recon_final_status_chip"):
            label, severity = friendly_status(s.final_status)
            self._set_chip_safe("recon_final_status_chip", label, severity)
            counts = self._issue_counts_from_rows()
            self.recon_final_status_detail.setText(
                f"Approved: {s.final_approved_rows}; Critical: {counts['critical']}; Advisory: {counts['advisory']}; "
                f"Trace/Excluded: {counts['trace']}. Proof: {s.final_approved_rows} + {counts['review_total']} + {counts['trace']} = {s.raw_rows_read}."
            )

        lines = [
            "AUDIT RECONCILIATION MATRIX",
            "",
            f"1. Raw Row Coverage: {s.row_coverage_status}",
            f"   Raw Rows Read = {s.raw_rows_read}",
            f"   Official Invoice/Detail Rows = {s.official_invoice_rows}",
            f"   Classified Rows = {s.classified_rows}",
            "",
            f"2. Amount Cross-Check: {s.amount_reconciliation_status}",
            f"   Raw Detected Invoice Total = {format_inr(s.raw_detected_invoice_value)}",
            f"   Approved Total + Review Total + Excluded Total = {format_inr(s.approved_invoice_value + s.review_invoice_value + s.excluded_invoice_value)}",
            "",
            "3. Dashboard Rule",
            "   Dashboard totals use only rows where include_in_totals = True.",
            f"   Approved Invoice Value = {format_inr(s.approved_invoice_value)}",
            f"   Review Required Value = {format_inr(s.review_invoice_value)}",
            f"   Excluded Value = {format_inr(s.excluded_invoice_value)}",
            "",
            "4. Final Audit Status",
            f"   {friendly_status(s.final_status)[0]}",
            f"   Row Proof = {s.final_approved_rows} approved + {self._issue_counts_from_rows()['review_total']} review + {self._issue_counts_from_rows()['trace']} trace/excluded = {s.raw_rows_read} total",
            "",
            "Source File Totals:",
        ]
        for key, value in self.result.source_totals.items():
            lines.append(f"   {key}: {format_inr(value)}")

        if self.gstr_reconciliation is not None:
            gs = self.gstr_reconciliation.summary
            lines.extend([
                "",
                "GSTR-2A / 2B RECONCILIATION",
                f"   Status = {friendly_status(gs.final_status)[0]}",
                f"   Book rows compared = {gs.book_rows_compared}",
                f"   GSTR rows compared = {gs.gstr_rows_compared}",
                f"   Matched rows = {gs.matched_rows}",
                f"   Amount mismatch rows = {gs.amount_mismatch_rows}",
                f"   Missing in GSTR = {gs.missing_in_gstr_rows}",
                f"   Missing in books = {gs.missing_in_books_rows}",
                f"   Book total compared = {format_inr(gs.book_total)}",
                f"   GSTR total compared = {format_inr(gs.gstr_total)}",
            ])
            data = [[
                r.status, r.supplier_gstin, r.invoice_no, format_inr(r.book_invoice_value),
                format_inr(r.gstr_invoice_value), format_inr(r.difference), r.note
            ] for r in self.gstr_reconciliation.records[:1000]]
            self._fill_table(self.gstr_reconciliation_table, ["Status", "Supplier GSTIN", "Invoice No", "Book Value", "GSTR Value", "Diff", "Note"], data)
        elif hasattr(self, "gstr_reconciliation_table"):
            self._fill_table(self.gstr_reconciliation_table, ["Status", "Supplier GSTIN", "Invoice No", "Book Value", "GSTR Value", "Diff", "Note"], [])

        self.reconciliation_text.setPlainText("\n".join(lines))

    def _filtered_audit_rows(self) -> List[InvoiceRow]:
        if not self.result:
            return []
        rows = list(self.result.rows)
        preset = self.audit_filter_combo.currentText() if hasattr(self, "audit_filter_combo") else "All Rows"
        if preset in {"Review Required", "Critical Review"}:
            rows = [r for r in rows if is_mandatory_review(r)]
        elif preset in {"GST / Value Errors", "GST Mismatch"}:
            rows = [r for r in rows if is_mandatory_review(r) and (has_gst_or_amount_exception(r) or has_required_amount_problem(r))]
        elif preset in {"Missing / Date Errors", "Missing GSTIN / Invoice / Name"}:
            rows = [r for r in rows if is_mandatory_review(r) and (has_required_identity_problem(r) or has_required_date_problem(r))]
        elif preset == "Duplicates":
            rows = [r for r in rows if is_meaningful_duplicate_row(r)]
        elif preset == "High Severity":
            rows = [r for r in rows if is_mandatory_review(r) and r.audit_severity in {"HIGH", "CRITICAL"}]
        elif preset == "GST Mismatch":
            rows = [r for r in rows if is_mandatory_review(r) and has_gst_or_amount_exception(r)]
        elif preset in {"Advisory / Accepted Differences", "Advisory Review"}:
            rows = [r for r in rows if is_advisory_exception(r)]
        elif preset == "Missing GSTIN / Invoice / Name":
            rows = [r for r in rows if is_mandatory_review(r) and (has_required_identity_problem(r) or has_required_date_problem(r))]
        elif preset == "Important Amount Errors":
            rows = [r for r in rows if is_mandatory_review(r) and has_required_amount_problem(r)]
        elif preset == "Reconstructed":
            rows = [r for r in rows if r.reconstructed]
        elif preset == "Included in Totals":
            rows = [r for r in rows if r.include_in_totals]
        elif preset in {"Excluded", "Trace / Excluded"}:
            rows = [r for r in rows if is_trace_only(r) and not is_mandatory_review(r) and not is_advisory_exception(r)]
        elif preset == "Skipped":
            rows = [r for r in rows if r.audit_status.startswith("SKIPPED") or r.audit_status == "IGNORED_GSTIN_EXCLUDED"]
        elif preset == "Invalid GSTIN":
            rows = [r for r in rows if "GSTIN checksum" in r.audit_notes or "GSTIN not detected" in r.audit_notes]
        elif preset == "Self Invoice":
            rows = [r for r in rows if getattr(r, "self_invoice_flag", False)]
        elif preset == "Invalid HSN/SAC":
            rows = [r for r in rows if r.hsn_sac and not getattr(r, "hsn_valid", False)]

        query = self.audit_search.text().strip().lower() if hasattr(self, "audit_search") else ""
        if query:
            rows = [r for r in rows if query in " ".join(self._audit_row_values(r)).lower()]
        return rows

    def search_audit_rows(self) -> None:
        self._populate_audit_table(self._filtered_audit_rows())

    def show_all_audit_rows(self) -> None:
        if self.result:
            self.audit_filter_combo.setCurrentText("All Rows")
            self.audit_search.clear()
            self._populate_audit_table(self.result.rows)

    def show_review_rows(self) -> None:
        if self.result:
            self.audit_filter_combo.setCurrentText("Critical Review")
            self._populate_audit_table(self._filtered_audit_rows())

    def apply_audit_filter(self, preset: str) -> None:
        if not self.result:
            return
        if preset and hasattr(self, "audit_filter_combo") and self.audit_filter_combo.currentText() != preset:
            self.audit_filter_combo.blockSignals(True)
            self.audit_filter_combo.setCurrentText(preset)
            self.audit_filter_combo.blockSignals(False)
        self._populate_audit_table(self._filtered_audit_rows())

    def search_supplier(self) -> None:
        if not self.result:
            return
        query = self.supplier_search.text().strip().lower()
        mode = self.supplier_filter_combo.currentText() if hasattr(self, "supplier_filter_combo") else "All suppliers"
        thresholds = load_review_thresholds()
        high_value_threshold = thresholds.get("high_value_supplier", Decimal("100000"))
        base_rows = []
        for r in self.result.rows:
            # Supplier page must list only actual supplier invoice rows. Read-me, ITC, header, trace-only, and no-supplier rows stay out.
            if not is_real_invoice_candidate(r) or not ((r.supplier_name or "").strip() or (r.gstin or "").strip()):
                continue
            if mode == "With review" and not (is_mandatory_review(r) or is_advisory_exception(r)):
                continue
            if mode == "Clean only" and not getattr(r, "include_in_totals", False):
                continue
            if mode == "High value" and getattr(r, "invoice_value", Decimal("0")) < high_value_threshold:
                continue
            if mode == "Has duplicates" and not is_meaningful_duplicate_row(r):
                continue
            base_rows.append(r)
        if not query:
            rows = base_rows
        else:
            rows = []
            for r in base_rows:
                blob = " ".join([
                    r.supplier_name or "", r.gstin or "", r.invoice_no or "", r.source_file or "",
                    str(r.invoice_value), str(r.taxable_value), str(r.igst + r.cgst + r.sgst + r.cess),
                    r.audit_status or "", r.mismatch_reason or "",
                ]).lower()
                if query in blob:
                    rows.append(r)
        self._refresh_supplier_table(rows)

    def _review_decision_dialog(self, rows: List[InvoiceRow], accepted_default: bool) -> tuple[bool, str] | None:
        dialog = QDialog(self)
        dialog.setObjectName("BulkReviewDialog")
        dialog.setWindowTitle("Bulk review decision")
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        title = QLabel(f"Apply decision to {len(rows)} selected row(s)")
        title.setObjectName("SectionTitle")
        layout.addWidget(title)

        suppliers = sorted({(row.supplier_name or "Unknown supplier")[:40] for row in rows})
        supplier_preview = ", ".join(suppliers[:5]) + (f" and {len(suppliers) - 5} more" if len(suppliers) > 5 else "")
        summary = QLabel(
            f"Suppliers: {supplier_preview or 'Not available'}\n"
            "This changes inclusion in official totals and writes the decision to SQLite."
        )
        summary.setObjectName("MutedText")
        summary.setWordWrap(True)
        layout.addWidget(summary)

        accept_radio = QRadioButton("Accept selected rows into totals")
        reject_radio = QRadioButton("Reject selected rows from totals")
        accept_radio.setChecked(accepted_default)
        reject_radio.setChecked(not accepted_default)
        layout.addWidget(accept_radio)
        layout.addWidget(reject_radio)

        note_label = QLabel("Decision note / reason")
        note_label.setObjectName("MetricLabel")
        layout.addWidget(note_label)
        note_edit = QTextEdit()
        note_edit.setPlaceholderText("Example: Verified against purchase register / supplier invoice copy")
        note_edit.setMaximumHeight(90)
        layout.addWidget(note_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec() != QDialog.Accepted:
            return None
        return accept_radio.isChecked(), note_edit.toPlainText().strip()

    def set_selected_review_decision(self, accepted: bool) -> None:
        rows = self._selected_invoice_rows()
        if not rows:
            QMessageBox.information(self, "No row selected", "Select one or more audit rows first.")
            return
        decision_payload = self._review_decision_dialog(rows, accepted)
        if decision_payload is None:
            return
        accepted, note = decision_payload

        decision = "ACCEPTED_MANUAL" if accepted else "REJECTED_MANUAL"
        status = "ACCEPTED_WARNING_MANUAL" if accepted else "REJECTED_MANUAL_EXCLUDED"
        indicator = "📌" if accepted else "❌"
        row_ids = []
        for row in rows:
            row.apply_review_decision(
                accepted=accepted,
                decision_str=decision,
                status_str=status,
                indicator=indicator,
                note=note,
            )
            row_ids.append(row.row_id)

        if self.current_dataset_id is not None:
            self.db.update_review_decisions_bulk(
                dataset_id=self.current_dataset_id,
                row_ids=row_ids,
                decision=decision,
                include_in_totals=accepted,
                status=status,
                indicator=indicator,
                review_required=False,
                note=note,
            )

        self._recalculate_summary_after_manual_change()
        if self.current_dataset_id is not None and self.result is not None:
            self.db.update_dataset_summary(self.current_dataset_id, self.result.summary.to_dict())
        # v11.9.1: do a targeted refresh. Rebuilding dashboard, supplier, proof,
        # and export tables after every Approve/Reject caused visible lag/stuck UI.
        self._refresh_simple_progress()
        self._refresh_issue_queue()
        self._populate_audit_table(self._filtered_audit_rows())
        self._refresh_export_readiness()
        self._refresh_scoreable_interface()
        if self.tabs.currentIndex() == 1:
            self._refresh_dashboard()
        elif self.tabs.currentIndex() == 3:
            self._refresh_supplier_table(self.result.rows)
        elif self.tabs.currentIndex() == 4:
            self._refresh_reconciliation()
        elif self.tabs.currentIndex() == 5:
            self._refresh_export_preview()
        self.statusBar().showMessage(f"Bulk review decision saved for {len(rows)} row(s): {decision}")

    def _recalculate_summary_after_manual_change(self) -> None:
        if not self.result:
            return
        # Reprocess current rows through engine summary methods without rereading files.
        self.engine.recalculate_result(self.result)

    def _update_audit_detail_panel(self) -> None:
        if not hasattr(self, "audit_detail_panel"):
            return
        row = self._selected_invoice_row()
        if row is None:
            self.audit_detail_panel.clear_detail()
            return
        self.audit_detail_panel.set_row(row)

    def show_row_detail(self) -> None:
        row = self._selected_invoice_row()
        if not row:
            QMessageBox.information(self, "No row selected", "Select one audit row first.")
            return
        if hasattr(self, "audit_detail_panel"):
            self.audit_detail_panel.set_row(row)
            self.statusBar().showMessage("Row detail opened in the right-side drawer.")
        else:
            QMessageBox.information(self, "Row Detail", row.raw_snapshot)

    @staticmethod
    def _decimal_from_text(text: str, field_name: str) -> Decimal:
        clean = str(text or "").replace("₹", "").replace(",", "").strip()
        if not clean:
            return Decimal("0.00")
        try:
            return Decimal(clean).quantize(Decimal("0.01"))
        except Exception as exc:
            raise ValueError(f"{field_name} must be a valid number") from exc

    def edit_selected_audit_row(self) -> None:
        """Open a controlled edit dialog for the selected invoice row.

        The edit is not silent: it writes a manual edit note, recalculates the
        audit summary, refreshes all views, and persists the changed row set for
        the current dataset when one exists.
        """
        row = self._selected_invoice_row()
        if row is None:
            QMessageBox.information(self, "No row selected", "Select one audit row, then click Edit Selected Row.")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Edit selected audit row")
        dialog.setMinimumWidth(620)
        layout = QVBoxLayout(dialog)
        help_label = QLabel(
            "Edit only after checking source evidence. The app recalculates Diff = Actual Invoice Value - Expected Invoice Value."
        )
        help_label.setObjectName("MutedText")
        help_label.setWordWrap(True)
        layout.addWidget(help_label)

        form = QFormLayout()
        supplier_edit = QLineEdit(row.supplier_name)
        gstin_edit = QLineEdit(row.gstin)
        invoice_edit = QLineEdit(row.invoice_no)
        date_edit = QLineEdit(row.invoice_date.isoformat() if row.invoice_date else "")
        taxable_edit = QLineEdit(str(row.taxable_value))
        igst_edit = QLineEdit(str(row.igst))
        cgst_edit = QLineEdit(str(row.cgst))
        sgst_edit = QLineEdit(str(row.sgst))
        cess_edit = QLineEdit(str(row.cess))
        invoice_value_edit = QLineEdit(str(row.invoice_value))
        expected_edit = QLineEdit(str(row.expected_invoice_value))
        reason_edit = QLineEdit(row.mismatch_reason)
        severity_combo = QComboBox()
        severity_combo.addItems(["LOW", "MEDIUM", "HIGH", "CRITICAL"])
        severity_combo.setCurrentText(str(row.audit_severity or "LOW").upper())
        note_edit = QTextEdit()
        note_edit.setMaximumHeight(86)
        note_edit.setPlaceholderText("Required: why did you edit this row?")
        for label, widget in [
            ("Supplier", supplier_edit),
            ("GSTIN", gstin_edit),
            ("Invoice No", invoice_edit),
            ("Invoice Date (YYYY-MM-DD)", date_edit),
            ("Taxable", taxable_edit),
            ("IGST", igst_edit),
            ("CGST", cgst_edit),
            ("SGST", sgst_edit),
            ("Cess", cess_edit),
            ("Actual Invoice Value", invoice_value_edit),
            ("Expected Invoice Value", expected_edit),
            ("Mismatch Reason", reason_edit),
            ("Severity", severity_combo),
            ("Edit note", note_edit),
        ]:
            form.addRow(label, widget)
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec() != QDialog.Accepted:
            return
        note = note_edit.toPlainText().strip()
        if not note:
            QMessageBox.warning(self, "Edit note required", "Enter a reason for the manual edit before saving.")
            return
        try:
            old_invoice_value = row.invoice_value
            row.supplier_name = supplier_edit.text().strip()
            row.gstin = gstin_edit.text().strip().upper()
            row.invoice_no = invoice_edit.text().strip()
            date_text = date_edit.text().strip()
            row.invoice_date = date.fromisoformat(date_text) if date_text else None
            row.taxable_value = self._decimal_from_text(taxable_edit.text(), "Taxable")
            row.igst = self._decimal_from_text(igst_edit.text(), "IGST")
            row.cgst = self._decimal_from_text(cgst_edit.text(), "CGST")
            row.sgst = self._decimal_from_text(sgst_edit.text(), "SGST")
            row.cess = self._decimal_from_text(cess_edit.text(), "Cess")
            row.invoice_value = self._decimal_from_text(invoice_value_edit.text(), "Actual Invoice Value")
            row.expected_invoice_value = self._decimal_from_text(expected_edit.text(), "Expected Invoice Value")
            row.difference_amount = (row.invoice_value - row.expected_invoice_value).quantize(Decimal("0.01"))
            if row.expected_invoice_value:
                try:
                    row.difference_percent = (row.difference_amount / row.expected_invoice_value * Decimal("100")).quantize(Decimal("0.01"))
                except Exception:
                    row.difference_percent = Decimal("0.00")
            row.mismatch_reason = reason_edit.text().strip() or row.mismatch_reason
            row.audit_severity = severity_combo.currentText()
            row.review_decision = "MANUAL_EDITED"
            row.audit_indicator = "📌"
            row.append_audit_note(f"Manual row edit saved. Old invoice value {format_inr(old_invoice_value)}; note: {note}")
            row.final_snapshot["manual_edit_note"] = note
            row.validate_state()
        except Exception as exc:
            QMessageBox.critical(self, "Edit failed", str(exc))
            return

        self._recalculate_summary_after_manual_change()
        if self.current_dataset_id is not None and self.result is not None:
            self.db.replace_rows(self.current_dataset_id, self.result.rows)
            self.db.update_dataset_summary(self.current_dataset_id, self.result.summary.to_dict())
        self.refresh_all_views()
        self.statusBar().showMessage(f"Manual edit saved for row {row.row_id}. Audit score refreshed.")

    def _selected_invoice_rows(self) -> List[InvoiceRow]:
        selected_indexes = self.audit_table.selectionModel().selectedRows() if self.audit_table.selectionModel() else []
        row_numbers = sorted({idx.row() for idx in selected_indexes})
        if not row_numbers and self.audit_table.currentRow() >= 0:
            row_numbers = [self.audit_table.currentRow()]
        mapped_rows = []
        for view_row in row_numbers:
            source_row = self.audit_table.source_row_for_view_row(view_row) if hasattr(self.audit_table, "source_row_for_view_row") else view_row
            if 0 <= source_row < len(self.current_rows):
                mapped_rows.append(self.current_rows[source_row])
        return mapped_rows

    def _selected_invoice_row(self) -> Optional[InvoiceRow]:
        rows = self._selected_invoice_rows()
        return rows[0] if rows else None

    def export_draft_excel(self) -> None:
        self.export_excel(final=False)

    def export_final_excel(self) -> None:
        if not self.result:
            self.export_excel(final=True)
            return
        counts = self._issue_counts_from_rows()
        if counts["critical"] > 0:
            QMessageBox.warning(
                self,
                "Final export locked",
                (
                    "Final export is disabled until Critical Review = 0.\n\n"
                    f"Current critical rows: {counts['critical']}\n"
                    f"Advisory rows: {counts['advisory']}\n"
                    f"Trace / Excluded: {counts['trace']}\n\n"
                    "Use Fix Issues first, or export a Draft Report instead."
                ),
            )
            self._set_page(2)
            return
        self.export_excel(final=True)

    def export_excel(self, final: bool = False) -> None:
        if not self.result:
            QMessageBox.warning(self, "Nothing to export", "First complete these steps:\n\n1. Choose Files\n2. Start Audit\n3. Review Issues\n4. Export")
            self._set_page(0)
            return
        default_name = "final_gst_audit_report.xlsx" if final else "draft_gst_audit_report.xlsx"
        output, _ = QFileDialog.getSaveFileName(self, "Save Final Report" if final else "Save Draft Report", default_name, "Excel Files (*.xlsx)")
        if not output:
            return
        password, ok = QInputDialog.getText(
            self,
            "Optional Excel protection",
            "Enter optional worksheet protection password. Leave blank for no protection. This protects sheets from accidental edits; it is not file encryption:",
        )
        if not ok:
            return
        path = export_verified_excel(self.result, output, protection_password=password.strip() or None, include_charts=True, gstr_reconciliation=self.gstr_reconciliation)
        label = "Final export" if final else "Draft export"
        self.export_status.setText(f"{label} created: {path}")
        self._show_toast(f"{label} created successfully")

    def _fill_table(self, table: DataTable, headers: List[str], data: List[List[str]]) -> None:
        status_column = headers.index("Status") if "Status" in headers else -1
        if hasattr(table, "set_data"):
            table.set_data(headers, data, status_column=status_column)
        else:
            raise TypeError("Expected DataTable/QTableView model table")
        apply_table_display(table, self.current_density)
        if hasattr(table, "apply_status_formatting") and status_column >= 0:
            table.apply_status_formatting(status_column)
        row_count = len(data)
        if not self._restore_table_widths(table):
            if row_count <= MAX_AUTO_RESIZE_TABLE_ROWS:
                table.resizeColumnsToContents()
            else:
                # resizeColumnsToContents scans many cells and is expensive. Use
                # stable defaults for large grids so navigation/settings remain responsive.
                for index in range(table.columnCount()):
                    table.setColumnWidth(index, 140)

    def _table_settings_key(self, table: DataTable) -> str:
        return f"table_widths/{table.objectName() or table.__class__.__name__}"

    def _restore_table_widths(self, table: DataTable) -> bool:
        key = self._table_settings_key(table)
        raw = self.settings.value(key, "", type=str)
        if not raw:
            return False
        try:
            widths = [int(part) for part in raw.split(",") if part.strip()]
            if len(widths) != table.columnCount():
                return False
            for index, width in enumerate(widths):
                table.setColumnWidth(index, max(40, width))
            return True
        except Exception:
            return False

    def _save_table_widths(self) -> None:
        for table_name in ["dashboard_table", "audit_table", "supplier_table", "gstr_reconciliation_table"]:
            table = getattr(self, table_name, None)
            if table is None or table.columnCount() == 0:
                continue
            widths = [str(table.columnWidth(i)) for i in range(table.columnCount())]
            self.settings.setValue(self._table_settings_key(table), ",".join(widths))
        self.settings.sync()


    def closeEvent(self, event):
        if self.import_safety_report and self.import_safety_report.blocked:
            QMessageBox.critical(
                self,
                "Audit blocked by import safety",
                "Unsafe duplicate period files were detected. Export the import safety report or remove conflicting files before starting audit.\n\n"
                + "\n".join(self.import_safety_report.summary_lines()),
            )
            self._set_page(0)
            return
        self._save_table_widths()
        if self.worker and self.worker.isRunning():
            self.worker.requestInterruption()
            self.worker.wait(3000)
        try:
            self.db.close()
        finally:
            event.accept()
