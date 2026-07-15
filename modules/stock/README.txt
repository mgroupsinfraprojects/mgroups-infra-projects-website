M-Groups Inventory V6.2.2 - Top Level Field-Friendly Material Control

Purpose:
Maintain and find all company materials across store/godown, sites, temporary yards and other locations.
The system tracks purchase, store-to-site dispatch, site-to-site shifting, site return, site usage, damage/missing,
physical stock count, opening stock, receive confirmation, audit log, reports and backups.

How to run on Windows:
1. Extract this ZIP.
2. Prefer moving the folder to C:\MGroupsInventory instead of running from Downloads.
3. Double-click run.bat.
4. Open http://127.0.0.1:5000 if the browser does not open automatically.
5. Keep the black command window open while using the software.

Mobile / same-WiFi access:
- V6.2.2 runs on host 0.0.0.0 by default, so phones on the same WiFi/LAN can access it.
- The app prints a LAN URL in the black window, for example: http://192.168.1.25:5000
- On the phone, connect to the same WiFi and open that LAN URL.
- If it does not open, allow Windows Firewall inbound TCP port 5000 or use RUN_LOCAL_ONLY.bat for PC-only use.
- For users outside the office/site WiFi, use cloud/VPS deployment. Do not expose a local Windows PC directly to the internet.

Run modes:
- run.bat: recommended safe LAN mode, no virtual environment, avoids Device Guard pip.exe issue.
- RUN_SAFE_NO_VENV.bat: same safe mode with minimal messages.
- RUN_LOCAL_ONLY.bat: only the local PC can open it.
- RUN_DEV_DEBUG.bat: developer debug mode.

Data locations:
- Database: instance/inventory.db
- Uploads: static/uploads/
- Reports: exports/
- Backups: backups/

Important V6.2 / V6.2.1 changes retained:
- LAN/mobile same-WiFi access fixed using host 0.0.0.0.
- run.bat prints LAN access guidance and handles app restart after backup restore.
- Pagination added to Materials, New Entry/Movements, and Audit Log lists.
- Backup restore now triggers automatic app restart when run through run.bat.
- datetime.utcnow deprecation warnings removed.

Important V6.1 changes still included:
- Active navbar highlight.
- Stock View renamed to Current Stock.
- Dashboard includes inactive locations if they still have stock; stock is never hidden.
- Location/material deactivation is blocked if stock exists.
- Other/custom options for movement type, location type, category, unit and usage type.
- Quick-action cards for supervisors/storekeepers.
- Where-is-material search in Dashboard and Current Stock.
- Pending receive badge in navbar.
- Damage/Missing entry as its own action.
- Movement challan print and PDF export.
- Extra Excel reports.
- Backup download and restore.

Login:
No login page is included. The app is ready to receive your manual login using session or headers:
session['user_id'], session['user_name'], session['user_role']
or headers X-User-ID, X-User-Name, X-User-Role.

Production note:
For real company multi-branch use, deploy to a server/cloud/VPS and switch SQLite to PostgreSQL.


V6.2.2 strict fixes
- Removed misleading SQLAlchemy DateTime(timezone=True) flags because SQLite does not preserve tzinfo on round-trip.
- Application timestamps are stored intentionally as naive Asia/Kolkata local time, which matches the single-timezone India field workflow and reports.
- Dashboard today_movements is now wired into the visible Today Entries card instead of being dead route data.
- Smoke test now covers the dashboard route and verifies the timestamp storage contract.
- README changelog updated to describe the actual behavior instead of claiming timezone-aware persistence.

V6.2.1 strict fixes retained
- RUN_LOCAL_ONLY.bat, RUN_DEV_DEBUG.bat, RUN_WITH_VENV_IF_ALLOWED.bat, run.bat, RUN_SAFE_NO_VENV.bat, and run.sh all honor exit code 3 and restart after backup restore.

V6.2.2 verification
- pytest passes and now covers the dashboard route.
- Main pages tested: dashboard, entries, new entry, receive, current stock, materials, locations, suppliers, reports, audit, backup and health check.
- Legacy SQLAlchemy Query.get() warnings have been removed by using db.session.get() for direct primary-key lookups.
