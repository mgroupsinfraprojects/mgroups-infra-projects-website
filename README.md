# V16.2 Premium 3D Owner UI

# M-GROUPS INFRA PROJECTS — v4 Top Production Website

Professional Flask website for M-GROUPS INFRA PROJECTS with public company pages, admin content management, production storage support, SEO pages, enquiry notification, and backup/restore.

## Included

### Public website
- Home, About, Services, Projects, Project Case Study, Gallery, Contact
- Service-area SEO pages
- Privacy Policy and Terms pages
- WhatsApp floating button
- Google Map embed support
- Google Business Profile link support
- Sitemap and robots.txt
- LocalBusiness schema

### Admin panel
- Editable company settings, contact details, colors, logo, SEO, Google Map, Google Business link
- Editable company description, mission, vision, values, and experience metrics
- Services CRUD
- Projects/work CRUD with case-study fields
- Gallery upload
- Contact enquiry management
- Enquiry CSV export
- JSON backup export
- JSON backup restore
- Admin password change
- Audit logs
- Production setup status panel

### Production/hardening
- PostgreSQL support through `DATABASE_URL`
- Cloudinary persistent image storage through `CLOUDINARY_URL`
- SMTP enquiry email notifications
- Cloudinary/local image cleanup when replacing/deleting media
- CSRF protection
- Login rate limiting
- Security headers
- Health check route: `/healthz`
- Basic pytest test suite

## Local run

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
python app.py
```

Open:

```text
http://127.0.0.1:5000
http://127.0.0.1:5000/admin
```

First admin:

Set `ADMIN_USERNAME`, `ADMIN_DEFAULT_PASSWORD`, and `ADMIN_RECOVERY_EMAIL` privately. Do not commit real passwords to GitHub. If `ADMIN_DEFAULT_PASSWORD` is not set during local testing, the app generates a local-only bootstrap password in `instance/admin_bootstrap_password.txt`.

Change the password immediately after first login.

## Render deployment

Build command:

```bash
pip install -r requirements.txt
```

Start command:

```bash
gunicorn app:app --workers 2 --threads 4 --timeout 120
```

Add environment variables from `.env.example`. Also read `PRODUCTION_REQUIRED_DETAILS.md` before going live.

Minimum production variables:

```text
SECRET_KEY=<generate strong secret>
COOKIE_SECURE=1
DATABASE_URL=<PostgreSQL URL>
CLOUDINARY_URL=<Cloudinary URL>
ADMIN_USERNAME=<owner username>
ADMIN_DEFAULT_PASSWORD=<temporary strong password>
ADMIN_RECOVERY_EMAIL=<owner recovery email>
```

Optional enquiry email variables:

```text
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=<email>
SMTP_PASSWORD=<app password>
SMTP_FROM=<email>
SMTP_TO=<business email>
SMTP_USE_TLS=1
```

## Testing

```bash
pytest
```

## Production note

For a real business website, do not rely only on SQLite/local uploads on Render Free. Use PostgreSQL and Cloudinary/Supabase Storage so admin data and uploaded photos persist after redeploys.

## v5 Verified Content Edition

This build includes public-safe company details extracted from the provided Google Drive folder:

- Udyam registration details
- GST registration details
- registered address/contact values
- experience certificate record names
- contractor registration record names
- project/work documentation summaries

Sensitive identifiers from invoices/legal/tax documents are intentionally not displayed in public copy. Review `DRIVE_CONTENT_INTEGRATION.md` before deploying.


## v6 update

Added privacy-first contact visibility and full admin-controlled text, color, font, section and navigation settings. Use Admin → Visibility & Appearance to control what is public.


## v7 Field-Level Public Visibility

Admin can now control public visibility for individual fields in Website Settings, About & Experience, Services, Projects/Works, and Gallery. This allows private values to remain stored internally while hiding them from the public website. Phone/WhatsApp and project value are private by default.

## v8 Advanced CMS Admin Controls

This version adds Live Preview, Draft/Publish, Version History and Drag-and-Drop Ordering.

Admin paths:

- `/admin/preview` — preview draft/private content before publishing.
- `/admin/ordering` — drag homepage sections, services, projects and gallery items.
- `/admin/versions` — restore previous versions.

Public routes only show published services, projects and gallery items.

## v9 Advanced CMS Additions

This version includes per-field typography/style controls beside visibility checkboxes, a visual page builder, owner/editor/viewer admin roles, side-by-side version comparison, and an E2E browser test plan.

Important privacy default: phone and WhatsApp are hidden publicly unless enabled in admin controls.


## V13 admin password recovery

This package includes a forgot-password flow for admin accounts. Configure `ADMIN_RECOVERY_EMAIL` and SMTP variables in Render, then test `/admin/forgot-password`. See `PASSWORD_RECOVERY_SETUP.md`.

## V16 Owner-Ready Portal Flow

Public website stays open for visitors. Internal tools are protected:

Public Website → Login → My Workspace → Website / Stock / Employees / GST / Reports / Users / System.

Use role permissions to decide which module boxes and child actions each user can see.

For best speed on Render, disable auto-deploy while testing and use a paid web service for business use.


## V16.2 Premium 3D Owner UI
- Adds premium 3D hero, 3D cards, reveal animations and owner-demo polish.
- Keeps V16.1 stock database fix and portal/permission structure.
- Use this version for owner demo if you want premium visual impact.
