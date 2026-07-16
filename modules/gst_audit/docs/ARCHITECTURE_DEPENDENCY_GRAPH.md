# Architecture Dependency Graph

This project is a desktop application, but it follows layered architecture rules.
The runtime package remains `app/` to preserve working imports and packaging.
The logical architecture is:

```text
frontend / app.ui
        ↓
controllers / app.ui.controllers
        ↓
backend / app.core
        ↓
models + money + gstin + date_parser

exporter   ← app.core audit result objects
persistence← app.core.database
security   ← app.core.security + database review hash chain
assets     ← app.ui only
```

## Allowed dependency directions

| From | May import | Must not import |
|---|---|---|
| `app.ui` | `app.core`, PySide6, assets | low-level test utilities |
| `app.core` | Python stdlib, pandas/openpyxl, app.core modules | `app.ui`, PySide6 widgets/dialogs |
| `app.core.exporter` | `app.core.models`, xlsxwriter/openpyxl | `app.ui` |
| `app.core.database` | `app.core.models`, sqlite3, security helpers | `app.ui` |
| `app.core.security` | stdlib/cryptography | `app.ui` |
| `tests` | all project modules | production-only secrets |

## Boundary principle

Business rules must be runnable without Qt. The audit engine, money parsing,
GSTIN validation, duplicate detection, credit/debit-note handling, reconciliation,
CSV/XLSX parsing, and export logic must not depend on desktop widgets.
