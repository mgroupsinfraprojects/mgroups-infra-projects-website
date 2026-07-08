# Browser E2E Test Plan — v9

Run after deploying or locally starting the Flask app.

## Critical flows
1. Public home page loads without exposing phone number by default.
2. Admin login works.
3. Owner can create editor/viewer users.
4. Viewer cannot publish POST changes.
5. Website Settings can save draft, preview, publish.
6. Each field visibility checkbox hides/shows the field publicly.
7. Each field style control changes font, size, weight, color, alignment, italic, uppercase.
8. Page Builder draft block appears in admin preview only.
9. Page Builder published block appears on public home page.
10. Version History compare shows side-by-side differences.
11. Drag ordering updates section/project/service/gallery/page-block order.
12. Contact enquiry stores and exports to CSV.
