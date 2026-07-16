from __future__ import annotations

from pathlib import Path

from app.version import APP_VERSION, RELEASE_NAME

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "app/ui/main_window.py"
DASHBOARD = ROOT / "app/ui/controllers/dashboard_controller.py"
VERIFY = ROOT / "scripts/verify_release.py"


def test_v997_release_identity() -> None:
    assert APP_VERSION == "11.13.0"
    assert "GUI Sync Clarity" in RELEASE_NAME


def test_page_navigation_triggers_targeted_refresh() -> None:
    source = MAIN.read_text(encoding="utf-8")
    assert "def _refresh_current_page" in source
    assert "QTimer.singleShot(0, self._refresh_current_page)" in source
    assert "self._refresh_simple_progress()" in source
    assert "self._refresh_issue_queue()" in source
    assert "self._refresh_reconciliation()" in source
    assert "self._refresh_export_readiness()" in source


def test_review_queue_uses_row_counts_not_stale_cards() -> None:
    source = MAIN.read_text(encoding="utf-8")
    assert "def _issue_counts_from_rows" in source
    assert "counts = self._issue_counts_from_rows()" in source
    assert "issue_review_count_label" in source
    assert "issue_high_count_label" in source
    assert "issue_gst_count_label" in source
    assert "issue_excluded_count_label" in source


def test_start_export_and_reconciliation_are_refresh_safe() -> None:
    source = MAIN.read_text(encoding="utf-8")
    assert "Done · {s.raw_rows_read} rows" in source
    assert "export_review_detail" in source
    assert "QTimer.singleShot(150, self.refresh_all_views)" in source


def test_sidebar_and_old_settings_are_child_readable() -> None:
    source = MAIN.read_text(encoding="utf-8")
    assert "def _migrate_gui_defaults" in source
    assert "display/font_size" in source
    assert "current_font < 10" in source
    assert "display/density" in source
    assert "def _sidebar_title_for_display" in source
    assert "M GROUPS\\nGST AUDIT PRO" in source


def test_dashboard_excluded_action_targets_real_filter_name() -> None:
    source = DASHBOARD.read_text(encoding="utf-8")
    assert 'self.audit_filter_combo.setCurrentText("Excluded")' in source
    assert 'Skipped / Excluded' not in source


def test_release_verification_requires_v997_notes() -> None:
    source = VERIFY.read_text(encoding="utf-8")
    assert "docs/WORKFLOW_CLARITY_V9_9_8.md" in source
