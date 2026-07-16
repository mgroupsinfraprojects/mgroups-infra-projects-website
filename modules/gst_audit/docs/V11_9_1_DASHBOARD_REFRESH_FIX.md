# V11.9.1 Dashboard Refresh + Lag Fix

## Fixed

- Dashboard metric cards now update before charts and hidden decision widgets.
- Dashboard refresh is exception-safe; if charts or drill-down fail, visible totals still show.
- Review decisions no longer trigger full app-wide refresh of every table and chart.
- F5/load refresh now performs a targeted current-page refresh to reduce UI lag.
- Regression tests aligned with V11.9 threshold policy: GST mismatches below the configured `gst_critical_amount` remain advisory/trace instead of blocking Critical Review.

## Validation

- `pytest -q`: 204 passed.
- `python3 -m compileall`: passed.
- `python3 scripts/verify_release.py`: passed.
- `python3 scripts/dev.py release-check`: passed.

## Known boundary

GUI rendering was not visually run in the Linux validation environment because PySide6 is a Windows/desktop dependency and is not installed in the sandbox. The patch is source-level and regression-tested; run `START_GST_AUDIT_PRO.bat` on Windows with Python 3.11/3.12 for final visual confirmation.
