# GST Audit Pro v9.9.6 — Simple GUI Elite Patch

This patch focuses on making the interface smaller, clearer, and safer for non-technical users.

## GUI upgrades

- The Upload page is now a simple **Start Here** workflow with four visible steps: Choose Files, Start Audit, Review Issues, Export.
- Added a file-type/profile selector so users can choose Auto Detect, Purchase Register, GSTR-2A/2B, Supplier Invoice List, or Custom Excel/CSV.
- Added visible step-status chips so users can see what is waiting, done, needs review, or ready.
- Added a Review Center issue queue for Needs Review, High Risk, GST Mismatch, and Duplicates/Excluded.
- Added Export Readiness cards showing row coverage, amount match, review queue, and final lock status.
- Added user-friendly error recovery messages for locked files, missing columns, old `.xls` files, encoding problems, and merged headers.
- Added keyboard shortcuts for main pages: Ctrl+1 Start, Ctrl+2 Dashboard, Ctrl+3 Review, Ctrl+4 Export.

## Validation gate

The source release gate still includes release verification, compile checks, processor smoke, sample dataset checks, pytest regression tests, and coverage.
