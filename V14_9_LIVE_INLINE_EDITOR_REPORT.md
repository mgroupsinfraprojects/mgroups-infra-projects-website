# V14.9 Live Inline Editor

Adds an owner-only live editing workflow so content can be edited on the real public interface instead of searching through long admin forms.

## New route
- `/admin/live-edit?page=home`

## Editable from live interface
- Hero title, subtitle, badge and CTA labels
- About content
- Service titles/descriptions
- Project titles/descriptions/locations
- Gallery title/captions
- Contact page labels and contact text

## Safety
- Owner-only access
- CSRF protected API saves
- No image editing from live editor; images still use Gallery/Media Library
- Existing admin forms remain as fallback
