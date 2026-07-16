from __future__ import annotations

import importlib.util
import os
import platform
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_MODULES = [
    "pandas",
    "openpyxl",
    "xlsxwriter",
    "PySide6",
    "cryptography",
    "xlrd",
]


def check_module(name: str) -> tuple[bool, str]:
    spec = importlib.util.find_spec(name)
    if spec is None:
        return False, f"Missing Python dependency: {name}"
    return True, f"Dependency available: {name}"


def check_write_location() -> tuple[bool, str]:
    try:
        with tempfile.NamedTemporaryFile(prefix="gst_preflight_", suffix=".tmp", delete=False) as tmp:
            tmp.write(b"ok")
            path = Path(tmp.name)
        path.unlink(missing_ok=True)
        return True, f"Temp write permission OK: {tempfile.gettempdir()}"
    except Exception as exc:  # pragma: no cover - environment-specific
        return False, f"Temp write permission failed: {exc}"


def check_startup_import() -> tuple[bool, str]:
    try:
        sys.path.insert(0, str(ROOT))
        from app.version import APP_NAME, APP_VERSION  # noqa: F401
        from app.ui.main_window import MainWindow  # noqa: F401
        return True, f"Startup import OK: {APP_NAME} v{APP_VERSION}"
    except Exception as exc:
        return False, f"Startup import failed: {exc.__class__.__name__}: {exc}"


def main() -> int:
    print("GST Audit Pro Windows/source preflight")
    print(f"Python: {sys.version.split()[0]}")
    print(f"Platform: {platform.platform()}")
    print(f"Project root: {ROOT}")
    print("")

    checks: list[tuple[bool, str]] = []
    checks.append(((3, 11) <= sys.version_info[:2] < (3, 13), "Python version OK: 3.11/3.12" if (3, 11) <= sys.version_info[:2] < (3, 13) else "Python 3.11 or 3.12 required"))
    for module in REQUIRED_MODULES:
        checks.append(check_module(module))
    checks.append(check_write_location())
    checks.append(check_startup_import())

    failed = False
    for ok, msg in checks:
        print(("[PASS] " if ok else "[FAIL] ") + msg)
        failed = failed or not ok

    if failed:
        print("\nPreflight failed. Install requirements first:")
        print("  python -m pip install -r requirements.txt")
        return 1

    print("\nPreflight passed. You can run:")
    print("  python main.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
