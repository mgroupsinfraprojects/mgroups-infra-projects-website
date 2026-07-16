from __future__ import annotations

import json
from pathlib import Path

from app.core.branding import DEFAULT_NAVIGATION_LABELS, branding_from_mapping, load_branding_file, merge_branding_overrides

ROOT = Path(__file__).resolve().parents[1]


def test_app_identity_json_drives_changeable_software_and_navigation_names() -> None:
    identity_path = ROOT / "config" / "app_identity.json"
    data = json.loads(identity_path.read_text(encoding="utf-8"))
    assert data["app_name"] == "GST Audit Pro"
    assert data["navigation"]["upload"] == "Start Audit"
    assert set(DEFAULT_NAVIGATION_LABELS).issubset(data["navigation"])

    branding = load_branding_file(identity_path)
    assert branding.app_name == data["app_name"]
    assert branding.nav_label("review") == data["navigation"]["review"]


def test_branding_sanitizes_unsafe_values_and_preserves_defaults() -> None:
    branding = branding_from_mapping(
        {
            "app_name": "  My <Firm> GST!!!  ",
            "navigation": {"upload": "  Begin / Audit  ", "missing": "ignored"},
        }
    )
    assert branding.app_name == "My Firm GST"
    assert branding.nav_label("upload") == "Begin / Audit"
    assert branding.nav_label("dashboard") == DEFAULT_NAVIGATION_LABELS["dashboard"]


def test_settings_overrides_can_replace_file_branding_without_pyside_dependency() -> None:
    base = branding_from_mapping({"app_name": "Base GST", "navigation": {"review": "Old Review"}})
    merged = merge_branding_overrides(
        base,
        {
            "app_name": "Firm Audit Desk",
            "window_title": "Firm GST Control Center",
            "navigation": {"review": "Exception Queue"},
        },
    )
    assert merged.app_name == "Firm Audit Desk"
    assert merged.window_title == "Firm GST Control Center"
    assert merged.nav_label("review") == "Exception Queue"


def test_settings_page_exposes_branding_theme_and_audit_sections() -> None:
    source = (ROOT / "app/ui/views/settings_view.py").read_text(encoding="utf-8")
    assert "Application Identity & Navigation" in source
    assert "Theme & Display Settings" in source
    assert "Audit Rules & GSTIN Lists" in source
    assert "window.navigation_label_edits" in source
    assert "config/app_identity.json" in source
