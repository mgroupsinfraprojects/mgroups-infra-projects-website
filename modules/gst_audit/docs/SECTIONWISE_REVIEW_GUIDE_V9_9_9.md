# v9.9.9 Section-wise Review Guide After Use

Use this after running the app with your real GST files. Review one section at a time; do not judge the whole app from one screen.

## 1. Start Audit

Expected:
- File count is clear.
- Full file table is hidden unless `Show selected files` is clicked.
- Processing status changes from Waiting to Done.
- Review Issues shows only important pending review count.
- Export status shows Ready / Review Required / Blocked.

Reject the screen if:
- It shows Waiting after processing.
- It shows every file in a huge table by default.
- It sends small rounding differences to mandatory review.

## 2. Smart Dashboard

Expected sections:
1. Fix First: important problems only.
2. Search and View: find company/GSTIN/invoice/month/source file.
3. Totals: invoice value, taxable value, GST value, review rows.
4. Charts: month and supplier/GSTIN charts.
5. Supplier/GSTIN drill-down: click to inspect details.

Reject the dashboard if:
- Charts appear before audit status.
- It says Ready while mandatory review rows still exist.
- Filters appear to change official audit totals.

## 3. Review Queue

Expected:
- Default view shows only mandatory review.
- Identity problems: GSTIN, supplier, invoice number.
- Amount problems: taxable, GST value, total value, large difference.
- Small rounding/noise rows are trace/advisory, not mandatory.
- Accept/reject requires a note.

Reject the review queue if:
- Empty rows appear as mandatory review.
- Every tiny decimal difference blocks the audit.
- Dashboard and Review Queue counts disagree.

## 4. Supplier / GSTIN Center

Expected:
- Supplier count, invoice count, invoice value, and important review count are visible.
- Clicking a supplier shows invoice-level details.
- Invoice details include invoice number, date, taxable value, GST value, total value, status, source file, and Excel row where possible.

Reject the page if:
- It only shows totals and no invoice drill-down.
- Review rows cannot be traced back to supplier invoices.

## 5. Reconciliation

Purpose:
Reconciliation checks whether uploaded rows and totals are internally balanced. Normal users may not need it daily, but it is useful when export is blocked or totals look wrong.

Expected:
- Simple explanation appears first.
- Technical matrix/log is hidden or secondary.
- Row coverage and amount cross-check show Pass/Fail clearly.

Reject the page if:
- It shows only technical text.
- It says Not Run after files were processed.

## 6. Reports & Export

Expected:
- Export page starts with readiness status.
- Draft export is allowed after processing.
- Final report is allowed only when important review is clear.
- Export preview explains what sheets will be created.

Reject the page if:
- It is unclear whether the file is safe to export.
- Quality Gate score is missing after processing.

## 7. Admin Settings

Expected:
- Company/navigation names are separate from theme controls.
- Basic appearance is simple: theme, font size, density, window size.
- Admin rules are separate: GSTIN lists, review thresholds, export rules.
- Advanced layout changes should be safe hide/show/order controls, not risky free drag-and-drop.

Reject the page if:
- Theme settings are mixed with audit rules.
- Font can be set below readable size.
- Admin can hide mandatory audit warnings.

## Minimum acceptance score after real use

| Section | Minimum acceptable score |
|---|---:|
| Start Audit | 94 |
| Smart Dashboard | 95 |
| Review Queue | 95 |
| Supplier / GSTIN | 94 |
| Reconciliation | 91 |
| Reports & Export | 94 |
| Admin Settings | 91 |

If any section drops below the minimum, fix that section before adding more features.
