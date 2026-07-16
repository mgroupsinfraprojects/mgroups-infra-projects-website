from __future__ import annotations

from pathlib import Path


def test_v9_9_9_readable_layer_facades_import_cleanly():
    import dashboard
    import theme
    import workflow

    assert "Overview" in dashboard.DASHBOARD_MODES
    assert theme.DEFAULT_FONT_SIZE >= 10
    assert workflow.MANDATORY_REVIEW_AMOUNT > 0


def test_v9_9_9_professional_folder_docs_are_present_and_specific():
    root = Path(__file__).resolve().parents[1]
    docs = [
        root / "docs" / "PROFESSIONAL_FOLDER_STRUCTURE_V9_9_9.md",
        root / "docs" / "SECTIONWISE_REVIEW_GUIDE_V9_9_9.md",
        root / "docs" / "WORKFLOW_ARCHITECTURE_V9_9_9.md",
    ]
    for doc in docs:
        text = doc.read_text(encoding="utf-8")
        assert "Start Audit" in text or "Folder Structure" in text or "Workflow" in text
    structure = docs[0].read_text(encoding="utf-8")
    for folder in ["frontend/", "backend/", "dashboard/", "theme/", "workflow/", "data_layer/", "security_layer/"]:
        assert folder in structure


def test_v9_9_9_upload_card_collapses_file_details_by_default():
    source = (Path(__file__).resolve().parents[1] / "app" / "ui" / "widgets" / "upload_card.py").read_text(encoding="utf-8")
    assert "file_table.setVisible(False)" in source
    assert "Show selected files" in source
    assert "Ready to audit" in source
