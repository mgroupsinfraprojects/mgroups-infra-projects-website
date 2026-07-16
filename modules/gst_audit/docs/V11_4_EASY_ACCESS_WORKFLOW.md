# v11.4 Easy Access Workflow Release

## Purpose

This patch reduces screen friction after real user screenshot review. The app now behaves more like a task workflow than a technical dashboard.

## Changes

1. After processing files, the app opens **Fix Issues** directly instead of sending the user to the dashboard.
2. Sidebar/navigation uses short task labels through a one-time settings migration:
   - Start
   - Dashboard
   - Fix Issues
   - Suppliers
   - Proof
   - Export
   - Settings
3. Dashboard source chips now show **all source files** instead of hiding them behind `+ more`.
4. Dashboard month chips now show **all months** instead of hiding them behind `+ more`.
5. Chart section label now tells users to click a bar for details.
6. Chart clicks now show a full drill-down summary with row count, approved count, critical/advisory/trace counts, invoice value, taxable value, and GST value.
7. Review queue buttons were shortened to prevent clipping:
   - Approve
   - Ignore
   - Why?
   - Edit Row
   - Evidence

## Intended Workflow

Choose files → Start audit → Fix Issues → Dashboard → Export

The dashboard remains available, but review is now the first post-processing action because unresolved critical rows block final export.

## Validation

- Python compile: passed
- Pytest: 202 passed
- Release verifier: passed
- V11 elite verifier: passed

## Remaining Limitation

The release is still a ZIP/source release, not a signed Windows installer. SQLite ResourceWarnings still appear in existing tests and should be cleaned in a future deployment-hardening release.
