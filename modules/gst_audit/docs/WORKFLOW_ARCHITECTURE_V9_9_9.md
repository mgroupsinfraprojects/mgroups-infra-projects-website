# v9.9.9 Workflow Architecture Release

## Main change

The package now includes a clear professional folder map and section-wise review guide. The Start Audit upload card was also simplified so selected-file details are collapsed by default.

## User workflow

```text
Start Audit
  -> Add files
  -> Start Audit
  -> Fix only important review rows
  -> Export draft/final report
```

## Review policy

Mandatory review is limited to meaningful problems:
- Invalid or missing GSTIN.
- Missing supplier/company name.
- Missing invoice number.
- Taxable value, GST value, total value issues above review threshold.
- Critical GST mismatch rules.

Trace-only/advisory:
- Empty or skipped rows.
- Small rounding differences.
- Excluded duplicate rows already removed from official totals.
- Low-risk freight/TCS/TDS/rounding explanations.

## Architecture review folders

- `frontend/` maps to visible UI screens/widgets.
- `backend/` maps to core GST/audit logic.
- `dashboard/` maps to Smart Dashboard ownership.
- `theme/` maps to display/theme ownership.
- `workflow/` maps to human review policy.
- `data_layer/` maps to persistence.
- `security_layer/` maps to security helpers.

These are facades. Runtime code remains under `app/` to avoid import breakage.
