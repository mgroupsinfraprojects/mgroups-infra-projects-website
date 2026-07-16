# v9.9.7 GUI Sync Clarity Release

This patch fixes the confusing state mismatch visible in Windows screenshots.

## Fixed
- Start Here status cards refresh after processing and after returning to the page.
- Review Queue counters are computed directly from processed rows and match Dashboard issue counts.
- Reconciliation cards refresh when the page is opened.
- Export Readiness and Quality Gate refresh when the page is opened.
- Sidebar title no longer clips long company branding; long names are compacted for display.
- Saved old compact/font-8 settings are migrated to comfortable/font-10 defaults.
- Page refresh is targeted on tab navigation instead of relying only on initial processing completion.

## User flow
Open `START_GST_AUDIT_PRO.bat`, choose files, start audit, review issues, then export.
