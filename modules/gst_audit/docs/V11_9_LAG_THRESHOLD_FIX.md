# V11.9 Lag + Threshold Enforcement Fix

## Purpose
This release fixes two issues found during Windows testing:

1. The UI lagged/stuck when clicking Settings or changing pages after audit processing.
2. Admin review thresholds were saved but the Fix Issues table did not immediately reflect the new ranges.

## Fixes

- After processing, the app now opens Fix Issues and refreshes only the visible page instead of refreshing every heavy dashboard/table at once.
- Audit tables render the first 500 filtered rows by default and keep the full dataset available for filtering/export.
- Large tables no longer call `resizeColumnsToContents()` for thousands of rows.
- Settings threshold changes now immediately recalculate the visible Fix Issues/Dashboard/Export status without re-uploading files.
- Duplicate review policy no longer treats every excluded row with a duplicate key as a human-review duplicate.
- Low rounding/freight/TDS/TCS-style amount differences stay out of Critical Review unless they cross the admin critical threshold.

## Default Important Review Thresholds

- Critical invoice-value difference: ₹10,000
- Advisory difference starts at: ₹2,500
- Ignore tiny difference below: ₹500
- Critical GST component difference: ₹2,500
- Duplicate review minimum value: ₹10,000
- Critical percentage difference: 10%

## Expected behavior with the user's 11 selected GSTR-2B workbooks

- Rows scanned: 11,890
- Approved rows: 3,950
- Critical review: approximately 14 important rows
- Advisory review: approximately 59 rows
- Trace/excluded: approximately 7,856 rows

Small rounding rows such as ₹164/₹300 no longer appear in Critical Review when the admin thresholds are set above them.
