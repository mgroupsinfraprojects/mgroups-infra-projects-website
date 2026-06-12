# M-GROUPS INFRA PROJECTS v11 — Font & Style Runtime Fix

## Problem fixed
In v10, some admin typography controls saved correctly but did not visibly affect all public website sections because many templates did not apply per-field style values to their public elements. Numeric font sizes such as `22` also produced invalid CSS in some global variables because the value had no unit.

## Fixes added
- Global font settings now apply with stronger CSS priority.
- Numeric size values are normalized automatically: `22` becomes `22px`.
- Global body text size, hero title size, section title size, container width, card radius and button radius now accept both plain numbers and CSS values.
- Per-field text style now applies on public templates for:
  - company name
  - tagline
  - hero title/subtitle
  - credentials
  - service-area headings
  - about section
  - services section
  - project cards and project details
  - stats labels
  - why section
  - CTA section
  - contact page
  - footer contact details
- Appearance page text labels now have style controls.
- Service/project/gallery item style controls now load saved values when editing.
- Color style fields no longer force default black when the admin did not intentionally set a color.

## Tested
Flask test-client checks passed for:
- `/`
- `/about`
- `/services`
- `/projects`
- `/gallery`
- `/contact`
- `/service-areas`
- `/admin`
- `/admin/settings`
- `/admin/gallery`
- `/admin/about`
- `/admin/services`
- `/admin/projects`
- `/admin/appearance`
- `/admin/page-builder`
- `/admin/media`
- `/admin/permissions`

POST tests passed for:
- Website Settings style save and public rendering
- Appearance global font/size save and public rendering
- Service item font/size/color save and public rendering

## Usage note
Admin can type font size as either `22` or `22px`; both work.
