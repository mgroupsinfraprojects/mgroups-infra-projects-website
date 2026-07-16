from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_oversized_legacy_window_settings_are_reset() -> None:
    text = (ROOT / "app/ui/main_window.py").read_text(encoding="utf-8")
    assert 'if size_text in {"1920 x 1080", "Fullscreen"}' in text
    assert 'size_text = "Normal 1366 x 768"' in text
    assert 'self.settings.setValue("display/window_size", size_text)' in text


def test_window_resize_is_centered_and_safe() -> None:
    text = (ROOT / "app/ui/main_window.py").read_text(encoding="utf-8")
    assert "def _resize_safely" in text
    assert "def _center_on_screen" in text
    assert "geometry.width() - 120" in text
    assert "geometry.height() - 120" in text


def test_settings_do_not_offer_accidental_fullscreen_startup() -> None:
    text = (ROOT / "app/ui/views/settings_view.py").read_text(encoding="utf-8")
    assert "Normal 1366 x 768" in text
    assert "Fit screen" in text
    assert "1920 x 1080" not in text
    assert "Fullscreen" not in text
