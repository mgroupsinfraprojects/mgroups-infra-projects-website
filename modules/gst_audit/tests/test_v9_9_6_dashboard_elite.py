from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_VIEW = ROOT / "app/ui/views/dashboard_view.py"
DASHBOARD_CONTROLLER = ROOT / "app/ui/controllers/dashboard_controller.py"
STYLE = ROOT / "app/assets/styles/main.qss"


def test_dashboard_is_decision_first_not_chart_first():
    source = DASHBOARD_VIEW.read_text(encoding="utf-8")
    decision_index = source.index("window.dashboard_decision_card")
    issue_index = source.index("window.dashboard_issue_panel")
    filter_index = source.index("layout.addWidget(filter_panel)")
    charts_index = source.index("layout.addWidget(charts_section)")
    assert decision_index < charts_index
    assert issue_index < charts_index
    assert "Audit status" in source
    assert "Quality Gate before export" in source
    assert "Official vs visible totals" in source
    assert decision_index < filter_index


def test_dashboard_has_child_readable_fix_queue_and_export_gate():
    source = DASHBOARD_VIEW.read_text(encoding="utf-8")
    for phrase in [
        "Fix first",
        "Review rows",
        "High risk",
        "GST mismatch",
        "Duplicates / skipped",
        "Simple path: Choose Files → Start Audit → Review Issues → Export.",
    ]:
        assert phrase in source
    for attr in [
        "dashboard_issue_review_label",
        "dashboard_issue_high_label",
        "dashboard_issue_gst_label",
        "dashboard_issue_excluded_label",
        "dashboard_gate_row_chip",
        "dashboard_gate_amount_chip",
        "dashboard_gate_review_chip",
        "dashboard_gate_lock_chip",
    ]:
        assert attr in source


def test_dashboard_controller_refreshes_quality_gate_and_issue_counts():
    source = DASHBOARD_CONTROLLER.read_text(encoding="utf-8")
    assert "def _refresh_dashboard_decision_center" in source
    assert "quality_gate_score" in source
    assert "quality_gate_status" in source
    assert "Official review:" in source
    assert "Visible review:" in source
    assert "dashboard_issue_review_chip" in source
    assert "dashboard_gate_lock_chip" in source
    assert "_refresh_dashboard_decision_center(rows, approved_rows, review_count, mismatch_count)" in source


def test_dashboard_styles_include_elite_decision_cards():
    style = STYLE.read_text(encoding="utf-8")
    for object_name in [
        "DashboardDecisionCard",
        "DashboardDecisionTitle",
        "DashboardMiniPanel",
        "DashboardIssuePanel",
        "DashboardIssueCard",
        "DashboardIssueNumber",
    ]:
        assert object_name in style
