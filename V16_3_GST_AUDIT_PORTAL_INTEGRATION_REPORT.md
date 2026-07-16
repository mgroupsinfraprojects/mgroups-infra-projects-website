# V16.3 GST Audit Portal Integration

## Purpose
Connect the copied GST Invoice Audit tool to the M-GROUPS protected portal.

## New routes
- `/portal/gst` — GST module hub cards
- `/portal/gst/tool` — protected GST audit workspace
- `/portal/gst/audit` — upload Excel/CSV and run audit
- `/portal/gst/review` — approve/reject/ignore review rows
- `/portal/gst/export` — export verified Excel
- `/portal/gst/report` — printable GST report
- `/portal/gst/audit-log` — audit log CSV
- `/portal/gst/clear` — clear current GST audit session

## Permissions used
- `gst_view`
- `gst_upload`
- `gst_edit`
- `gst_reports`

## Notes
- This is an audit/reconciliation assistant, not GST filing software.
- Runtime audit session data is stored in memory and `modules/gst_audit/web_runtime`; download exports after running audits.
- For production record keeping, store final exports in company storage.
