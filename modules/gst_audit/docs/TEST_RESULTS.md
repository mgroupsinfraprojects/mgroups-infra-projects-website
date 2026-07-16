# Test Results — v9.9.3 Elite Configuration Patch

Recorded verification for the current source package.

## Environment used for source validation

- Platform: Linux container
- Python: 3.13.x container runtime
- Declared project runtime: Python 3.11–3.12
- GUI runtime: not executed here because PySide6/Windows GUI is unavailable in this container

## Commands and results

| Command | Result |
|---|---:|
| `python scripts/dev.py release-check` | Passed |
| `python -m pytest --no-cov` | 189 passed, 2 skipped |
| `python -m pytest -q` | 89% app.core coverage |
| `python scripts/run_sample_dataset_checks.py` | Passed |
| `python scripts/smoke_test_processor.py --self-check` | Passed |

## Coverage summary

`app.core` coverage improved from 87% to 89% after adding tests for branding, security, logging, money formatting, and performance helpers.

## Skipped tests

The two skipped tests are GUI-specific tests requiring PySide6. They must be run on Windows or another environment with PySide6 installed.
