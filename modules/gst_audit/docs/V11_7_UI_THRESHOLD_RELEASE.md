# GST Audit Pro v11.7 UI Threshold Release

## Purpose
This release focuses on usability and review precision:

- Admin-controlled review amount thresholds.
- Small value differences no longer flood Critical Review.
- Dashboard simplified to Search + Totals + Charts by default.
- Supplier page remains searchable, but only supplier invoice rows are listed.
- Appearance settings use safe professional presets instead of exposing unrelated colour controls that can make the UI unreadable.
- Feature controls now expose deeper sub-feature options for dashboard, review, suppliers, proof, and export.

## Review Threshold Defaults

| Rule | Default |
|---|---:|
| Critical value difference | ₹500 |
| Advisory value difference | ₹100 |
| Ignore tiny difference below | ₹10 |
| Critical percentage difference | 1% |
| High-value supplier threshold | ₹1,00,000 |

Always reviewed regardless of amount:

- GSTIN error
- Supplier missing
- Invoice number missing
- Date error
- Meaningful duplicate invoice

## Dashboard Default
The dashboard now focuses on:

1. Search
2. Totals
3. Charts

Supplier drilldown is optional and can be opened when needed.

## Supplier Search Capability
The supplier search matches:

- Supplier name
- GSTIN
- Invoice number
- Source file
- Invoice value
- Taxable value
- GST value
- Audit status
- Mismatch reason

The supplier table excludes non-supplier/support rows.
