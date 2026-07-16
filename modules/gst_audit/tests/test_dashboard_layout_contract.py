from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_VIEW = ROOT / "app/ui/views/dashboard_view.py"
MAIN_WINDOW = ROOT / "app/ui/main_window.py"


def test_dashboard_uses_scroll_area_to_prevent_small_screen_overlap():
    source = DASHBOARD_VIEW.read_text(encoding="utf-8")
    assert "QScrollArea" in source
    assert "setWidgetResizable(True)" in source
    assert "setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)" in source


def test_dashboard_charts_have_compact_progressive_disclosure_contract():
    source = DASHBOARD_VIEW.read_text(encoding="utf-8")
    assert "chart.setMinimumHeight(220)" in source
    assert "charts_section.setMinimumHeight(250)" in source
    assert "window.dashboard_chart_details_btn" in source
    assert "window.dashboard_extra_charts" in source
    assert "chart.setVisible(False)" in source


def test_supplier_drilldown_is_separate_from_chart_grid():
    source = DASHBOARD_VIEW.read_text(encoding="utf-8")
    chart_index = source.index("layout.addWidget(charts_section)")
    title_index = source.index("layout.addWidget(table_title)")
    splitter_index = source.index("layout.addWidget(window.dashboard_splitter)")
    assert chart_index < title_index < splitter_index
    assert "window.dashboard_splitter.setMinimumHeight(260)" in source


def test_processing_status_bar_uses_friendly_status_not_raw_enum():
    source = MAIN_WINDOW.read_text(encoding="utf-8")
    assert "status_label = friendly_status(s.final_status)[0]" in source
    assert "· {s.final_status}" not in source
