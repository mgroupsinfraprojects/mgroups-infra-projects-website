# V15.6.4 Portal Child Permission + Card Layout Fix

## Problem
The portal module page showed actions as a plain vertical list in some deployments, and the Website module still exposed broad website actions instead of filtering each inner action by its own permission.

## Fix
- Restores portal module cards using strong CSS and an inline fallback in `module_hub.html`.
- Removes the sensitive/old `Website Dashboard` action from Website module.
- Splits Website actions into child permissions:
  - `website_live_edit`
  - `website_settings_edit`
  - `design_edit`
  - `website_about_edit`
  - `website_services_edit`
  - `website_projects_edit`
  - `website_gallery_edit`
  - `media_edit`
- Adds GET/POST protection for old `/admin/...` pages so a user cannot manually type URLs and access pages not allowed by role permissions.
- Keeps `/admin` production dashboard restricted to Developer/System permissions.

## Files
- `app_sections/03_helpers.py`
- `routes/02_admin_auth_dashboard.py`
- `routes/06_portal_routes.py`
- `templates/portal/module_hub.html`
- `static/css/style.css`

## Test
1. Login as Developer and open `/portal/web`.
2. Confirm action cards display in grid.
3. Login as Manager and open `/portal/web`.
4. Confirm only role-enabled website action cards appear.
5. Manually try restricted URLs such as `/admin/appearance` with a manager account that does not have `design_edit`; it should redirect/block.
