# Ownership and Folder Boundaries

## `app/core/` — backend/domain layer

Allowed:
- GST invoice parsing and classification
- Decimal financial calculations
- duplicate detection and recalculation
- GSTIN/HSN/date/invoice-number validation
- reconciliation and totals
- export generation and SQLite persistence
- security helpers used by persistence/export

Forbidden:
- `PySide6` imports
- `QMessageBox`, `QWidget`, `QDialog`, or UI widgets
- direct user interaction or GUI rendering
- importing `app.ui`

## `app/ui/` — frontend layer

Allowed:
- PySide6 windows, pages, widgets, dialogs, and theme management
- user actions, guided search/filtering, upload screens, dashboard display
- calling backend services from `app.core`

Forbidden:
- duplicating financial rules already implemented in `app.core`
- direct mutation of audit rows outside approved model/controller methods

## `app/assets/` and `app/resources/`

Allowed:
- icons, QSS styles, preview images, packaged UI resources

Forbidden:
- business logic
- generated local screenshots from test runs

## `tests/`

Allowed:
- unit, integration, architecture-boundary, GUI-contract, and release-cleanliness tests

Forbidden:
- relying on local absolute machine paths
- checking stale hard-coded version numbers when `app.version.APP_VERSION` exists

## `scripts/`

Allowed:
- smoke tests, release verification, developer command entrypoints, build helpers

Forbidden:
- production business logic required by the application at runtime
