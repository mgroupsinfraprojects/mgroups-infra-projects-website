# ADR 0003 — Exporter reads audit results and does not own audit rules

## Decision

The report/export layer may format audit results, but it must not redefine financial rules.

## Context

If export logic recalculates totals differently from the audit engine, Excel reports can diverge from dashboard/database values.

## Consequences

- Audit rules stay in `app.core.audit_engine` and supporting core modules.
- Exporter receives already-classified rows and summaries.
- Regression tests can compare dashboard, engine, and export totals consistently.
