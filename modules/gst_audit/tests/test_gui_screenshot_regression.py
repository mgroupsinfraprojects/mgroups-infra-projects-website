from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from datetime import date

import pytest

pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from PySide6.QtCore import Qt

from app.core.models import AuditResult, AuditSummary, InvoiceRow
from app.ui.main_window import MainWindow


ARTIFACT_DIR = Path(__file__).resolve().parents[1] / "artifacts" / "screenshots"


def _sample_result() -> AuditResult:
    rows = [
        InvoiceRow(
            row_id=1,
            source_file="jan_upload.xlsx",
            sheet_name="Sheet1",
            excel_row_number=2,
            raw_snapshot=[],
            supplier_name="ALAMPATA",
            gstin="29ABLFA6396D1Z2",
            invoice_no="A-001",
            invoice_date=date(2026, 1, 10),
            taxable_value=Decimal("331915.50"),
            cgst=Decimal("29872.38"),
            sgst=Decimal("29872.37"),
            invoice_value=Decimal("391663.00"),
            expected_invoice_value=Decimal("391660.25"),
            difference_amount=Decimal("2.75"),
            mismatch_reason="SMALL_PERCENTAGE_ROUNDING",
            audit_status="VALID",
            audit_severity="LOW",
            review_required=False,
            include_in_totals=True,
        ),
        InvoiceRow(
            row_id=2,
            source_file="dec_upload.xlsx",
            sheet_name="Sheet1",
            excel_row_number=3,
            raw_snapshot=[],
            supplier_name="RR ROOFING",
            gstin="33ABCDE1234F1Z5",
            invoice_no="R-102",
            invoice_date=date(2025, 12, 8),
            taxable_value=Decimal("50000.00"),
            cgst=Decimal("4500.00"),
            sgst=Decimal("4500.00"),
            invoice_value=Decimal("59000.00"),
            expected_invoice_value=Decimal("59000.00"),
            mismatch_reason="BALANCED_OR_ROUNDING",
            audit_status="REVIEW_REQUIRED",
            audit_severity="MEDIUM",
            review_required=True,
            include_in_totals=False,
        ),
    ]
    summary = AuditSummary(
        files_processed=2,
        raw_rows_read=2,
        classified_rows=2,
        valid_rows=1,
        review_required_rows=1,
        final_approved_rows=1,
        approved_invoice_value=Decimal("391663.00"),
        approved_taxable_value=Decimal("331915.50"),
        approved_cgst=Decimal("29872.38"),
        approved_sgst=Decimal("29872.37"),
        approved_total_gst=Decimal("59744.75"),
        row_coverage_status="MATCHED",
        amount_reconciliation_status="MATCHED",
        final_status="BALANCED_REVIEW_REQUIRED",
    )
    return AuditResult(rows=rows, summary=summary, source_totals={}, month_totals={}, supplier_totals={})


def _grab_widget(widget, name: str) -> Path:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    path = ARTIFACT_DIR / name
    pixmap = widget.grab()
    assert not pixmap.isNull()
    assert pixmap.width() >= 900
    assert pixmap.height() >= 550
    assert pixmap.save(str(path))
    assert path.exists() and path.stat().st_size > 10_000
    return path


def test_dashboard_screenshot_regression_light_layout(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.resize(1366, 768)
    window.result = _sample_result()
    window.current_rows = window.result.rows
    window._refresh_dashboard_guided_filter_options()
    window.apply_dashboard_filter()
    window.show()
    qtbot.waitExposed(window, timeout=2000)
    qtbot.wait(100)
    _grab_widget(window, "dashboard_light_1366x768.png")


def test_guided_filter_popup_screenshot_is_not_black(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.resize(1366, 768)
    window.result = _sample_result()
    window.current_rows = window.result.rows
    window._refresh_dashboard_guided_filter_options()
    window.apply_dashboard_filter()
    window.show()
    qtbot.waitExposed(window, timeout=2000)
    selector = window.dashboard_search_selector
    selector.search_edit.setFocus()
    qtbot.keyClicks(selector.search_edit, "AL")
    qtbot.waitUntil(lambda: selector._inline_popup.isVisible(), timeout=1000)
    popup = selector._inline_popup
    path = _grab_widget(popup, "guided_filter_popup.png")
    # A black rendering defect produces a suspiciously tiny or flat screenshot;
    # file-size plus non-null dimensions catch that regression without binding
    # the test to exact pixel colors across Windows display scaling modes.
    assert path.stat().st_size > 3_000


def test_full_value_picker_screenshot_is_not_black(qtbot):
    from app.ui.widgets.guided_filter import _FloatingValuePicker

    picker = _FloatingValuePicker("Search or select company...")
    qtbot.addWidget(picker)
    picker.set_data(
        ["ALAMPATA", "RR ROOFING", "SARANYA", "DHASVANTHSAI"],
        {"ALAMPATA": 8, "RR ROOFING": 4, "SARANYA": 9, "DHASVANTHSAI": 36},
        {"ALAMPATA"},
        "A",
    )
    picker.resize(520, 320)
    picker.show()
    qtbot.waitExposed(picker, timeout=2000)
    qtbot.wait(100)
    path = _grab_widget(picker, "full_value_picker.png")
    assert path.stat().st_size > 5_000
