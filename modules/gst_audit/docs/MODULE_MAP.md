# Module Map

## Frontend: `app/ui/`

| Module/folder | Purpose |
|---|---|
| `main_window.py` | Main PySide6 shell, sidebar, stacked pages, window-level events. |
| `controllers/dashboard_controller.py` | Bridges user actions, audit results, filters, and dashboard state. |
| `views/` | Page-level UI screens: dashboard, upload, audit, suppliers, reconciliation, export, settings. |
| `widgets/` | Reusable UI components: guided search, picker popup, data table, charts, metric cards, chips, toast, empty states. |
| `processing_worker.py` | Background QThread worker for non-blocking file processing. |
| `theme_manager.py` | Theme, style, display, and QSS control. |

## Backend/domain: `app/core/`

| Module | Purpose |
|---|---|
| `audit_engine.py` | Main GST file processing engine: Excel/CSV parsing, row classification, duplicate detection, annotations, recalculation. |
| `models.py` | Dataclasses for rows, summaries, totals, processing results, and validation state. |
| `exporter.py` | Excel export, executive summary, compact/full report sheets, formula-injection protection. |
| `database.py` | SQLite persistence, review decisions, hash-chain/audit state. |
| `gstin.py` | GSTIN validation and checksum logic. |
| `gst_compliance.py` | GST compliance classifications and mismatch reasoning. |
| `gstr_reconciliation.py` | GSTR/book reconciliation helpers. |
| `header_detector.py`, `field_detector.py` | GST portal/header/field mapping logic. |
| `money.py` | Decimal-safe INR parsing and financial conversion. |
| `date_parser.py` | Robust date parsing for GST files. |
| `invoice_number.py` | Invoice sequence extraction and gap-related utilities. |
| `analytics.py` | Dashboard totals and analytical summaries. |
| `security.py` | RBAC model, encryption helpers, hashing, hash-chain verification. |
| `import_profiles.py` | GST/GSTR import profile definitions and aliases. |
| `performance.py` | Performance guardrails and limits. |
| `logging_config.py` | Logging setup. |

## Quality: `tests/`

| Test group | Purpose |
|---|---|
| `test_core_audit.py` | Main engine regression coverage. |
| `test_v9_*` | Version-specific correctness fixes and regression locks. |
| `test_gui_*`, `test_dashboard_*` | GUI/layout/source-contract validation. |
| `test_release_packaging.py` | Release hygiene checks. |
| `test_gstr_reconciliation_and_formats.py` | GSTR reconciliation and format-specific checks. |

## Tools: `scripts/`

| Script | Purpose |
|---|---|
| `smoke_test_processor.py` | Minimal engine smoke test with reconciliation checks. |
| `verify_release.py` | Release package hygiene verification. |
| `run_real_data_v91.py` | Real-data processing harness retained for regression use. |
| `gui_smoke_test.py` | Basic GUI startup smoke test. |

## v9.7 logical compatibility packages

| Package | Points to | Purpose |
|---|---|---|
| `frontend` | `app.ui` | Makes the frontend layer explicit without breaking existing imports. |
| `backend` | `app.core` | Makes the backend/domain layer explicit without breaking existing imports. |
| `data_layer` | `app.core.database`, `app.core.models` | Documents persistence/model ownership. |
| `security_layer` | `app.core.security` | Documents RBAC/encryption/hash-chain ownership. |
