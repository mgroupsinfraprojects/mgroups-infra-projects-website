# Workflow

```text
START
  ↓
Select GST Excel Files
  ↓
Read Workbooks + Sheets
  ↓
Read Every Non-empty Row
  ↓
Classify Header / Metadata Rows as Skipped
  ↓
Detect GSTIN, Supplier, Invoice No, Date, Amounts
  ↓
Reconstruct possible shifted / continuation rows
  ↓
Validate GST formula
  ↓
Classify mismatch reason and severity
  ↓
Detect duplicates
  ↓
Set include_in_totals decision
  ↓
Build approved dashboard totals
  ↓
Run reconciliation matrix
  ↓
Manual review: accept/reject warning rows
  ↓
Export verified Excel report
END
```
