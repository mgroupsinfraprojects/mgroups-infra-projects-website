# V15.2 Full Live Editor Stabilization Patch

## Purpose
This patch makes Live Editor the primary easy-edit workflow while keeping advanced/legacy admin forms available as fallback.

## Main fixes
- Adds CSRF meta token to the public live-edit page so inline save does not fail silently.
- Rebuilds Live Editor toolbar with Save, font, size, bold, italic, color, align, Design Center, and Exit controls.
- Adds left page navigator for Home, About, Services, Projects, Gallery, Contact, Service Areas, Privacy, and Terms.
- Adds live modal actions to create Service, Project, Gallery Image, and Home Block from the real website editor.
- Adds `/admin/live-edit/style` endpoint for toolbar style changes.
- Adds `/admin/live-edit/action` endpoint for safe add/replace content actions.
- Improves save error reporting so Render logs can identify the exact route failure.
- Adds live-edit support for service area and policy pages.

## Files changed
- routes/03_admin_advanced_cms.py
- templates/base.html
- templates/home.html
- templates/about.html
- templates/services.html
- templates/projects.html
- templates/project_detail.html
- templates/gallery.html
- templates/contact.html
- templates/service_areas.html
- templates/service_area_detail.html
- templates/policy.html
- templates/admin/base.html
- templates/admin/about.html
- templates/admin/appearance.html
- templates/admin/_field_style.html
- app_sections/04_styles.py
- static/js/live_edit.js
- static/css/style.css

## Important decision
Old content forms are not deleted. They remain as fallback/advanced forms. Do not remove them until Live Editor has been tested for Home, About, Services, Projects, Gallery, Contact, and Service Areas.

## Test checklist after deploy
1. Login as owner.
2. Open Admin → Daily Work → Live Edit.
3. Edit hero title and click Save.
4. Edit hero subtitle and click outside.
5. Use color picker on selected text.
6. Add a test service, then delete it from Services if not needed.
7. Add a test gallery image, then delete it if not needed.
8. Open normal public website and confirm changes.
9. If any save fails, check Render logs for `Live edit save failed`.
