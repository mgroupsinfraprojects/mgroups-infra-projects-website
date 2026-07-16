# V10 Perfect Workflow Release

## Objective

V10 changes the product from a table-heavy GST parser into a decision-first audit workflow.
The user should first see what must be reviewed, then search/view supporting data, then inspect invoice-value analytics.

## What V10 adds

1. **Review Queue Engine** — deterministic separation of mandatory review, advisory review, trace-only, approved, and matched rows.
2. **Fix-First Dashboard Payload** — GST/invoice mistakes appear before charts.
3. **Supplier Drilldown Intelligence** — every supplier/GSTIN group exposes invoice count, approved value, GST value, mandatory review count, advisory count, trace-only count, and invoice-level rows.
4. **Export Blocking Contract** — only mandatory-review defects block export; minor rounding, empty rows, headers, page text, and duplicate trace rows do not.
5. **Realistic Enterprise Boundary** — the package remains a local desktop audit package, not a cloud GST filing/e-invoice/e-way-bill platform.

## V10 rule hierarchy

```text
GSTIN / supplier / invoice identity defect  -> Mandatory Review
Critical GST component mismatch             -> Mandatory Review
Material amount mismatch                    -> Mandatory Review
Freight / discount / TCS / TDS suspicion    -> Advisory Review
Small rounding or clean balanced row         -> Not mandatory
Empty row / skipped row / duplicate trace    -> Trace Only
Approved included row                        -> Approved
```

## Product position

V10 should beat all earlier local desktop releases in review clarity and audit workflow.
It does not beat TallyPrime, Zoho Books, or ClearTax as an end-to-end compliance platform because those products include cloud filing, e-invoicing, e-way bill, ERP/accounting, or government/network integrations.
