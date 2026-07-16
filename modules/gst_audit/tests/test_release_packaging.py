from __future__ import annotations

from pathlib import Path

from scripts.verify_release import verify_release


def test_required_release_files_are_present():
    root = Path(__file__).resolve().parents[1]
    missing_only = [p for p in verify_release(root) if p.startswith("Missing required")]
    assert missing_only == []


def test_modern_ui_files_are_present():
    root = Path(__file__).resolve().parents[1]
    required = [
        "app/ui/widgets/metric_card.py",
        "app/ui/widgets/status_chip.py",
        "app/ui/widgets/data_table.py",
        "app/ui/views/upload_view.py",
        "app/ui/views/audit_view.py",
        "app/ui/views/supplier_view.py",
        "app/ui/views/reconciliation_view.py",
        "app/ui/views/export_view.py",
        "app/ui/views/settings_view.py",
        "app/assets/styles/main.qss",
    ]
    assert [item for item in required if not (root / item).exists()] == []


def test_status_chip_labels_are_professional_text_not_emoji_prefixes():
    source = (Path(__file__).resolve().parents[1] / "app/ui/widgets/status_chip.py").read_text(encoding="utf-8")
    forbidden = ["✅", "⚠", "❌", "🔁", "🧾", "⏭"]
    assert [symbol for symbol in forbidden if symbol in source] == []
