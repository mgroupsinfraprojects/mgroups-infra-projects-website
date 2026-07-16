from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel


STATUS_LABELS: dict[str, tuple[str, str]] = {
    "FULLY_VERIFIED": ("Fully Verified", "success"),
    "BALANCED_BUT_REVIEW_REQUIRED": ("Balanced — Review Required", "warning"),
    "AMOUNT_RECONCILIATION_FAILED": ("Amount Mismatch", "danger"),
    "ROW_COVERAGE_FAILED": ("Row Coverage Failed", "danger"),
    "APPROVED": ("Approved", "success"),
    "VALID": ("Valid", "success"),
    "ACCEPTED": ("Accepted", "success"),
    "REVIEW_REQUIRED": ("Review Required", "warning"),
    "WARNING": ("Warning", "warning"),
    "SKIPPED": ("Skipped", "neutral"),
    "DUPLICATE": ("Duplicate", "neutral"),
    "GST_MISMATCH": ("GST Mismatch", "warning"),
    "ERROR": ("Error", "danger"),
    "EXCLUDED": ("Excluded", "neutral"),
    "INFO": ("Information", "info"),
}

SEVERITY_ALIASES: dict[str, str] = {
    "error": "danger",
    "failed": "danger",
    "invalid": "danger",
    "review": "warning",
    "warn": "warning",
    "ok": "success",
    "approved": "success",
}


def friendly_status(status: str | None) -> tuple[str, str]:
    """Return a professional human-readable label and visual severity."""
    raw = (status or "").strip().upper()
    if raw in STATUS_LABELS:
        return STATUS_LABELS[raw]
    display = raw.replace("_", " ").title() if raw else "No Status"
    if "REVIEW" in raw or "WARNING" in raw:
        return (display, "warning")
    if "ERROR" in raw or "FAILED" in raw or "INVALID" in raw or "MISMATCH" in raw:
        return (display, "danger")
    if "APPROVED" in raw or "VALID" in raw or "ACCEPTED" in raw or "VERIFIED" in raw:
        return (display, "success")
    return (display, "neutral")


class StatusChip(QLabel):
    """Pill-shaped professional status indicator.

    The widget stores its visual state as Qt properties. That keeps it compatible
    with the runtime theme manager instead of hardcoding one light-only palette.
    """

    def __init__(self, text: str = "", severity: str | None = None, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("StatusChip")
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumHeight(28)
        if severity is None:
            self.set_status(text)
        else:
            self.set_chip(text, severity)

    def set_chip(self, text: str, severity: str = "neutral") -> None:
        severity_key = SEVERITY_ALIASES.get(severity.lower(), severity.lower())
        if severity_key not in {"success", "warning", "danger", "info", "neutral"}:
            severity_key = "neutral"
        self.setText(text)
        self.setProperty("variant", severity_key)
        self._refresh_style()

    def set_status(self, status: str) -> None:
        label, severity = friendly_status(status)
        self.set_chip(label, severity)

    def _refresh_style(self) -> None:
        style = self.style()
        style.unpolish(self)
        style.polish(self)
