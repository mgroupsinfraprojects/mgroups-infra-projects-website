# V14.4 Admin User Edit/Delete Patch

## Base
Built from `m_groups_infra_projects_v14_3_gallery_full_image_display_fix.zip`.

## Changes
- Added Edit action for admin users.
- Added owner-only user edit page.
- Added Delete action for admin users.
- Prevents deleting the currently logged-in user.
- Prevents disabling/deleting the last active owner account.
- Prevents removing owner role from your own account.
- Password update is optional when editing a user.
- Deletes password reset tokens for a user before deleting the user record.

## Files changed
- `app.py`
- `templates/admin/users.html`
- `templates/admin/user_edit.html`
- `static/css/style.css`

## Test
- Python compile passed for `app.py`.
