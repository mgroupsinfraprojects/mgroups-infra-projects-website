# ADR 0005 — Keep guided search as a UI component, not a core rule

## Decision

Guided search/filter widgets remain in `app.ui.widgets` and controller/view code.

## Context

Search/filter interaction is a frontend concern. The core engine should only process audit data and expose row fields/totals.

## Consequences

- Search UX can evolve without changing audit calculations.
- Core financial tests remain independent of popup and widget behavior.
