# V15.4.1 500 Error Hotfix

## Purpose
Fix a 500 error after adding the Portal/Login patch by making the public navbar safe even if the portal context or endpoint is not fully registered on an existing deployment.

## Likely cause
The new public navbar used dynamic Jinja calls for the portal/login link. On an already-running production app with mixed-version files, this can break the public homepage if the portal route or `current_admin` template context is not available at render time.

## Changes
- `templates/base.html`
  - Uses safe literal paths `/portal` and `/admin/login` for navbar login/workspace links.
  - Avoids hard failing when `current_admin` is not available.
- `app_sections/05_drafts_versions.py`
  - Ensures `current_admin` is injected into templates.
- `routes/06_portal_routes.py`
  - Includes portal workspace routes.
- `app.py`
  - Ensures `routes/06_portal_routes.py` is loaded.

## Deploy
Upload/replace the included files, commit, then Render → Manual Deploy → Clear build cache & deploy.

## Test
1. Open public homepage `/` in an incognito/private browser.
2. Confirm homepage loads.
3. Click Login.
4. Login with existing owner account.
5. Confirm redirect to `/portal`.
