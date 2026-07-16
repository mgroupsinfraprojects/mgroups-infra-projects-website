# GST Audit Pro v11.6 — Clean Review, Supplier-Only, Admin Feature Release

## Purpose

This patch responds to UI review feedback after v11.5. It keeps the successful Start → Fix Issues flow, but reduces review noise and improves admin control.

## Changes

- Review Queue now treats only real supplier invoice rows as review candidates.
- Empty/support/read-me/ITC/non-invoice rows stay trace-only and do not inflate review counts.
- Duplicate tab shows only meaningful duplicate supplier invoices, not helper/blank duplicate rows.
- Added a visible Reject button immediately after Approve.
- Dashboard default view shows search together with totals, charts, and supplier drill-down.
- Dashboard Fix Issues section respects admin feature visibility.
- Supplier page filters to supplier invoice rows only.
- Supplier search now uses name/GSTIN suggestions after processing.
- Appearance controls hide raw hex color text and use professional “Choose color” controls.
- Admin Features page now shows main module visibility plus sub-feature suggestions for each module.

## Known limitation

This is still a ZIP/source release. It is not a signed Windows installer, and GSTN/e-invoice/e-way bill integrations remain scaffold boundaries.
