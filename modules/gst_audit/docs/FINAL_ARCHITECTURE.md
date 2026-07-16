# Final Architecture

```text
GST Invoice Audit Desktop Software
│
├── PySide6 UI Layer
│   ├── Upload
│   ├── Dashboard
│   ├── Audit Rows
│   ├── Supplier / GSTIN Search
│   ├── Reconciliation Matrix
│   ├── Export
│   └── Theme & Display Settings
│
├── Audit Engine
│   ├── Excel Reader
│   ├── Header Detector
│   ├── GSTIN Regex Detector
│   ├── Date Parser
│   ├── Row Reconstruction
│   ├── GST Mismatch Classifier
│   ├── Duplicate Detector
│   └── Summary Builder
│
├── Persistence Layer
│   ├── SQLite database
│   ├── Dataset records
│   ├── Invoice row records
│   └── Review decision history
│
└── Export Layer
    ├── Verified Excel
    ├── Approved Rows
    ├── Review Required Rows
    ├── Skipped Rows
    ├── GST Mismatch Report
    ├── Supplier Summary
    ├── Source Reconciliation
    └── Month Reconciliation
```
