# Production Hardening Fixes

This version addresses the strict review findings that kept the previous desktop prototype at production score 78/100.

## Fixed critical issues

1. **UI freeze risk reduced**
   - Excel processing now runs in `ProcessingWorker`, a `QThread` subclass.
   - Main Qt thread remains available for repainting, progress updates, and cancellation request.

2. **Regression tests added**
   - `tests/test_core_audit.py` contains 11 pytest tests covering money parsing, INR formatting, GSTIN checksum, mismatch classification, summary reconciliation, duplicate exclusion, SQLite persistence, export creation, and synthetic Excel processing.

3. **SQLite connection cleanup added**
   - `AuditDatabase.close()` is idempotent.
   - `MainWindow.closeEvent()` closes the database on app exit.
   - Worker-created database connections are closed in `finally`.

## Fixed major issues

1. **GSTIN checksum validation**
   - GSTIN validation now performs both regex validation and official mod-36 checksum validation.

2. **Progress indicator**
   - Processing displays `QProgressDialog` with live status text.

3. **Export formatting**
   - Verified Excel export now includes frozen panes, title row, styled headers, autofilter, money/date/text formatting, and automatic column widths.

4. **Encapsulation improved**
   - UI now uses public engine methods: `build_result_from_rows()`, `recalculate_result()`, `group_totals()`, and `month_totals()`.
   - Private aliases remain only for backward compatibility with older scripts.

5. **Logging added**
   - Logs are written to `logs/gst_invoice_audit.log`.

## Build-time gates

`build_exe.bat` now runs before PyInstaller:

```bat
python scripts\smoke_test_processor.py --self-check
python scripts\gui_smoke_test.py
python -m pytest
```

The EXE build stops if any of these fail.


## V3 minor hardening fixes

- Removed pandas boolean `== True` comparisons in exporter.
- Merged Excel export title row across all columns.
- Added `pyproject.toml` with Python `>=3.11,<3.13` constraint.
- Moved non-supplier metadata tokens into `NON_SUPPLIER_TOKENS`.
- Added row-level logging for GSTIN validation failures, reconstruction events, and duplicate exclusions.
- Enabled pytest coverage reporting with `pytest-cov`.
