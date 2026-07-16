from __future__ import annotations

import logging
from pathlib import Path


def setup_logging(log_path: Path | str | None = None) -> Path:
    """Configure app logging once and return the log file path."""
    if log_path is None:
        log_dir = Path.cwd() / "logs"
        log_path = log_dir / "gst_invoice_audit.log"
    else:
        log_path = Path(log_path)
        log_dir = log_path.parent
    log_dir.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    if root.handlers:
        return log_path
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.FileHandler(log_path, encoding="utf-8"), logging.StreamHandler()],
    )
    return log_path
