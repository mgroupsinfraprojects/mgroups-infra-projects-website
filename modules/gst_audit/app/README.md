# `app/` — Runtime Application Package

This is the actual Python package used by `main.py` and PyInstaller.

## Contents

| Folder/file | Meaning |
|---|---|
| `ui/` | Frontend layer: windows, views, widgets, controllers, QThread worker, themes. |
| `core/` | Backend/domain layer: audit engine, GST logic, reconciliation, database, export, security. |
| `assets/` | Icons, preview screenshots, QSS styles. |
| `resources/` | Runtime QSS/style resources. |
| `version.py` | Single version/build metadata source. |

Do not rename this package casually. Many imports and PyInstaller rules depend on `app.*` paths.
