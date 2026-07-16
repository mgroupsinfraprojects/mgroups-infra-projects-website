# Architecture

```text
GST Invoice Audit Software
│
├── PySide6 Desktop UI
│   ├── Upload Files
│   ├── Dashboard
│   ├── Audit Rows
│   ├── Supplier / GSTIN Search
│   ├── Reconciliation Matrix
│   └── Verified Export
│
├── Python Audit Engine
│   ├── Excel Reader
│   ├── Header Detector
│   ├── GSTIN Regex Detector
│   ├── Date Parser
│   ├── Row Reconstruction Logic
│   ├── GST Formula Validator
│   ├── Duplicate Detector
│   └── Reconciliation Engine
│
├── SQLite Storage Layer
│   ├── datasets
│   └── invoice_rows
│
└── Export Layer
    ├── Verified Excel
    ├── Review Required Rows
    ├── Skipped Rows
    ├── GST Mismatch Report
    ├── Supplier Summary
    └── Source Reconciliation
```

## Design Rule

The dashboard never directly trusts raw Excel values. Data passes through:

```text
Raw Row → Detected Fields → Validation → Review Decision → Approved Dashboard Total
```
