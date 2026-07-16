from __future__ import annotations

import traceback
from pathlib import Path
from typing import List

from PySide6.QtCore import QThread, Signal

from app.core.audit_engine import InvoiceAuditEngine
from app.core.database import AuditDatabase
from app.core.models import AuditResult


class ProcessingWorker(QThread):
    """Background worker so large Excel processing never blocks the UI thread."""

    progress_changed = Signal(int, str)
    result_ready = Signal(object, int, str)  # AuditResult, dataset_id, dataset_name
    failed = Signal(str)

    def __init__(self, file_paths: List[str], ignored_gstins: List[str] | None = None, self_gstins: List[str] | None = None, parent=None) -> None:
        super().__init__(parent)
        self.file_paths = file_paths
        self.ignored_gstins = ignored_gstins or []
        self.self_gstins = self_gstins or []

    def run(self) -> None:
        try:
            engine = InvoiceAuditEngine()

            def progress(percent: int, message: str) -> None:
                if self.isInterruptionRequested():
                    raise RuntimeError("Processing cancelled by user")
                self.progress_changed.emit(percent, message)

            result: AuditResult = engine.process_files(
                self.file_paths,
                progress_callback=progress,
                ignored_gstins=self.ignored_gstins,
                self_gstins=self.self_gstins,
            )
            dataset_name = "GST Audit - " + ", ".join(Path(f).name for f in self.file_paths[:3])
            if len(self.file_paths) > 3:
                dataset_name += f" + {len(self.file_paths) - 3} more"
            db = AuditDatabase()
            try:
                dataset_id = db.save_result(dataset_name, result.summary.to_dict(), result.rows)
            finally:
                db.close()
            self.result_ready.emit(result, dataset_id, dataset_name)
        except Exception as exc:  # pragma: no cover - surfaced to GUI
            detail = f"{exc}\n\n{traceback.format_exc()}"
            self.failed.emit(detail)
