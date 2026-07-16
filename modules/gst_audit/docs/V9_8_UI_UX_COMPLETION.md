# v9.8 UI/UX Completion Release

v9.8 keeps the v9.7 architecture and core audit engine intact. The changes are concentrated in the user workflow layer so the application feels less like a developer test bench and more like a professional GST audit workstation.

## What changed

| Area | v9.7 problem | v9.8 correction |
|---|---|---|
| Dashboard charts | Four large charts pushed the supplier table too far down on laptop screens. | Primary charts are compact by default; diagnostic charts use progressive disclosure. |
| Audit table | Technical columns appeared before the decision-making columns. | Decision-first column order: supplier, GSTIN, invoice, date, actual, expected, diff, reason, status. |
| Audit table clutter | Sheet, row id, HSN, include flag, and raw row id consumed horizontal space. | Extra columns are hidden by default and available through `Show more columns`. |
| Bulk review | Plain text prompt did not explain financial impact. | Structured dialog shows row count, supplier preview, accept/reject choice, and saved note. |
| Reconciliation | Large text wall was difficult for non-technical users. | Four card-based checks: row coverage, amount cross-check, dashboard rule, final status. |
| Export page | Export action did not tell the user what would be exported. | Export preview lists included sheets and current dataset totals. |
| Upload actions | Buttons had equal visual weight. | Start Audit is primary; Browse is secondary; Clear is danger-outline; tooltips added. |
| Settings | Save confirmation used blocking message box. | Settings now use the toast/status system. |

## Files changed

```text
app/ui/views/dashboard_view.py        # compact chart grid + chart details toggle
app/ui/views/audit_view.py            # table extra-column toggle control
app/ui/views/reconciliation_view.py   # card-based reconciliation summary
app/ui/views/export_view.py           # export preview panel
app/ui/views/upload_view.py           # upload button hierarchy/tooltips
app/ui/main_window.py                 # audit table order, bulk review dialog, export preview, settings toast
app/ui/theme_manager.py               # theme-aware styling for new controls
app/assets/styles/main.qss            # fallback/static styles for new controls
tests/test_v9_8_ui_workflow_completion.py
```

## Strict impact

- UI/UX score target: **95–97 / 100** for internal business use.
- Commercial product score target: **95–96 / 100** source package level.
- Enterprise deployment is still not 99/100 because signed installer, organization identity/RBAC, encrypted deployment policy, and Windows installer validation are deployment-layer items, not UI code fixes.
