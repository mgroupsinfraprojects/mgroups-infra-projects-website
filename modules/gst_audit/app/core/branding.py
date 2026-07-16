from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

from app.version import APP_NAME, APP_TITLE, APP_VERSION

ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_BRANDING_FILE = ROOT_DIR / "config" / "app_identity.json"

DEFAULT_NAVIGATION_LABELS: dict[str, str] = {
    "upload": "Start",
    "dashboard": "Dashboard",
    "review": "Fix Issues",
    "suppliers": "Suppliers",
    "reconciliation": "Proof",
    "exports": "Export",
    "settings": "Settings",
}

_NAV_KEYS = tuple(DEFAULT_NAVIGATION_LABELS)
_MAX_NAME_LENGTH = 72
_SAFE_TEXT_RE = re.compile(r"[^\w\s&.,:/+()\-–—]")


@dataclass(frozen=True)
class AppBranding:
    """Runtime branding and navigation labels.

    This is intentionally kept in app.core so it can be tested without PySide6.
    It supports two customization paths:
    1. edit config/app_identity.json before launching the desktop app;
    2. change values from the Settings page, which stores local QSettings overrides.
    """

    app_name: str = APP_NAME
    window_title: str = APP_TITLE
    sidebar_title: str = APP_NAME
    sidebar_subtitle: str = "Invoice verification workspace"
    navigation: Mapping[str, str] = field(default_factory=lambda: dict(DEFAULT_NAVIGATION_LABELS))

    @property
    def full_window_title(self) -> str:
        title = self.window_title or self.app_name
        return f"{title} v{APP_VERSION}"

    def nav_label(self, key: str) -> str:
        return str(self.navigation.get(key, DEFAULT_NAVIGATION_LABELS.get(key, key.title())))

    def as_json_dict(self) -> dict[str, object]:
        return {
            "app_name": self.app_name,
            "window_title": self.window_title,
            "sidebar_title": self.sidebar_title,
            "sidebar_subtitle": self.sidebar_subtitle,
            "navigation": {key: self.nav_label(key) for key in _NAV_KEYS},
        }


def _clean_display_text(value: object, fallback: str) -> str:
    text = str(value or "").strip()
    if not text:
        return fallback
    text = _SAFE_TEXT_RE.sub("", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:_MAX_NAME_LENGTH] or fallback


def _clean_navigation(raw: object) -> dict[str, str]:
    result = dict(DEFAULT_NAVIGATION_LABELS)
    if isinstance(raw, Mapping):
        for key in _NAV_KEYS:
            if key in raw:
                result[key] = _clean_display_text(raw[key], result[key])
    return result


def branding_from_mapping(raw: Mapping[str, object] | None) -> AppBranding:
    raw = raw or {}
    return AppBranding(
        app_name=_clean_display_text(raw.get("app_name"), APP_NAME),
        window_title=_clean_display_text(raw.get("window_title"), APP_TITLE),
        sidebar_title=_clean_display_text(raw.get("sidebar_title"), APP_NAME),
        sidebar_subtitle=_clean_display_text(raw.get("sidebar_subtitle"), "Invoice verification workspace"),
        navigation=_clean_navigation(raw.get("navigation")),
    )


def load_branding_file(path: Path = DEFAULT_BRANDING_FILE) -> AppBranding:
    if not path.exists():
        return branding_from_mapping({})
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return branding_from_mapping({})
    if not isinstance(payload, Mapping):
        return branding_from_mapping({})
    return branding_from_mapping(payload)


def merge_branding_overrides(base: AppBranding, overrides: Mapping[str, object] | None) -> AppBranding:
    """Apply settings-page overrides on top of file/default branding."""
    merged = base.as_json_dict()
    overrides = overrides or {}
    for key in ("app_name", "window_title", "sidebar_title", "sidebar_subtitle"):
        value = overrides.get(key)
        if value:
            merged[key] = value
    nav = dict(merged.get("navigation", DEFAULT_NAVIGATION_LABELS))
    raw_nav = overrides.get("navigation")
    if isinstance(raw_nav, Mapping):
        nav.update({str(k): str(v) for k, v in raw_nav.items() if str(v).strip()})
    merged["navigation"] = nav
    return branding_from_mapping(merged)
