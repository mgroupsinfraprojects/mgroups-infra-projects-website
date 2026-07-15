# V15.7.1 Stock Admin Permission Hotfix

## Fix
- Fixes `/portal/stock` returning 403 for legacy ADMIN / admin / super_admin accounts.
- Treats Developer, Owner, ADMIN, admin, super_admin and administrator-style legacy roles as full control for stock.
- Login now stores `portal_permissions=["*"]` for legacy full-control admin accounts.

## Files
- `modules/stock/app.py`
- `routes/02_admin_auth_dashboard.py`
- `app_sections/03_helpers.py`

## Test
1. Deploy.
2. Logout.
3. Login again as ADMIN.
4. Open `/portal/stock`.
