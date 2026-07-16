from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_single_version_source_and_export_uses_it_v88():
    version_source = (ROOT / "app/version.py").read_text(encoding="utf-8")
    exporter_source = (ROOT / "app/core/exporter.py").read_text(encoding="utf-8")
    assert "APP_VERSION = " in version_source
    assert 'APP_VERSION = "9.3.0"' not in version_source
    assert "from app.version import APP_VERSION, RELEASE_NAME" in exporter_source
    assert "v6.8 stabilization release" not in exporter_source


def test_excel_export_formula_injection_hardening_contract():
    source = (ROOT / "app/core/exporter.py").read_text(encoding="utf-8")
    assert "strings_to_formulas" in source
    assert "strings_to_urls" in source
    assert "sanitize_excel_value" in source
    assert "EXCEL_FORMULA_PREFIXES" in source


def test_main_tables_use_qtableview_model_not_qtablewidget():
    source = (ROOT / "app/ui/widgets/data_table.py").read_text(encoding="utf-8")
    assert "class DataTableModel(QAbstractTableModel)" in source
    assert "class DataTable(QTableView)" in source
    assert "source_row_for_view_row" in source
    assert "class DataTable(QTableWidget)" not in source


def test_database_has_user_data_path_and_tamper_evident_review_log():
    source = (ROOT / "app/core/database.py").read_text(encoding="utf-8")
    assert "LOCALAPPDATA" in source
    assert "XDG_DATA_HOME" in source
    assert "previous_hash" in source
    assert "decision_hash" in source
    assert "hashlib.sha256" in source


def test_v87_dashboard_count_donut_uses_row_formatter_not_currency():
    source = (ROOT / "app/ui/controllers/dashboard_controller.py").read_text(encoding="utf-8")
    assert "def _format_row_count" in source
    assert "formatter=self._format_row_count" in source
    chart_source = (ROOT / "app/ui/widgets/chart_panel.py").read_text(encoding="utf-8")
    assert "max_bar_width = 220 if bar_count == 1 else 170" in chart_source


def test_v87_dashboard_compacts_quick_filter_chips_and_protects_share_width():
    source = (ROOT / "app/ui/controllers/dashboard_controller.py").read_text(encoding="utf-8")
    assert "visible_sources = [source for source, _count in source_counts.most_common(2)]" in source
    assert "visible_months = [month for month, _count in month_items[-3:]]" in source
    assert "{0: 44, 3: 84, 5: 86, 8: 76}" in source


def test_v87_popup_clears_stale_query_and_forces_light_popup_background():
    source = (ROOT / "app/ui/widgets/guided_filter.py").read_text(encoding="utf-8")
    assert "Do not keep stale internal popup search text" in source
    assert 'self._query_by_field[key] = "" if selected_values else popup.current_query()' in source
    assert "FilterPopupScrollContent" in source
    assert "previously appeared as black blocks" in source


def test_v87_polished_supplier_detail_panel_uses_rich_html():
    view_source = (ROOT / "app/ui/views/dashboard_view.py").read_text(encoding="utf-8")
    controller_source = (ROOT / "app/ui/controllers/dashboard_controller.py").read_text(encoding="utf-8")
    assert "QTextBrowser" in view_source
    assert "setHtml" in controller_source
    assert "risk-card" in controller_source


def test_v87_release_cleanliness_and_screenshot_regression_scaffold():
    assert (ROOT / "tests/test_gui_screenshot_regression.py").exists()
    verify_source = (ROOT / "scripts/verify_release.py").read_text(encoding="utf-8")
    assert "local test artifact" in verify_source
    assert "__pycache__" in verify_source


def test_v87_popup_has_premium_bounded_dropdown_contract():
    source = (ROOT / "app/ui/widgets/guided_filter.py").read_text(encoding="utf-8")
    theme_source = (ROOT / "app/ui/theme_manager.py").read_text(encoding="utf-8")
    assert "MIN_WIDTH = 560" in source
    assert "MAX_WIDTH = 720" in source
    assert "POPUP_HEIGHT = 430" in source
    assert "FOOTER_HEIGHT = 56" in source
    assert "SCROLL_MAX_HEIGHT = 246" in source
    assert "popup.setFixedSize(width, _FloatingValuePicker.POPUP_HEIGHT)" in source
    assert "Selected" in source
    assert "Best matches" in source
    assert "Suggested matches" in source
    assert "No {self.field_label.lower()} found" in source
    assert "Qt.Key.Key_Down" in source
    assert "Qt.Key.Key_Space" in source
    assert "Qt.KeyboardModifier.ControlModifier" in source
    assert "FilterPopupFooter" in theme_source
    assert "FilterPopupGroupLabel" in theme_source
    assert 'QFrame#FilterOptionRow[focused="true"]' in theme_source
