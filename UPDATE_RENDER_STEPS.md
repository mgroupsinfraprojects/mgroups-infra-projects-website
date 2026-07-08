# Update Existing Render Site from GitHub

1. Extract this ZIP.
2. Open your GitHub repository connected to Render.
3. Backup the existing repository first.
4. Upload/replace the project files.
5. Do not upload `.venv`, `__pycache__`, `.env`, local DB files, or runtime secrets.
6. Commit changes.
7. Render redeploys automatically if Auto Deploy is enabled.
8. Open `/admin`, login, and change password.
9. Add real company details and project photos.

## Render settings

Build command:

```bash
pip install -r requirements.txt
```

Start command:

```bash
gunicorn app:app --workers 2 --threads 4 --timeout 120
```

## Strong setup

Add these env variables in Render:

```text
SECRET_KEY=<strong random key>
COOKIE_SECURE=1
DATABASE_URL=<PostgreSQL URL>
CLOUDINARY_URL=<Cloudinary URL>
```

Without `DATABASE_URL`, the app uses SQLite fallback. Without `CLOUDINARY_URL`, uploaded images use local storage.
