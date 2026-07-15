# V15.6.1 Portal Module Logic Fix

## Purpose
Fix the UX/logic confusion where My Workspace module boxes opened directly into old admin pages.

## Before
- Website card redirected directly to `/admin`.
- Users card redirected directly to `/admin/users`.
- User felt Website and Users were the same admin area with the same sidebar/navigation.

## After
- `/portal/web` opens a Website Management module hub.
- `/portal/users` opens a Users & Access Control module hub.
- Stock, Employees, GST, Reports and System also open their own module hub pages.
- Old admin pages remain as action pages inside module hubs.

## Files
- `routes/06_portal_routes.py`
- `templates/portal/module_hub.html`
- `static/css/style.css`

## Deploy
Commit message: `Fix portal module routing logic`
Then Render: Manual Deploy -> Clear build cache & deploy.
