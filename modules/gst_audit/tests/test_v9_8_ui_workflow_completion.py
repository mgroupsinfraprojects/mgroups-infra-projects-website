from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN_WINDOW = ROOT / "app/ui/main_window.py"
AUDIT_VIEW = ROOT / "app/ui/views/audit_view.py"
UPLOAD_VIEW = ROOT / "app/ui/views/upload_view.py"
EXPORT_VIEW = ROOT / "app/ui/views/export_view.py"
RECON_VIEW = ROOT / "app/ui/views/reconciliation_view.py"
THEME_MANAGER = ROOT / "app/ui/theme_manager.py"


def test_audit_table_uses_decision_first_column_order_and_compact_toggle():
    source = MAIN_WINDOW.read_text(encoding="utf-8")
    assert "def _audit_table_headers" in source
    assert '"Flag", "Supplier", "GSTIN", "Invoice No", "Date", "Actual", "Expected", "Diff"' in source
    assert "hidden_when_compact = {12, 13, 14, 15, 18}" in source
    assert "def toggle_audit_extra_columns" in source
    assert "audit_columns_toggle_btn" in AUDIT_VIEW.read_text(encoding="utf-8")


def test_bulk_review_uses_structured_dialog_not_text_prompt_only():
    source = MAIN_WINDOW.read_text(encoding="utf-8")
    assert "def _review_decision_dialog" in source
    assert "QDialog" in source
    assert "QRadioButton" in source
    assert "QInputDialog.getText" not in source[source.index("def set_selected_review_decision"):source.index("def _recalculate_summary_after_manual_change")]


def test_upload_and_export_pages_have_action_hierarchy_and_preview():
    upload = UPLOAD_VIEW.read_text(encoding="utf-8")
    export = EXPORT_VIEW.read_text(encoding="utf-8")
    main = MAIN_WINDOW.read_text(encoding="utf-8")
    assert "PrimaryActionButton" in upload
    assert "SecondaryButton" in upload
    assert "DangerOutlineButton" in upload
    assert "window.export_preview" in export
    assert "def _refresh_export_preview" in main
    assert "self.process_btn.setText(\"Starting…\")" in main
    assert "self.process_btn.setText(\"2. Start Audit\")" in main


def test_reconciliation_is_card_based_and_settings_use_toast():
    recon = RECON_VIEW.read_text(encoding="utf-8")
    main = MAIN_WINDOW.read_text(encoding="utf-8")
    assert "ReconciliationCard" in recon
    assert "recon_row_coverage_chip" in recon
    assert "recon_amount_chip" in recon
    assert "recon_final_status_chip" in recon
    assert "Settings applied and saved" in main
    assert "QMessageBox.information(self, \"Settings saved\"" not in main


def test_theme_knows_new_ui_object_names():
    theme = THEME_MANAGER.read_text(encoding="utf-8")
    assert "QFrame#ReconciliationCard" in theme
    assert "QPushButton#SecondaryButton" in theme
    assert "QPushButton#PrimaryActionButton" in theme
    assert "QDialog#BulkReviewDialog" in theme
