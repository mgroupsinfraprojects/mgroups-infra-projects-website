# V15.4.2 Live Edit Attrs 500 Hotfix

## Issue
Render logs showed homepage 500 error:

`jinja2.exceptions.UndefinedError: 'live_edit_attrs' is undefined`

The public templates call `live_edit_attrs(...)` for Live Editor support, but the helper was not injected into the Jinja context after the portal patch.

## Fix
Updated `app_sections/05_drafts_versions.py`:

- Adds a safe `live_edit_attrs(target, field, target_id=None)` helper.
- Injects it into the Flask/Jinja context processor.
- Returns empty string on normal public pages.
- Returns `data-live-edit`, `data-live-target`, `data-live-field`, and optional `data-live-id` only on `/admin/live-edit` pages.

## Upload
Replace only:

`app_sections/05_drafts_versions.py`

## Deploy
Commit message:

`Fix live edit attrs template error`

Then Render:

`Manual Deploy -> Clear build cache & deploy`
