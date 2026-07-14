# V15.1 Content Admin UX Cleanup

This patch reduces admin form clutter after V15 Design Center.

## Changes
- Rebuilt About page into a content-focused editor.
- Removed repeated per-field font/size/color blocks from normal content pages.
- Preserves existing styles when hidden controls are not submitted.
- Keeps Advanced Tools sidebar open when the active page is inside Advanced Tools.
- Clarifies separation: Content pages = text/content, Design Center = brand/theme, Live Edit = quick inline editing.

## Files
- templates/admin/base.html
- templates/admin/about.html
- templates/admin/_field_style.html
- app_sections/04_styles.py
- static/css/style.css
