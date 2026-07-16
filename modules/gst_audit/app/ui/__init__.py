"""PySide6 user-interface package.

The package avoids importing PySide6 at module-import time so non-GUI release
checks, facade imports, and core tests can run on headless machines.  Accessing
``app.ui.MainWindow`` still performs the real GUI import lazily.
"""

from __future__ import annotations

from typing import Any

__all__ = ["MainWindow"]


def __getattr__(name: str) -> Any:
    if name == "MainWindow":
        from app.ui.main_window import MainWindow

        return MainWindow
    raise AttributeError(name)
