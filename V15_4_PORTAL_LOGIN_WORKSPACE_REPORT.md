# V15.4 Portal Login + My Workspace Patch

## Purpose
Adds the portal architecture requested by the owner:

- Public navbar has Login button.
- One common login for all authorized users.
- After login, users go to `/portal` / My Workspace.
- My Workspace shows module boxes based on user role/permission.
- Current website admin opens from the Website module.
- Stock, Employees, GST, Reports, Users, and System are prepared as protected portal modules/placeholders.

## New public flow

Public visitor:

`Home / About / Services / Projects / Gallery / Contact / Login`

Authorized user:

`Login -> M-GROUPS Portal -> My Workspace -> allowed module boxes`

## Roles added/supported

- developer
- company_owner
- manager
- supervisor
- authorized
- viewer

Legacy roles still supported:

- owner
- editor

## Files changed

- app.py
- app_sections/03_helpers.py
- routes/02_admin_auth_dashboard.py
- routes/05_admin_tools_users.py
- routes/06_portal_routes.py
- templates/base.html
- templates/portal/workspace.html
- templates/portal/module_placeholder.html
- templates/admin/users.html
- templates/admin/user_edit.html
- static/css/style.css

## Important
This patch does not yet merge the stock ZIP. It prepares the protected portal module where stock will be integrated next.

## Test checklist

1. Public website opens.
2. Navbar Login button appears.
3. Login redirects to `/portal`.
4. Developer/owner sees all modules.
5. Viewer sees limited modules.
6. Website module opens existing admin dashboard.
7. Users & Roles can create allowed role types.
8. Direct URL access to restricted module redirects/blocks.
