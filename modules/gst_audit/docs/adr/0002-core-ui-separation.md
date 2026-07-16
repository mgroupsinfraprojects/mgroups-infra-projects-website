# ADR 0002 — Core must not depend on UI

## Decision

`app/core` must not import `app.ui` or PySide6.

## Context

The audit engine must be testable without the desktop GUI. Financial correctness, duplicate detection,
CSV/XLSX parsing, and export logic must work in headless environments.

## Consequences

- Core tests run without Qt.
- GUI failures do not invalidate financial calculations.
- Future service/API reuse remains possible.
