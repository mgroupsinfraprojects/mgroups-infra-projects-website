# dashboard/

Readable facade for the Smart Dashboard layer.

## Owns
- Decision-first dashboard structure.
- Fix First issue cards.
- Search and View controls.
- Totals, charts, and supplier/GSTIN drill-down views.

## Runtime source
- `app/ui/views/dashboard_view.py`
- `app/ui/dashboard_controller.py`
- `app/ui/controllers/dashboard_controller.py`

## Rule
Dashboard displays audit state. It must not recalculate backend GST logic.
