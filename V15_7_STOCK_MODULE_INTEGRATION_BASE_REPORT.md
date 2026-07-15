# V15.7 Stock Module Integration Base

## Purpose
Mount the existing M-GROUPS Inventory / Stock Management ZIP inside the current M-GROUPS Portal without renaming the stock app's internal filenames.

## Result
- My Workspace -> Stock opens the real stock management system at `/portal/stock`.
- The stock app is protected by the same M-GROUPS login session.
- Stock permissions are enforced inside the stock app:
  - `stock_view`
  - `stock_add`
  - `stock_transfer`
  - `stock_adjust`
  - `stock_reports`
  - plus system/backup permissions for stock backup pages.
- Stock database tables are prefixed to avoid conflict with website tables:
  - `stock_materials`, `stock_locations`, `stock_material_movements`, `stock_audit_logs`, etc.
- Stock app filenames are kept inside `modules/stock/`.

## Files
- `app.py`
- `routes/02_admin_auth_dashboard.py`
- `routes/07_stock_portal_mount.py`
- `modules/stock/*`
- `requirements.txt`

## Important deployment note
After uploading this patch, logout and login again. Login now writes `user_id`, `user_name`, `user_role`, and `portal_permissions` into the session for the stock module.

## Storage note
The stock app uses PostgreSQL for database tables when `DATABASE_URL` exists. Local uploaded files under `modules/stock/static/uploads` are not guaranteed permanent on Render Free. Cloudinary integration for stock photos can be added in the next phase.
