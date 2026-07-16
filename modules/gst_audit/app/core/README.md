# `app/core/` — Backend / Domain Layer

Business logic for GST invoice audit. This layer should stay independent from the GUI.

## Main responsibility

- XLS/XLSX/CSV import
- GST portal header and field detection
- Decimal-safe money parsing
- GSTIN validation
- Duplicate detection
- Credit/debit note handling
- Review-required classification
- Supplier anomaly and invoice-gap annotations
- GSTR reconciliation helpers
- SQLite persistence
- Excel report export
- Security helpers, RBAC, encryption utility functions
