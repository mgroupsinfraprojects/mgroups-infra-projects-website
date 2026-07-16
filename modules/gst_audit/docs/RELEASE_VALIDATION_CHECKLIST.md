# Release Validation Checklist

Use this before sharing a ZIP or EXE.

## Required automated checks

```bash
python -m pytest -q --no-cov
python scripts/dev.py release-check
python scripts/preflight_windows.py
```

## Required manual checks

- App opens from `python main.py`.
- Upload screen loads without missing icons/styles.
- Drag-and-drop area accepts Excel/CSV files.
- Dashboard filter suggestions open and reopen correctly.
- Reconciliation page shows status cards, not a plain text wall.
- Export preview displays row counts before export.
- Export creates an Excel report.
- Settings save uses toast/status feedback.

## Release must not contain

- `__pycache__`
- `.pytest_cache`
- `.coverage`
- `.pyc`
- `.log`
- temporary export files
- local screenshot artifacts

## Version rule

`app/version.py`, `pyproject.toml`, and `README.md` must all show the same current version.


## Sample dataset validation

```bash
python scripts/dev.py sample-check
```

Expected: balanced Excel, review/duplicate Excel, CSV import, and multi-file batch all pass with matched reconciliation and export files created.
