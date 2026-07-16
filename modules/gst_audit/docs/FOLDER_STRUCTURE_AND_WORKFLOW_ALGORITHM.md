# Folder Structure and Workflow Algorithm

This project uses two levels of structure:

1. **Real runtime packages** under `app/`. These are the files imported by the application.
2. **Readable layer folders** such as `frontend/`, `backend/`, `data_layer/`, and `security_layer/`. These are compatibility/guide folders that point developers to the correct runtime package without breaking the existing imports.

## Clean folder structure

```text
gst_invoice_audit_desktop/
├── app/                         # Real application code used at runtime
│   ├── core/                    # Backend/domain logic: audit engine, parsing, validation, export
│   ├── ui/                      # Frontend desktop UI: PySide6 screens, widgets, controllers
│   ├── assets/                  # QSS themes, preview images, static UI assets
│   ├── resources/               # Runtime resource files
│   └── version.py               # Single source for app name/version/release metadata
│
├── frontend/                    # Human-readable frontend layer map; points to app/ui
├── backend/                     # Human-readable backend layer map; points to app/core
├── data_layer/                  # Data/persistence map; points to SQLite/database code
├── security_layer/              # Security map; points to security utilities and deployment gaps
├── deployment/                  # Release/deployment checklist and packaging notes
├── documentation/               # User-facing documentation pointer
├── quality/                     # Architecture rules and test matrix
├── docs/                        # Full engineering documentation, ADRs, scorecards, workflows
├── scripts/                     # Developer commands: test, verify, clean, compile, smoke
├── tests/                       # Unit, integration, GUI-contract, packaging, and architecture tests
├── tools/                       # Helper scripts for development/release support
├── pyproject.toml               # Python package metadata and test config
└── README.md                    # Main project entry point
```

## Meaning of each main layer

| Layer | Folder | Meaning | Should contain | Must not contain |
|---|---|---|---|---|
| Frontend | `app/ui/` | User interface and interaction layer | PySide6 pages, widgets, theme manager, controller glue, background worker | GST calculation rules, duplicate logic, database SQL |
| Backend/domain | `app/core/` | Audit correctness and business rules | parsing, GSTIN validation, mismatch classification, duplicate detection, summaries, export logic | PySide6 imports, window code, visual styling |
| Data layer | `app/core/database.py` and `data_layer/` | SQLite persistence and saved review decisions | dataset storage, row storage, review updates, schema/version handling | UI widgets or dashboard rendering |
| Security layer | `app/core/security.py` and `security_layer/` | Safety checks and deployment security notes | file checks, path safety, limits, security documentation | business totals or UI layout |
| Quality | `tests/`, `quality/`, `scripts/verify_release.py` | Prevent regressions | tests, architecture rules, release cleanliness checks | application runtime logic |
| Documentation | `docs/`, `documentation/` | Explain design, operation, limitations | architecture, workflow, scorecards, release notes | executable business logic |

## Runtime workflow algorithm

```text
1. User selects Excel/CSV files
   └── app/ui/views/upload_view.py
       calls MainWindow.select_files()

2. User clicks Start Audit
   └── MainWindow.process_files()
       creates ProcessingWorker in app/ui/processing_worker.py

3. Background worker runs backend engine
   └── app/core/audit_engine.py
       reads XLSX/CSV safely
       detects headers
       parses invoice rows
       validates GSTIN/HSN/date/money fields
       classifies row status and mismatch reason
       detects duplicates
       annotates invoice gaps and supplier anomalies
       builds AuditResult and AuditSummary

4. Result is persisted
   └── app/core/database.py
       saves dataset, rows, summary, review decisions

5. UI refreshes all pages
   ├── Dashboard: totals, charts, supplier drill-down
   ├── Audit Rows: review queue and row detail panel
   ├── Suppliers: GSTIN/supplier aggregation
   ├── Reconciliation: row coverage and amount cross-check cards
   └── Export: preview of the report package

6. User applies manual review decisions
   └── MainWindow.set_selected_review_decision()
       opens structured decision dialog
       applies InvoiceRow.apply_review_decision()
       writes review decision to SQLite
       recalculates result safely through audit engine
       refreshes dashboard/reconciliation/export totals

7. User exports verified report
   └── app/core/exporter.py
       creates Excel workbook with summary, verified rows, mismatch details,
       supplier/month summaries, source totals, reconciliation, and charts
```

## Rule for future developers

Do not move runtime files only to make folders look cleaner. Keep working imports stable. Add readable layer folders as maps, and enforce boundaries with tests.
