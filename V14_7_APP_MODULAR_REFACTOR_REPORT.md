# V14.7 App Modular Refactor Report

## Goal
Reduce `app.py` from a 2,700+ line single file into smaller, easier-to-edit sections without changing production behaviour.

## Refactor style
This is a low-risk section split. `app.py` still owns the Flask app, database object, config, and runtime setup. It then loads smaller files in a fixed order so existing route names, decorators, model names, and helper references continue to work.

## New structure

```text
app.py                              # small bootstrap/loader
app_sections/01_models.py           # database models
app_sections/02_defaults.py         # default settings, labels, field lists
app_sections/03_helpers.py          # upload, media, auth, email, visibility helpers
app_sections/04_styles.py           # per-field typography/style helpers
app_sections/05_drafts_versions.py  # draft/publish/version helpers and context globals
app_sections/06_database_seed.py    # migrations, seed data, admin bootstrap
routes/01_public_routes.py          # public website routes
routes/02_admin_auth_dashboard.py   # login, forgot password, dashboard
routes/03_admin_advanced_cms.py     # preview, ordering, versions
routes/04_admin_content.py          # settings/about/services/projects/gallery/enquiries/backup
routes/05_admin_tools_users.py      # media, permissions, page builder, users, errors
```

## What did not change
- Start command remains `gunicorn app:app`.
- Render environment variables remain the same.
- Database tables remain the same.
- Existing URLs/routes remain the same.
- Admin login, manual password reset, Cloudinary upload, PostgreSQL, public pages, and sidebar UX remain unchanged.

## Edit guide
- Users/password reset: `routes/05_admin_tools_users.py` and `routes/02_admin_auth_dashboard.py`
- Gallery upload: `routes/04_admin_content.py` and upload helpers in `app_sections/03_helpers.py`
- Public pages: `routes/01_public_routes.py`
- Database models: `app_sections/01_models.py`
- Default public content/settings: `app_sections/02_defaults.py`
- Styling logic: `app_sections/04_styles.py`
- Migrations/bootstrap: `app_sections/06_database_seed.py`

## Notes
This is not a full Flask Blueprint/application-factory refactor. It is a safer first-stage split intended to make the code easier to edit without risking route or database breakage. A full Blueprint refactor can be done later after the site is stable.

## Testing performed
- Python compile test passed on `app.py`, all `app_sections/*.py`, and all `routes/*.py`.
