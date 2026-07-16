# Editable Application Identity

Edit `app_identity.json` to change the visible software name and sidebar navigation labels before starting the app.

Supported keys:

- `app_name`: short product name used in branding.
- `window_title`: full title shown in the Windows title bar.
- `sidebar_title`: title shown at the top of the left navigation.
- `sidebar_subtitle`: small helper text below the sidebar title.
- `navigation`: labels for `upload`, `dashboard`, `review`, `suppliers`, `reconciliation`, `exports`, and `settings`.

Keep labels short. The app sanitizes unsafe characters and falls back to defaults if the JSON is invalid.
