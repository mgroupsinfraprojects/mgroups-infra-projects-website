from __future__ import annotations

from pathlib import Path

from app.version import APP_VERSION, RELEASE_NAME

ROOT = Path(__file__).resolve().parents[1]


def test_v995_simple_gui_release_identity() -> None:
    assert APP_VERSION == "11.13.0"
    assert "GUI Sync Clarity" in RELEASE_NAME


def test_upload_page_is_four_step_start_workflow() -> None:
    source = (ROOT / "app/ui/views/upload_view.py").read_text(encoding="utf-8")
    assert "Start Here" in source
    assert "1. Choose Files" in source
    assert "2. Start Audit" in source
    assert "3. Review Issues" in source
    assert "4. Export" in source
    assert "import_profile_combo" in source
    assert "Auto detect columns" in source
    assert "GSTR-2A / GSTR-2B" in source


def test_review_center_has_issue_queue_and_detail_drawer() -> None:
    source = (ROOT / "app/ui/views/audit_view.py").read_text(encoding="utf-8")
    main = (ROOT / "app/ui/main_window.py").read_text(encoding="utf-8")
    assert "Review Center" in source
    assert "IssueQueueCard" in source
    assert "Needs Review" in source
    assert "High Risk" in source
    assert "GST Mismatch" in source
    assert "Duplicates / Excluded" in source
    assert "RowDetailPanel" in source
    assert "def _refresh_issue_queue" in main


def test_export_readiness_is_visible_before_export() -> None:
    source = (ROOT / "app/ui/views/export_view.py").read_text(encoding="utf-8")
    main = (ROOT / "app/ui/main_window.py").read_text(encoding="utf-8")
    assert "Export Readiness" in source
    assert "Quality score:" in source
    assert "Row coverage" in source
    assert "Amount match" in source
    assert "Review queue" in source
    assert "Final lock" in source
    assert "def _refresh_export_readiness" in main
    assert "quality_gate_score" in main
    assert "quality_gate_status" in main


def test_error_recovery_and_keyboard_shortcuts_are_child_safe() -> None:
    main = (ROOT / "app/ui/main_window.py").read_text(encoding="utf-8")
    assert "def _friendly_processing_error" in main
    assert "What to do next:" in main
    assert "Ctrl+1" in main
    assert "Ctrl+2" in main
    assert "Ctrl+3" in main
    assert "Ctrl+4" in main
    assert "Choose files first" in main
