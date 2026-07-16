# workflow/

Readable facade for human workflow and review policy.

## Owns
- What becomes mandatory review.
- What is advisory only.
- What is trace/skipped only.
- The human path: Start Audit -> Fix First -> Review Queue -> Export.

## Runtime source
- `app/core/review_policy.py`
- `app/core/quality_gate.py`
- `app/ui/views/upload_view.py`
- `app/ui/views/audit_view.py`
- `app/ui/views/export_view.py`

## Current review rule
Mandatory review is only for meaningful problems: GSTIN, supplier, invoice number, taxable/total/GST amount problems, and large differences. Small rounding/noise rows remain traceable but do not block review.
