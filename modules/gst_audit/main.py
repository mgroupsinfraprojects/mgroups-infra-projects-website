from __future__ import annotations

import sys
from PySide6.QtWidgets import QApplication

from app.core.branding import load_branding_file
from app.core.logging_config import setup_logging
from app.ui.main_window import MainWindow


def main() -> int:
    setup_logging()
    app = QApplication(sys.argv)
    app.setApplicationName(load_branding_file().app_name)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
