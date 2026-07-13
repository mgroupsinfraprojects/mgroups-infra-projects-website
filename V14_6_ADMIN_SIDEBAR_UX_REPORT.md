# V14.6 Admin Sidebar UX Cleanup

## Purpose
The admin sidebar had too many flat menu items, making the CMS feel crowded and difficult for non-technical users.

## Changes
- Replaced flat sidebar list with grouped navigation sections.
- Added Daily Work, Website Content, Owner Controls, Advanced Tools, and Account groups.
- Simple Mode now hides advanced tools by default.
- Added visible role chip and compact primary actions.
- Added active link highlighting.
- Kept all existing routes and permissions unchanged.

## Upload/replace files
- templates/admin/base.html
- static/css/style.css
- V14_6_ADMIN_SIDEBAR_UX_REPORT.md

## Expected result
The admin panel becomes easier to use for daily editing while advanced owner controls remain available when needed.
