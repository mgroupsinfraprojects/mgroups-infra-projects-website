# GST Audit Pro v11.5 Simple Admin Workflow Release

## Purpose
This release simplifies the visible workflow and adds admin-controlled feature visibility.

## Main workflow
1. Start
2. Fix Issues
3. Dashboard
4. Export

Supporting pages:
- Suppliers
- Proof
- Settings

## Key fixes
- Start page no longer shows large four-step cards by default.
- After upload/process, the workflow should guide users to Fix Issues first.
- Dashboard prioritizes totals, charts, and suppliers instead of showing every technical panel first.
- Metric cards are clickable and show full detail summaries.
- Supplier page supports search/filter and multi-supplier selection for invoice detail review.
- Admin Settings now has tabs: Branding, Appearance, Features, Audit Rules.
- Admin can hide/unhide sidebar features except Start and Settings.
- Fix Issues now separates real review categories: GST/value, missing/date, duplicates, trace.
- GSTR-2B support/read-me/ITC summary rows are trace-only instead of critical review rows.

## Validation summary
- Python compile passed.
- Pytest passed with `202 passed` using `--no-cov`.
- 22-file import safety smoke: 22 uploaded, 11 selected, 11 duplicates excluded.
- 11 selected workbook audit smoke: 11,890 rows, 3,950 approved, 15 critical, 65 advisory, 7,860 trace.

## Remaining strict limitations
- This is still a ZIP/source release, not a signed Windows installer.
- SQLite ResourceWarnings remain in the older test path.
- Live GSTN/e-invoice/e-way bill integrations are still scaffolds.
