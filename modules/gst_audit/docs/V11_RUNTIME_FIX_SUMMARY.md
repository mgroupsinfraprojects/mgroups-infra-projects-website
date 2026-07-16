# v11 Runtime Fix Summary

This patch fixes the runtime and UX issues found during the 11-file Windows audit run.

## Fixed defects

1. `MainWindow.audit_extra_columns_visible` is initialized before any table refresh.
2. `_apply_audit_column_visibility()` is defensive and no longer crashes if called early.
3. Review counts now use one vocabulary across screens:
   - Critical Review
   - Advisory Review
   - Trace / Excluded
   - Approved
4. Trace / Excluded count now excludes Critical and Advisory rows, preventing the old 157-vs-79 confusion.
5. Supplier / GSTIN Center now shows Critical Review counts from all rows, not only included official-total rows.
6. Review queue card buttons now actually update the audit filter when clicked.
7. Review table hides extra technical columns by default to reduce horizontal clutter.
8. Reconciliation page includes row-proof wording: approved + review + trace/excluded = total rows.
9. Export page now makes draft-vs-final wording clearer.
10. Added GUI/runtime regression tests for the missing attribute and count consistency.

## Verified with the provided 11 Excel files

Observed result:

- Total rows: 4,031
- Approved: 3,874
- Critical Review: 14
- Advisory Review: 64
- Trace / Excluded: 79
- Proof: 3,874 + 78 + 79 = 4,031

## Validation commands run

- `python -m compileall app tests`
- `pytest -q`
- `python scripts/verify_release.py`
- `python scripts/verify_v11_elite_release.py`

## Remaining non-code release limitation

This source package is fixed, but it is still not a signed Windows MSI/EXE installer. For client release, build and sign the installer separately.
