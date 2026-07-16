# v9.9.3 Effectiveness / Configuration Release

v9.9.3 keeps the GST calculation engine stable and improves the release, startup, customization, and settings workflow around it.

## What changed

| Area | Improvement |
|---|---|
| Version clarity | App version is now `9.9.3`. |
| Editable identity | `config/app_identity.json` controls visible app name, window title, sidebar title, subtitle, and navigation labels. |
| Settings page | Settings is now a control center for branding, navigation labels, theme, density, window size, and GSTIN rule lists. |
| Theme control | Placeholder QSS files were replaced with meaningful reference skins for light, dark, blue, high-contrast, and custom themes. |
| Release gate | `scripts/dev.py release-check` verifies syntax, required files, version sync, forbidden artifacts, smoke processing, and sample datasets. |
| Build gate | `build_exe.bat` now runs the full release gate before PyInstaller. |
| Core tests | Added coverage for branding, security, performance, logging, and money-formatting edge cases. |

## What did not change

- No GST tax arithmetic was weakened.
- No approved/review/duplicate status semantics were changed.
- The v9.8 UI workflow and v9.7 architecture boundary remain intact.

## Correct run order for a fresh machine

```bash
python -m pip install -r requirements.txt
python scripts/preflight_windows.py
python scripts/dev.py release-check
python main.py
```

## Strict effect

This version moves the product from “strong audit engine with weak settings polish” toward a more configurable firm-ready desktop product. Full enterprise deployment still requires signed installer validation on Windows.
