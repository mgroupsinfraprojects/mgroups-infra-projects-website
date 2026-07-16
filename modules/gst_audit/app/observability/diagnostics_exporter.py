from __future__ import annotations

import platform
from app.version import APP_VERSION


def build_diagnostics() -> dict:
    return {"app_version": APP_VERSION, "python": platform.python_version(), "os": platform.platform()}
