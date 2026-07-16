# Final Run Guide

## 1. Install dependencies

```bash
python -m pip install -r requirements.txt
```

Use Python 3.11 or 3.12. The project configuration intentionally excludes Python 3.13+ until all PySide6 and packaging dependencies are verified there.

## 2. Run preflight

```bash
python scripts/preflight_windows.py
```

This checks:

- Python version
- required packages
- temp-folder write access
- startup import of `MainWindow`

If this fails, fix dependencies before opening the GUI.

## 3. Run release check

```bash
python scripts/dev.py release-check
```

This runs compile, release verification, and the processor smoke test.

## 4. Start the application

```bash
python main.py
```

On Windows, use the one-click launcher:

```bat
START_GST_AUDIT_PRO.bat
```

No separate helper launcher is shipped; users open only `START_GST_AUDIT_PRO.bat`.

## 5. Build EXE

```bat
build_exe.bat
```

Before distributing the EXE, test it on a clean Windows machine and run the manual GUI checklist in `docs/WINDOWS_GUI_TEST_CHECKLIST.md`.
