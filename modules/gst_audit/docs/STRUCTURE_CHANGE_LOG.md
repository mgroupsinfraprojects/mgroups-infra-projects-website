# Structure Cleanup Change Log

## What changed

- Added `docs/FOLDER_STRUCTURE.md` for complete folder explanation.
- Added `docs/MODULE_MAP.md` for file-by-file module meaning.
- Added `docs/DEVELOPER_ONBOARDING.md` for run/test/build instructions.
- Added README files to important runtime folders:
  - `app/`
  - `app/ui/`
  - `app/core/`
  - `app/assets/`
  - `app/resources/`
  - `tests/`
  - `scripts/`
  - `docs/`
- Added top-level logical guide folders:
  - `frontend/`
  - `backend/`
  - `data_layer/`
  - `security_layer/`
  - `quality/`
  - `tools/`
  - `deployment/`
  - `documentation/`

## What did not change

- No business logic changed.
- No GST calculation logic changed.
- No UI widget logic changed.
- No import path was renamed.
- No original package structure was broken.

## Reason

The project already has a working split: `app/ui` is frontend and `app/core` is backend. Renaming these folders physically would be risky because the app, tests, and PyInstaller spec depend on stable import paths. This release improves understandability without damaging runtime originality.
