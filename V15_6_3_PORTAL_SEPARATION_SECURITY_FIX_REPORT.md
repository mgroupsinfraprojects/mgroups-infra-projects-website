# V15.6.3 Portal Separation + Security Fix

## Problem
Portal module pages were present, but action pages still felt mixed with the old admin area. Website and Users modules could still lead users into the old common admin dashboard/sidebar. Non-developer users could also see the `/admin` production dashboard if they were routed there.

## Fix
- Restores portal module action cards CSS so `/portal/web` and `/portal/users` show clean cards, not a vertical plain list.
- Removes the sensitive `Website Dashboard -> /admin` shortcut from the Website module and replaces it with Public Website Preview.
- Adds `?module=website/users/system` hints to module action URLs to keep admin sidebar context separated.
- Makes `/admin` production dashboard developer/system-only. Non-system users are redirected back to My Workspace.
- Re-ships portal-aware admin sidebar so Website, Users and System pages are visually separated.

## Files
- routes/02_admin_auth_dashboard.py
- routes/06_portal_routes.py
- templates/admin/base.html
- templates/portal/module_hub.html
- static/css/style.css

## Expected behavior
- `/portal/web` shows Website module action cards.
- Website actions open only website-related pages; Users/System links do not appear in the Website sidebar.
- `/portal/users` shows Users & Access Control action cards.
- Users actions open access-control pages; website editing links do not appear in the Users sidebar.
- Manager/supervisor/viewer accounts cannot see `/admin` production status, audit logs, SMTP status or system setup dashboard.
