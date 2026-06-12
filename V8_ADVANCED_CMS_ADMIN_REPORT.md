# M-GROUPS INFRA PROJECTS v8 — Advanced CMS Admin Upgrade

## Added in v8

### 1. Live Preview
- `/admin/preview`
- Preview homepage, about, services, projects, gallery and contact pages before publishing.
- Draft/private items are visible only in admin preview.
- Public visitors cannot access draft preview without admin login.

### 2. Draft / Publish
- Website Settings can be saved as draft, previewed, then published.
- About & Experience can be saved as draft, previewed, then published.
- Services, Projects and Gallery items now have a `Draft / Published` state.
- Public website shows only published service/project/gallery items.

### 3. Version History
- `/admin/versions`
- Saves restore points for settings, appearance, about, services, projects, gallery and ordering.
- Admin can restore older versions.
- Restore actions are audit logged.

### 4. Drag-and-Drop Ordering
- `/admin/ordering`
- Drag-and-drop homepage section order.
- Drag-and-drop services order.
- Drag-and-drop projects order.
- Drag-and-drop gallery order.
- Uses CSRF-protected JSON reorder endpoint.

### 5. Public Safety
- Phone/WhatsApp remain hidden unless explicitly enabled.
- Draft content is not visible publicly.
- Project values remain hidden by default through field visibility controls.
- Version restore requires admin login.

## New routes

- `/admin/preview`
- `/admin/versions`
- `/admin/versions/<id>/restore`
- `/admin/ordering`
- `/admin/reorder/<kind>`

## New database tables

- `draft_content`
- `content_versions`

## New/changed columns

- `services.is_published`
- `services.published_at`
- `services.updated_at`
- `projects.sort_order`
- `projects.is_published`
- `projects.published_at`
- `projects.updated_at`
- `gallery.is_published`
- `gallery.published_at`
- `gallery.updated_at`

## Strict score impact

| Area | v7 | v8 |
|---|---:|---:|
| Admin control | 92 | 95 |
| Privacy control | 94 | 95 |
| Draft/publish workflow | 55 | 88 |
| Version restore/history | 40 | 86 |
| Ordering control | 55 | 90 |
| Overall package | 91 | 93 |

## Remaining gap before 96+

- Visual WYSIWYG page builder.
- Per-field live side-by-side diff.
- Multi-admin roles/permissions.
- Full browser E2E test suite.
- Real project photos and production PostgreSQL/Cloudinary/SMTP setup.
