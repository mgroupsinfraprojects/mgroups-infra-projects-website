# GST Invoice Audit Desktop — Clean Folder Structure

This release keeps the original runtime imports intact while documenting the project in a clean frontend/backend-style structure. The executable code remains under `app/` because changing import paths at this stage would risk breaking a working audited release.

## Top-level layout

```text
gst_invoice_audit_desktop/
├── main.py                         # Application entry point
├── app/                            # Runtime application package
│   ├── ui/                         # Frontend layer: PySide6 windows, views, widgets, controllers
│   ├── core/                       # Backend/domain layer: audit engine, GST logic, DB, export, security
│   ├── assets/                     # Frontend assets: icons, screenshots, QSS styles
│   ├── resources/                  # Runtime style resources
│   └── version.py                  # Single source of version/build metadata
├── tests/                          # Automated quality checks and regression tests
├── scripts/                        # Developer/QA utility scripts
├── docs/                           # Architecture, workflow, release, and validation documents
├── requirements.txt                # Runtime Python dependencies
├── pyproject.toml                  # Build/tool configuration
├── pytest.ini                      # Test configuration
├── GSTInvoiceAudit.spec            # PyInstaller build specification
├── build_exe.bat                   # Windows EXE build helper
```

## Logical frontend/backend map

| Logical layer | Actual folder | Meaning |
|---|---|---|
| Frontend | `app/ui/` | Desktop GUI: main window, pages, widgets, guided search, dashboard charts, theme handling. |
| Backend / domain | `app/core/` | GST audit engine, invoice parsing, duplicate checks, credit notes, GSTIN validation, reconciliation, export, persistence. |
| Assets | `app/assets/` | Icons, preview screenshots, QSS style sheets. |
| Shared runtime | `app/version.py`, `app/resources/` | Version metadata and runtime resources used by frontend/backend. |
| QA | `tests/` | Unit, integration, source-contract, GUI-contract, export, and real-data hardening tests. |
| Tools | `scripts/` | Smoke tests, release verification, real-data test runner, GUI smoke test. |
| Documentation | `docs/` | Architecture, workflow, hardening notes, scorecards, deployment gap lists. |
| Deployment | `GSTInvoiceAudit.spec`, `build_exe.bat`, `START_GST_AUDIT_PRO.bat` | Windows packaging and execution helpers. |

## Why the code was not physically moved to `frontend/` and `backend/`

The project already has a clean internal split:

- `app/ui` is the frontend.
- `app/core` is the backend.

Physically renaming these folders to `frontend` and `backend` would require changing many imports, tests, and PyInstaller packaging rules. That creates risk without improving runtime correctness. The safer professional structure is to preserve the working package layout and document the architectural roles clearly.

## Recommended future rename path, only if needed

If a future major version wants physical folder names, do it as a breaking refactor:

```text
src/gst_audit/
├── frontend/       # former app/ui
├── backend/        # former app/core
├── assets/         # former app/assets
├── shared/         # version/resources/config shared between layers
└── main.py
```

Do this only after adding import-compatibility wrappers and running the full test suite plus Windows EXE validation.

## v9.7 enforcement additions

v9.7 adds test-protected architecture guides without moving runtime code:

| Guide/package | Runtime target | Purpose |
|---|---|---|
| `frontend/` | `app/ui/` | Explicit frontend compatibility/guide package. |
| `backend/` | `app/core/` | Explicit backend/domain compatibility/guide package. |
| `data_layer/` | `app/core/database.py`, `app/core/models.py` | Persistence and row-model boundary guide. |
| `security_layer/` | `app/core/security.py`, database hash-chain code | RBAC/encryption/hash-chain boundary guide. |
| `quality/` | `tests/`, `scripts/` | Architecture and QA rules. |
| `deployment/` | build/spec/release checklist | Packaging and release rules. |
