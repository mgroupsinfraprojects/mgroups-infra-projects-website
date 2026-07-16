# ConstructERP v2 — Employee & Payroll Operations

A rebuilt Flask employee-management ERP for construction companies. The original database structure and operational modules are retained, but the backend and interface have been hardened for real use.

## Included modules

- Operations dashboard
- Sites and projects
- Employee directory and profiles
- Daily attendance and monthly history
- Leave request approval workflow
- Salary advances with partial recovery tracking
- Payroll generation, payment locking, and CSV export
- Health check for deployment monitoring

## Important security boundary

This version intentionally keeps the original **no-login workflow**. It is suitable for local use or deployment behind an existing authenticated M-Groups portal.

Do **not** expose it as an unrestricted public website because employee records can contain Aadhaar, bank, payroll, and contact information. Add portal authentication and role permissions before public internet access.

## Backend corrections

1. Payroll advance deductions are capped so net pay cannot become negative.
2. Advance recovery occurs only when payroll is marked paid.
3. Partial advance recovery is tracked with `recovered_amount`.
4. Paid payroll records are locked from recalculation.
5. Monthly payroll is prorated by joining date and explicit absence.
6. Attendance history is filtered in SQL instead of loading the entire table.
7. Dashboard site counts use grouped queries instead of one query per site.
8. Employee lists, leave, advances, payroll, and attendance history use pagination.
9. Employee deletion preserves operational history by deactivating records with transactions.
10. Leave date ordering and overlap are validated.
11. Future attendance and attendance before joining date are blocked.
12. POST forms use CSRF protection.
13. Database, secret key, port, and debug mode use environment configuration.
14. Existing SQLite databases are upgraded automatically without deleting data.
15. A `/healthz` endpoint and production Gunicorn command are included.

## Local setup — Windows

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open: `http://127.0.0.1:5000`

You can also double-click `RUN_WINDOWS.bat`.

## Local setup — Linux/macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Or:

```bash
chmod +x run.sh
./run.sh
```

## Environment variables

Copy `.env.example` values into your hosting platform's environment settings.

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Required secure random value for CSRF/session signing |
| `DATABASE_URL` | Optional PostgreSQL URL; defaults to `instance/erp.db` |
| `PORT` | Web server port; defaults to `5000` |
| `FLASK_DEBUG` | Set to `1` only for local debugging |

Generate a secret key:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

## Render deployment

1. Push the `erp` folder to GitHub.
2. Create a new Render Web Service from the repository.
3. Build command:

```bash
pip install -r requirements.txt
```

4. Start command:

```bash
gunicorn app:app --workers 2 --threads 4 --timeout 120
```

5. Add `SECRET_KEY` in Render Environment.
6. For production data persistence, attach PostgreSQL and set `DATABASE_URL`.

SQLite on a normal Render filesystem is ephemeral. A redeploy or restart can remove data unless a persistent disk is configured. PostgreSQL is the correct production option.

## Existing database upgrade

The included `instance/erp.db` is preserved. On first start, the application adds the `advance.recovered_amount` column if it is missing and repairs impossible legacy unpaid payroll values such as negative net pay.

Back up `instance/erp.db` before replacing an older installation.

## Payroll rules

### Daily workers

```text
Gross = Present-equivalent days × Daily wage + Overtime pay
```

A Half Day counts as `0.5`. Leave, Holiday, Absent, and unmarked days are not paid for daily workers.

### Monthly staff

```text
Base salary = Monthly salary prorated from joining date
Gross = Base salary − explicit absence deduction + Overtime pay
```

Approved leave, holidays, and unmarked calendar days remain paid. A Half Day deducts `0.5` day.

### Salary advance

```text
Advance deduction = minimum(outstanding advance, gross − other deductions)
Net pay cannot be negative.
```

Recovery is committed only after clicking **Mark paid**.

## Tests

```bash
python -m unittest discover -s tests -v
```

The test suite covers:

- Primary page rendering and health check
- Negative payroll prevention
- Partial advance recovery
- Historical employee-data preservation
- Future attendance rejection

## Main files

```text
app.py                 Flask application factory, routes, validation, security
models.py              SQLAlchemy models and constraints
services.py            Payroll and advance-recovery business logic
templates/              Responsive Jinja interface
static/css/app.css      Design system and mobile-responsive layout
static/js/app.js        Sidebar, bulk attendance, pay-field behavior
static/vendor/          Local Bootstrap, icons, and JS (no CDN dependency)
instance/erp.db         Existing SQLite data
tests/test_smoke.py     Backend smoke and business-rule tests
Procfile                Production start command
```
