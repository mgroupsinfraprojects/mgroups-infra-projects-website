# V14.8 Admin Page UX Cleanup Report

## Purpose
Reduce the feeling that admin pages are messy after opening sidebar sections. This patch does not add business features. It improves page readability, grouping, and day-to-day usability.

## Main changes

- Renamed sidebar labels:
  - Overview -> Dashboard
  - Visibility & Appearance -> Appearance
  - Drag & Drop Ordering -> Ordering
  - Homepage Block Builder -> Home Blocks
- Cleaned repeated visibility/style control boxes.
- Removed misleading checked "Use custom style" checkboxes from public label controls.
- Grouped Appearance public labels into smaller sections:
  - Hero & Buttons
  - Trust & Credentials
  - Homepage Section Labels
  - Why Choose Us
  - Contact & Footer
  - Stats Labels
- Split Visibility controls into:
  - Contact Visibility
  - Business Credentials
  - Navigation & Footer
- Rebuilt About page into:
  - Main Company Profile
  - Optional Public Statistics
- Simplified Home Blocks page and placed Block Style under an optional advanced details panel.
- Added CSS for compact admin controls, nested accordions, sticky tabs, cleaner cards, and less visual noise.

## Files changed

- templates/admin/base.html
- templates/admin/_field_style.html
- templates/admin/appearance.html
- templates/admin/about.html
- templates/admin/page_builder.html
- static/css/style.css

## Safety

- No database schema changes.
- No route name changes.
- No environment variable changes.
- No public page logic changes.
- Existing saved content remains compatible.

## Test performed

- Python compile check passed for app.py, app_sections/*.py, and routes/*.py.

## Recommended after deploy

1. Open admin in Simple Mode.
2. Check Dashboard, About, Appearance, Home Blocks.
3. Confirm saving About still works.
4. Confirm saving Appearance still works.
5. Check public Home/About pages after saving.
