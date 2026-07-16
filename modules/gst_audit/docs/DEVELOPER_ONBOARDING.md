# Developer Onboarding

## First run

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Run tests

```bash
python -m pytest -q
```

## Run processor smoke test

```bash
python scripts/smoke_test_processor.py --self-check
```

## Verify release hygiene

```bash
python -B scripts/verify_release.py
```

## Build Windows EXE

```bat
build_exe.bat
```

## Where to modify code

| Task | Edit here |
|---|---|
| Dashboard page / visual UI | `app/ui/views/dashboard_view.py` |
| Guided search / selectable filter popup | `app/ui/widgets/guided_filter.py`, `app/ui/widgets/guided_search_picker.py` |
| File processing and audit decisions | `app/core/audit_engine.py` |
| Export workbook content | `app/core/exporter.py` |
| Database/review persistence | `app/core/database.py` |
| Security/RBAC/hash utilities | `app/core/security.py` |
| GSTIN validation | `app/core/gstin.py` |
| Tests for new logic | `tests/` |

## Rule for future changes

Do not mix GUI logic into `app/core/`. The backend must remain usable without PySide6. Any change to financial logic must have tests before UI changes are added.
