from __future__ import annotations

import importlib
from pathlib import Path

from app.version import APP_VERSION

ROOT = Path(__file__).resolve().parents[1]


def test_v991_version_and_one_click_launcher_are_present() -> None:
    assert APP_VERSION == "11.13.0"
    assert (ROOT / "START_GST_AUDIT_PRO.bat").exists()
    launcher = (ROOT / "START_GST_AUDIT_PRO.bat").read_text(encoding="utf-8")
    assert "py -3.11" in launcher
    assert "py -3.12" in launcher
    assert "Installing missing required packages" in launcher
    assert "pip install -r requirements.txt" in launcher


def test_app_ui_widgets_package_is_import_safe_without_eager_widget_resolution() -> None:
    widgets = importlib.import_module("app.ui.widgets")
    assert "MetricCard" in widgets.__all__
    assert "SearchByValueMultiSelect" in widgets.__all__
    source = (ROOT / "app" / "ui" / "widgets" / "__init__.py").read_text(encoding="utf-8")
    assert "from PySide6" not in source
    assert "import PySide6" not in source


def test_single_user_launcher_is_not_a_wrapper() -> None:
    launcher_path = ROOT / "START_GST_AUDIT_PRO.bat"
    assert launcher_path.exists()
    assert not (ROOT / "run_app.bat").exists()
    text = launcher_path.read_text(encoding="utf-8")
    assert 'call "%~dp0run_app.bat"' not in text
    assert "python.exe" in text
    assert r"scripts\preflight_windows.py" in text
    assert "main.py" in text
