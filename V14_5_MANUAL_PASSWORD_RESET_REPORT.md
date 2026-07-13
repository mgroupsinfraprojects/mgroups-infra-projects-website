# V14.5 Manual Password Reset Patch

Purpose: make admin-user password recovery usable without SMTP email.

## Changes
- Clarified Admin Users & Roles page.
- Added explicit "Edit / Reset Password" wording.
- Edit User page now states owner can set a new password without SMTP/email.
- Create-user password minimum aligned to 10 characters.
- Added audit event when owner manually resets a user password.

## Files changed
- app.py
- templates/admin/users.html
- templates/admin/user_edit.html

## Use
Admin → Admin Users & Roles → Edit / Reset Password → Set New Password → Save.
Then give the new password privately to the user.
