# V16.4 Employee Portal Integration Report

## Purpose
Mount the construction Employee/Payroll ERP inside the protected M-GROUPS portal.

## Added
- `modules/employees/` keeps the employee ERP original file names.
- `routes/09_employee_portal_mount.py` mounts the app at `/portal/employees/app`.
- `routes/06_portal_routes.py` now opens real employee action cards instead of placeholders.
- `app.py` loads the employee mount route.
- `requirements.txt` adds Flask-WTF for employee module CSRF forms.

## Protected routes
- `/portal/employees` module hub
- `/portal/employees/app/` employee dashboard
- `/portal/employees/app/employees`
- `/portal/employees/app/sites`
- `/portal/employees/app/attendance`
- `/portal/employees/app/attendance/history`
- `/portal/employees/app/leave`
- `/portal/employees/app/advances`
- `/portal/employees/app/payroll`

## Permissions used
- `employees_view` opens the module and view pages.
- `employees_add` / `employees_edit` allows POST actions.
- `employees_delete` allows dangerous deactivate/delete actions.
- `employees_reports` allows payroll/export/report actions.

## Deployment
Upload the patch files to the GitHub repository root, then Render -> Manual Deploy -> Clear build cache & deploy.
After deploy: logout, login again, My Workspace -> Employees.

## Note
The employee ERP stores sensitive employee/payroll data. Do not expose it publicly. Keep it under portal login only.
