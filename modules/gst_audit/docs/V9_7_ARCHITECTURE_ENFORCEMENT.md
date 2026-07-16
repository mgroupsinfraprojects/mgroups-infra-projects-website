# Architecture Enforcement — Current Contract

This document is retained because the automated release tests require it as a public architecture contract.

## Runtime root

`app/` is the runtime application package. The desktop app must start from `main.py` and must not require historical/training folders.

## Boundaries

| Layer | Allowed responsibility | Forbidden dependency |
|---|---|---|
| `app.core` | parsing, GST validation, reconciliation, export models, persistence helpers | `PySide6`, `app.ui` |
| `app.ui` | PySide6 widgets, pages, controllers, theme application | direct financial rule mutation without core model update |
| `scripts` | preflight, release checks, sample-data validation, build helpers | user-facing runtime logic |
| `config` | editable branding/navigation identity | executable code |

## Required enforcement

- `scripts/verify_release.py` scans Python imports and blocks `app.core` from importing `PySide6` or `app.ui`.
- `tests/test_v9_7_architecture_enforcement.py` validates public docs, package boundaries, and release checklist presence.
- Public facade packages must import cleanly or be removed.

## Current v9.9.2 additions

- Product name and navigation labels are separated into `config/app_identity.json` plus `app.core.branding`.
- Settings UI can override identity, theme, density, startup size, and GSTIN rules without Python edits.
- Build now runs the full `scripts/dev.py release-check` gate before EXE creation.
