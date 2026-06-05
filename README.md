# M-GROUPS INFRA PROJECTS Website

This is a complete Flask + SQLite company website with a public website and admin dashboard.

## What is included

- Public pages: Home, About, Services, Projects, Gallery, Contact
- Admin dashboard
- Editable company settings
- Editable company description, mission, vision, values, and experience numbers
- Add/edit/delete services
- Add/edit/delete projects and works
- Upload logo, service images, project images, and gallery photos
- Contact enquiry storage
- Admin password change
- SQLite database created automatically on first run

## Run on Windows

Double-click:

```bat
start_windows.bat
```

Or run manually:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open:

```text
http://127.0.0.1:5000
```

Admin:

```text
http://127.0.0.1:5000/admin
```

Default admin login:

```text
Username: admin
Password: ChangeMe@123
```

Change the password immediately after first login.

## Important production note

This package is ready for local use and demonstration. For real public hosting, you must configure HTTPS, secure environment variables, regular database backups, and a production WSGI server. Do not keep the default admin password.
