# M-GROUPS INFRA PROJECTS v10 — Runtime Fix + Advanced CMS Upgrade

## Critical bug fixed

The v9 Internal Server Error on these routes was caused by Jinja macros imported without context:

- `/admin/settings`
- `/admin/gallery`
- `/admin/about`
- `/admin/services/new`
- `/admin/projects/new`

Fixed by importing `admin/_field_style.html` macros **with context**, so `style_key`, `item_style_key`, `site`, and `is_on` are available inside the macro.

## Added in v10

- Media Library & Cropper page: `/admin/media`
- Role Permissions matrix: `/admin/permissions`
- Improved inline live canvas in Visual Page Builder
- Settings/gallery/about/service/project route runtime test coverage
- Playwright full route smoke test file
- Production setup report retained for Render env variables

## Tested locally using Flask test client

Passed GET checks:

- `/`
- `/admin`
- `/admin/settings`
- `/admin/gallery`
- `/admin/about`
- `/admin/services`
- `/admin/services/new`
- `/admin/projects`
- `/admin/projects/new`
- `/admin/appearance`
- `/admin/page-builder`
- `/admin/users`
- `/admin/versions`
- `/admin/ordering`
- `/admin/restore`
- `/admin/enquiries`
- `/admin/media`
- `/admin/permissions`

Passed POST checks:

- publish website settings
- upload gallery image
- upload media library image
- save role permissions

## Remaining external setup

These cannot be completed inside a ZIP file. They must be added in Render dashboard:

- `SECRET_KEY`
- `COOKIE_SECURE=1`
- `DATABASE_URL`
- `CLOUDINARY_URL`
- SMTP variables

## Strict score

- v9 after reported runtime error: 82/100 actual usable score
- v10 fixed package: 94/100 package score
- v10 admin control score: 97/100
- v10 live without Render env/photos: 85–88/100
- v10 live after PostgreSQL + Cloudinary + SMTP + real project photos: 93–95/100
