# ADR 0001 — Keep `app/` as the runtime root

## Decision

Keep the working runtime package as `app/`.

## Context

The application already uses imports such as `app.core.audit_engine` and `app.ui.main_window`.
Physically moving these packages to top-level `frontend/` and `backend/` would risk breaking tests,
PyInstaller packaging, and existing launch scripts.

## Alternatives considered

1. Move `app/ui` to `frontend` and `app/core` to `backend`.
2. Keep `app/` and document logical frontend/backend boundaries.
3. Add compatibility packages while preserving runtime imports.

## Chosen approach

Use option 3: preserve `app/`, add documented guide/compatibility packages, and enforce the boundaries with tests.

## Consequences

- Runtime stability is preserved.
- New developers still get clear frontend/backend terminology.
- Architecture violations can be detected automatically.
