# V15.2.1 Live Editor Side Panel Fix

## Problem fixed
The previous inline contenteditable live editor could show an unwanted floating white browser edit box on some Chrome/Brave setups.

## Fix
- Disabled direct contenteditable editing.
- Clicking page text now opens a controlled right-side editor panel.
- Save uses the same `/admin/live-edit/save` backend route.
- Toolbar font/size/color controls still work on the selected text.
- Added stronger toolbar input CSS to prevent browser/form CSS from escaping the toolbar.

## Files changed
- static/js/live_edit.js
- static/css/style.css

## Test flow
1. Login as owner.
2. Open `/admin/live-edit?page=home`.
3. Click hero title.
4. Edit text in right-side panel.
5. Click Save Text.
6. Check public home page.
