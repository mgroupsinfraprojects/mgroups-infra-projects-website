# Release Checklist

Before publishing a release ZIP:

- [ ] `python scripts/dev.py test` passes.
- [ ] `python scripts/dev.py smoke` passes.
- [ ] `python scripts/dev.py verify` passes.
- [ ] `python scripts/dev.py clean` removes local artifacts.
- [ ] `app/version.py` and `pyproject.toml` agree.
- [ ] No `__pycache__`, `.pytest_cache`, `.coverage`, `.pyc`, or `.log` files are in the ZIP.
- [ ] Windows EXE build is separately validated before any commercial deployment claim.
