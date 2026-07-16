# v9.9.3 Elite Configuration Professional Release

## Purpose

This patch converts the previous configuration release into a stricter professional source package. It keeps editable application identity/navigation settings while removing the two-launcher pattern and adding a client-facing export quality gate.

## Changes

- `START_GST_AUDIT_PRO.bat` is now the only user launcher and contains the complete startup workflow.
- `run_app.bat` is no longer shipped.
- Excel exports now include a `Quality Gate` worksheet with row coverage, amount reconciliation, review queue, duplicate control, traceability, formula-injection guard, and final-lock readiness checks.
- Release verification no longer requires helper launchers.
- Regression tests cover single-launcher packaging and export quality-gate presence.

## Remaining external validation

Windows GUI and EXE execution still require validation on a Windows machine with PySide6 and PyInstaller.
