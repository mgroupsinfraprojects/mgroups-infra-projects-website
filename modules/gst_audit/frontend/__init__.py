"""Frontend compatibility package.

The production UI implementation remains in :mod:`app.ui`.
This package exists to make the logical architecture explicit without breaking
legacy imports, tests, or PyInstaller packaging.
"""

RUNTIME_PACKAGE = "app.ui"
