# V15.7.2 Stock Template Path Hotfix

## Fixed issue
`/portal/stock/` returned 500 with:

`jinja2.exceptions.TemplateNotFound: dashboard.html`

## Root cause
The stock Flask app was mounted under the main M-GROUPS app using DispatcherMiddleware, but the stock app's template root was not explicitly pinned to `modules/stock/templates`. In Render, Flask tried to resolve `dashboard.html` from the wrong template loader context.

## Fix
Updated `modules/stock/app.py` so `create_app()` uses explicit:

- `root_path=modules/stock`
- `template_folder=modules/stock/templates`
- `static_folder=modules/stock/static`

## Files changed
- `modules/stock/app.py`

## Deploy
Upload/replace the file, commit, then Render Manual Deploy with clear build cache.
