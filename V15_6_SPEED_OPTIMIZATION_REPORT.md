# V15.6 Speed Optimization Patch

## Purpose
Reduce admin page load weight and repeated database reads before integrating the Stock module.

## Changes

### 1. Settings request cache
`settings_dict()` now caches the Setting table in Flask `g` for the current request. This reduces repeated Setting table queries caused by templates calling visibility/style/permission helpers many times.

### 2. Users pagination
`/admin/users` now loads users in pages of 10 instead of rendering every user row at once.

### 3. Smaller Role Permissions page
`/admin/permissions` now renders only one selected role at a time using `?role=manager`, `?role=supervisor`, etc. This avoids rendering every role and every permission group on every page load.

### 4. Safer permission save
Role Permissions now saves only the selected role. Developer/legacy owner remains locked with full access.

## Files
- `app_sections/03_helpers.py`
- `routes/05_admin_tools_users.py`
- `templates/admin/permissions.html`
- `templates/admin/users.html`
- `static/css/style.css`

## Deploy
Commit message:
`Optimize admin speed and permission pages`

Render:
Manual Deploy → Clear build cache & deploy

## Notes
This does not remove Render Free cold starts. To remove cold starts, upgrade Render Web Service from Free to paid.
