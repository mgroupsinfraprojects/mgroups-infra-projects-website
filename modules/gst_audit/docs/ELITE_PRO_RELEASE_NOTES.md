# v9.9.2 Elite Professional Release Notes

## Objective

v9.9.2 focuses on the weak areas from the strict review: professional release workflow, one-file launch, EXE readiness, reviewer-facing controls, and client-ready audit output.

## Professional software references translated into this product

Accounting/audit systems generally emphasize three operational controls:

1. Import and reconciliation workflows, so source data can be loaded and matched without losing traceability.
2. Audit history or audit trail style reporting, so changes and review decisions are visible.
3. Final review/sign-off gates, so reports are not treated as final until exceptions are handled.

v9.9.2 applies those principles locally for GST invoice audit work.

## Added in v9.9.2

### 1. True single launcher

The user-facing launcher is now only:

```bat
START_GST_AUDIT_PRO.bat
```

The previous wrapper-style `run_app.bat` was removed. The single launcher creates/uses `.venv`, installs requirements, runs preflight, and opens the app.

### 2. Reviewer Quality Gate

A new deterministic quality gate was added in:

```text
app/core/quality_gate.py
```

It checks:

- row coverage reconciliation
- amount reconciliation
- critical row isolation
- open review queue
- high-severity exception queue
- GST mismatch visibility
- duplicate control
- source traceability
- approved-total basis
- final lock readiness

The Excel export now includes a `Quality Gate` worksheet and cover-sheet quality score/status.

### 3. Cleaner sign-off workbook

The export sign-off sheet no longer duplicates the GSTIN field. This was a small but real professional-polish defect.

### 4. Stronger Windows preflight

`preflight_windows.py` now checks:

- Python version
- required Python modules
- critical project files
- sample dataset availability
- PyInstaller spec availability
- disk space
- temp write permission
- startup import

### 5. Stronger EXE build gate

`build_exe.bat` now runs:

1. source release gate
2. full regression suite
3. GUI startup smoke test
4. PyInstaller build
5. EXE output verification
6. manual checklist instruction

### 6. Elite regression tests

Added:

```text
tests/test_elite_quality_gate.py
```

This verifies the quality gate, workbook inclusion, quality score, and unique sign-off fields.

## Correct usage

### Normal user

Double-click:

```bat
START_GST_AUDIT_PRO.bat
```

### Developer/source verification

```bash
python scripts/dev.py release-check
python scripts/dev.py elite-check
```

### Windows EXE build

```bat
build_exe.bat
```

## Remaining external validation

This source release can be validated automatically. Final business-grade certification still requires a Windows machine to verify:

- PySide6 visual rendering
- real client files
- final EXE launch
- antivirus false-positive status
- signed installer or deployment package
