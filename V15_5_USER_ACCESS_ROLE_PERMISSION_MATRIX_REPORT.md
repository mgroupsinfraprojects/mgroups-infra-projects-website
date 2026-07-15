# V15.5 User Access + Role Permission Matrix

## Purpose
This patch replaces the old single “Allow editor” permission page with a role-based permission matrix for the M-GROUPS Portal.

## Added / Changed
- Users & Roles now shows:
  - role selection as “Who is this user?”
  - allowed module summary per user
  - links to Role Permissions
  - restricted action buttons based on current user's permissions
- Role Permissions now shows role boxes:
  - Company Owner
  - Manager
  - Supervisor
  - Authorized Person
  - Viewer
- Each role can be configured by permission groups:
  - Module visibility
  - Website management
  - Stock management
  - Employee management
  - GST / Audit
  - Reports & audit
  - Users & roles
  - System control
- Developer / legacy owner remains locked with full control.
- Permission settings are stored in the existing Setting table. No new database table is required.
- Portal module cards use the saved role permissions.

## Files
- app_sections/03_helpers.py
- routes/05_admin_tools_users.py
- templates/admin/permissions.html
- templates/admin/users.html
- templates/admin/user_edit.html
- static/css/style.css

## Deployment
Upload/replace the files above, commit, then Render Manual Deploy → Clear build cache & deploy.

## Test
1. Login as Developer/Owner.
2. Open Users & Roles.
3. Open Role Permissions.
4. Give Manager only Stock, Employees, Reports, Users.
5. Give Supervisor only Stock and Reports.
6. Give Viewer only Reports or read-only stock/report access.
7. Login each test user in incognito and confirm module boxes.
