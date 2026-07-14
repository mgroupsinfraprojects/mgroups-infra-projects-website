# V15 Design Center UX Patch

## Purpose
This patch replaces the long Appearance form with a cleaner Design Center layout.

## Main improvements
- Theme preset buttons: Classic Navy, Corporate Blue, White & Gold, Dark Premium.
- Cleaner global color controls with color picker + hex input.
- Fonts, sizes, radius and layout controls grouped into one readable section.
- Homepage sections separated from public labels.
- Public labels grouped into Hero, Trust/Credentials, Homepage Headings, Why Choose Us, Contact/Footer/Stats.
- Privacy/visibility controls grouped separately.
- Live mini-preview panel for header, hero, button and card style.
- Hidden preservation of advanced per-field style settings so old custom styles are not lost.
- Sidebar label changed from Appearance to Design Center.

## Files changed
- templates/admin/appearance.html
- templates/admin/base.html
- static/css/style.css

## Upload instructions
Upload/replace these files in GitHub, then redeploy on Render with Clear Build Cache & Deploy.

## Recommended use
Use Design Center only for theme, colors, fonts, public labels and section visibility. Use Live Edit for normal content text changes.
