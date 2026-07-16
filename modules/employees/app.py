from __future__ import annotations

import calendar
import csv
import os
import re
from datetime import UTC, date, datetime
from io import StringIO
from pathlib import Path

from flask import (
    Flask,
    Response,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_wtf.csrf import CSRFError, CSRFProtect
from sqlalchemy import and_, func, inspect, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import joinedload
from werkzeug.middleware.proxy_fix import ProxyFix

from models import (
    ATTENDANCE_STATUSES,
    EMPLOYEE_STATUSES,
    LEAVE_STATUSES,
    PAY_TYPES,
    ROLES,
    SITE_STATUSES,
    Advance,
    Attendance,
    Employee,
    Leave,
    Payroll,
    Site,
    db,
)
from services import (
    apply_advance_recovery,
    build_attendance_map,
    calculate_employee_payroll,
    month_bounds,
    outstanding_advances_by_employee,
)


BASE_DIR = Path(__file__).resolve().parent
csrf = CSRFProtect()


def normalize_database_url(url: str) -> str:
    # Render/Heroku may still expose the deprecated postgres:// prefix.
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


def ensure_schema() -> None:
    """Small backward-compatible upgrade for databases from the original ZIP.

    The source project had no migration system. This adds only the one column
    required to track partial salary-advance recovery, preserving existing data.
    """

    inspector = inspect(db.engine)
    if "advance" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("advance")}
    if "recovered_amount" not in columns:
        with db.engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE advance ADD COLUMN recovered_amount FLOAT DEFAULT 0 NOT NULL")
            )




def repair_legacy_data() -> None:
    """Correct impossible values created by the original payroll implementation."""

    dirty = False
    for advance in Advance.query.all():
        if advance.recovered_amount is None:
            advance.recovered_amount = advance.amount if advance.settled else 0
            dirty = True
        elif advance.settled and advance.recovered_amount < advance.amount:
            advance.recovered_amount = advance.amount
            dirty = True
        elif not advance.settled and advance.recovered_amount >= advance.amount:
            advance.settled = True
            dirty = True

    for payroll in Payroll.query.filter(Payroll.paid.is_(False)).all():
        available = max((payroll.gross_pay or 0) - (payroll.other_deduction or 0), 0)
        corrected_advance = min(max(payroll.advance_deduction or 0, 0), available)
        corrected_net = max(available - corrected_advance, 0)
        if round(payroll.advance_deduction or 0, 2) != round(corrected_advance, 2):
            payroll.advance_deduction = round(corrected_advance, 2)
            dirty = True
        if round(payroll.net_pay or 0, 2) != round(corrected_net, 2):
            payroll.net_pay = round(corrected_net, 2)
            dirty = True

    if dirty:
        db.session.commit()

def clean_text(value: str | None, max_length: int = 250) -> str:
    return (value or "").strip()[:max_length]


def parse_date(value: str | None, default: date | None = None) -> date | None:
    if not value:
        return default
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return default


def parse_int(
    value: str | int | None,
    default: int | None = None,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int | None:
    try:
        result = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    if minimum is not None and result < minimum:
        return default
    if maximum is not None and result > maximum:
        return default
    return result


def parse_float(
    value: str | float | None,
    default: float = 0,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    try:
        result = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    if minimum is not None and result < minimum:
        return default
    if maximum is not None and result > maximum:
        return default
    return result


def next_emp_code() -> str:
    last_id = db.session.query(func.max(Employee.id)).scalar() or 0
    return f"EMP{last_id + 1:04d}"


def valid_email(value: str) -> bool:
    if not value:
        return True
    return bool(re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value))


def mask_value(value: str | None, visible: int = 4) -> str:
    if not value:
        return "—"
    if len(value) <= visible:
        return value
    return "•" * (len(value) - visible) + value[-visible:]


def month_year_from_request() -> tuple[int, int]:
    today = date.today()
    month = parse_int(request.args.get("month"), today.month, 1, 12) or today.month
    year = parse_int(request.args.get("year"), today.year, 2000, 2100) or today.year
    return month, year


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)  # type: ignore[method-assign]

    database_url = normalize_database_url(
        os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'instance' / 'erp.db'}")
    )
    app.config.from_mapping(
        SECRET_KEY=os.getenv("SECRET_KEY", "local-dev-key-change-before-public-deployment"),
        SQLALCHEMY_DATABASE_URI=database_url,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True},
        WTF_CSRF_TIME_LIMIT=None,
        MAX_CONTENT_LENGTH=8 * 1024 * 1024,
        JSON_SORT_KEYS=False,
    )
    if test_config:
        app.config.update(test_config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    db.init_app(app)
    csrf.init_app(app)

    with app.app_context():
        db.create_all()
        ensure_schema()
        repair_legacy_data()

    @app.context_processor
    def inject_globals() -> dict:
        def page_url(page_number: int) -> str:
            args = request.args.to_dict(flat=True)
            args["page"] = page_number
            return url_for(request.endpoint, **args)

        return {
            "current_year": date.today().year,
            "employee_statuses": EMPLOYEE_STATUSES,
            "site_statuses": SITE_STATUSES,
            "attendance_statuses": ATTENDANCE_STATUSES,
            "mask_value": mask_value,
            "page_url": page_url,
        }

    @app.after_request
    def add_security_headers(response: Response) -> Response:
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
        )
        if request.is_secure:
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return response

    @app.get("/healthz")
    def healthz():
        try:
            db.session.execute(text("SELECT 1"))
            return jsonify(status="ok", database="connected"), 200
        except SQLAlchemyError:
            return jsonify(status="error", database="unavailable"), 503

    @app.get("/")
    def dashboard():
        today = date.today()
        total_emp = Employee.query.filter_by(status="Active").count()
        total_sites = Site.query.filter_by(status="Ongoing").count()

        attendance_counts = dict(
            db.session.query(Attendance.status, func.count(Attendance.id))
            .filter(Attendance.att_date == today)
            .group_by(Attendance.status)
            .all()
        )
        marked_today = (
            db.session.query(func.count(func.distinct(Attendance.employee_id)))
            .join(Employee, Employee.id == Attendance.employee_id)
            .filter(Attendance.att_date == today, Employee.status == "Active")
            .scalar()
            or 0
        )
        attendance_completion = round((marked_today / total_emp * 100), 1) if total_emp else 0

        pending_leaves = Leave.query.filter_by(status="Pending").count()
        unpaid_payrolls = Payroll.query.filter_by(paid=False).count()
        payroll_due = (
            db.session.query(func.coalesce(func.sum(Payroll.net_pay), 0))
            .filter(Payroll.paid.is_(False))
            .scalar()
            or 0
        )

        site_counts = (
            db.session.query(Site, func.count(Employee.id).label("employee_count"))
            .outerjoin(
                Employee,
                and_(Employee.site_id == Site.id, Employee.status == "Active"),
            )
            .group_by(Site.id)
            .order_by(Site.status.asc(), Site.name.asc())
            .all()
        )
        max_site_count = max((count for _, count in site_counts), default=1)

        recent_leaves = (
            Leave.query.options(joinedload(Leave.employee))
            .order_by(Leave.applied_on.desc())
            .limit(5)
            .all()
        )
        recent_payrolls = (
            Payroll.query.options(joinedload(Payroll.employee))
            .filter_by(paid=False)
            .order_by(Payroll.year.desc(), Payroll.month.desc(), Payroll.net_pay.desc())
            .limit(5)
            .all()
        )

        return render_template(
            "dashboard.html",
            today=today,
            total_emp=total_emp,
            total_sites=total_sites,
            present_today=attendance_counts.get("Present", 0),
            absent_today=attendance_counts.get("Absent", 0),
            marked_today=marked_today,
            attendance_completion=attendance_completion,
            pending_leaves=pending_leaves,
            unpaid_payrolls=unpaid_payrolls,
            payroll_due=float(payroll_due),
            site_counts=site_counts,
            max_site_count=max_site_count,
            recent_leaves=recent_leaves,
            recent_payrolls=recent_payrolls,
            calendar=calendar,
        )

    # ---------------- Sites / Projects ----------------
    @app.get("/sites")
    def sites():
        status = clean_text(request.args.get("status"), 30)
        query = Site.query
        if status in SITE_STATUSES:
            query = query.filter_by(status=status)
        all_sites = query.order_by(Site.status.asc(), Site.name.asc()).all()
        summary = dict(
            db.session.query(Site.status, func.count(Site.id)).group_by(Site.status).all()
        )
        return render_template("sites.html", sites=all_sites, status=status, summary=summary)

    def validate_site_form() -> tuple[dict, list[str]]:
        name = clean_text(request.form.get("name"), 120)
        location = clean_text(request.form.get("location"), 200)
        client_name = clean_text(request.form.get("client_name"), 120)
        start_date = parse_date(request.form.get("start_date"), date.today())
        status = request.form.get("status", "Ongoing")
        errors: list[str] = []
        if len(name) < 2:
            errors.append("Site name must contain at least 2 characters.")
        if status not in SITE_STATUSES:
            errors.append("Invalid site status.")
        return {
            "name": name,
            "location": location,
            "client_name": client_name,
            "start_date": start_date,
            "status": status,
        }, errors

    @app.route("/sites/add", methods=["GET", "POST"])
    def add_site():
        if request.method == "POST":
            data, errors = validate_site_form()
            if errors:
                for error in errors:
                    flash(error, "danger")
                return render_template("site_form.html", site=None, form_data=request.form), 400
            site = Site(**data)
            db.session.add(site)
            db.session.commit()
            flash(f"{site.name} was added.", "success")
            return redirect(url_for("sites"))
        return render_template("site_form.html", site=None, form_data={})

    @app.route("/sites/edit/<int:site_id>", methods=["GET", "POST"])
    def edit_site(site_id: int):
        site = db.get_or_404(Site, site_id)
        if request.method == "POST":
            data, errors = validate_site_form()
            if errors:
                for error in errors:
                    flash(error, "danger")
                return render_template(
                    "site_form.html", site=site, form_data=request.form
                ), 400
            for key, value in data.items():
                setattr(site, key, value)
            db.session.commit()
            flash(f"{site.name} was updated.", "success")
            return redirect(url_for("sites"))
        return render_template("site_form.html", site=site, form_data={})

    @app.post("/sites/delete/<int:site_id>")
    def delete_site(site_id: int):
        site = db.get_or_404(Site, site_id)
        if site.employees:
            flash("This site has assigned employees. Reassign them before deletion.", "danger")
            return redirect(url_for("sites"))
        db.session.delete(site)
        db.session.commit()
        flash("Site deleted.", "success")
        return redirect(url_for("sites"))

    # ---------------- Employees ----------------
    @app.get("/employees")
    def employees():
        q = clean_text(request.args.get("q"), 100)
        site_id = parse_int(request.args.get("site_id"), None, 1)
        status = clean_text(request.args.get("status"), 30)
        page = parse_int(request.args.get("page"), 1, 1) or 1

        query = Employee.query.options(joinedload(Employee.site))
        if q:
            search = f"%{q}%"
            query = query.filter(
                Employee.name.ilike(search)
                | Employee.emp_code.ilike(search)
                | Employee.phone.ilike(search)
                | Employee.role.ilike(search)
            )
        if site_id:
            query = query.filter(Employee.site_id == site_id)
        if status in EMPLOYEE_STATUSES:
            query = query.filter(Employee.status == status)

        pagination = query.order_by(Employee.id.desc()).paginate(
            page=page, per_page=15, error_out=False
        )
        return render_template(
            "employees.html",
            employees=pagination.items,
            pagination=pagination,
            sites=Site.query.order_by(Site.name).all(),
            statuses=EMPLOYEE_STATUSES,
            q=q,
            site_id=site_id or "",
            status=status,
        )

    def validate_employee_form(employee: Employee | None = None) -> tuple[dict, list[str]]:
        name = clean_text(request.form.get("name"), 120)
        phone = clean_text(request.form.get("phone"), 20)
        email = clean_text(request.form.get("email"), 120).lower()
        address = clean_text(request.form.get("address"), 250)
        role = request.form.get("role", "Helper")
        site_id = parse_int(request.form.get("site_id"), None, 1)
        join_date = parse_date(
            request.form.get("join_date"), employee.join_date if employee else date.today()
        )
        daily_wage = parse_float(request.form.get("daily_wage"), 0, 0, 10_000_000)
        monthly_salary = parse_float(
            request.form.get("monthly_salary"), 0, 0, 100_000_000
        )
        pay_type = request.form.get("pay_type", "Daily")
        status = request.form.get("status", "Active")
        aadhaar = re.sub(r"\D", "", request.form.get("aadhaar", ""))[:12]
        bank_account = clean_text(request.form.get("bank_account"), 30)
        ifsc = clean_text(request.form.get("ifsc"), 20).upper()

        errors: list[str] = []
        if len(name) < 2:
            errors.append("Employee name must contain at least 2 characters.")
        if phone and len(re.sub(r"\D", "", phone)) < 7:
            errors.append("Phone number is too short.")
        if not valid_email(email):
            errors.append("Enter a valid email address.")
        if role not in ROLES:
            errors.append("Invalid employee role.")
        if pay_type not in PAY_TYPES:
            errors.append("Invalid pay type.")
        if status not in EMPLOYEE_STATUSES:
            errors.append("Invalid employee status.")
        if pay_type == "Daily" and daily_wage <= 0:
            errors.append("Daily wage must be greater than zero for a daily worker.")
        if pay_type == "Monthly" and monthly_salary <= 0:
            errors.append("Monthly salary must be greater than zero for monthly staff.")
        if aadhaar and len(aadhaar) != 12:
            errors.append("Aadhaar number must contain exactly 12 digits.")
        if site_id and not db.session.get(Site, site_id):
            errors.append("Selected site does not exist.")

        return {
            "name": name,
            "phone": phone,
            "email": email,
            "address": address,
            "role": role,
            "site_id": site_id,
            "join_date": join_date,
            "daily_wage": daily_wage,
            "monthly_salary": monthly_salary,
            "pay_type": pay_type,
            "status": status,
            "aadhaar": aadhaar,
            "bank_account": bank_account,
            "ifsc": ifsc,
        }, errors

    @app.route("/employees/add", methods=["GET", "POST"])
    def add_employee():
        if request.method == "POST":
            data, errors = validate_employee_form()
            if errors:
                for error in errors:
                    flash(error, "danger")
                return render_template(
                    "employee_form.html",
                    employee=None,
                    form_data=request.form,
                    sites=Site.query.order_by(Site.name).all(),
                    roles=ROLES,
                    statuses=EMPLOYEE_STATUSES,
                ), 400

            employee = Employee(emp_code=next_emp_code(), **data)
            db.session.add(employee)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                employee.emp_code = f"EMP{int(datetime.now(UTC).replace(tzinfo=None).timestamp())}"
                db.session.add(employee)
                db.session.commit()
            flash(f"{employee.name} ({employee.emp_code}) was added.", "success")
            return redirect(url_for("employees"))

        return render_template(
            "employee_form.html",
            employee=None,
            form_data={},
            sites=Site.query.order_by(Site.name).all(),
            roles=ROLES,
            statuses=EMPLOYEE_STATUSES,
        )

    @app.route("/employees/edit/<int:employee_id>", methods=["GET", "POST"])
    def edit_employee(employee_id: int):
        employee = db.get_or_404(Employee, employee_id)
        if request.method == "POST":
            data, errors = validate_employee_form(employee)
            if errors:
                for error in errors:
                    flash(error, "danger")
                return render_template(
                    "employee_form.html",
                    employee=employee,
                    form_data=request.form,
                    sites=Site.query.order_by(Site.name).all(),
                    roles=ROLES,
                    statuses=EMPLOYEE_STATUSES,
                ), 400
            for key, value in data.items():
                setattr(employee, key, value)
            db.session.commit()
            flash(f"{employee.name} was updated.", "success")
            return redirect(url_for("employee_profile", employee_id=employee.id))

        return render_template(
            "employee_form.html",
            employee=employee,
            form_data={},
            sites=Site.query.order_by(Site.name).all(),
            roles=ROLES,
            statuses=EMPLOYEE_STATUSES,
        )

    @app.post("/employees/deactivate/<int:employee_id>")
    def deactivate_employee(employee_id: int):
        employee = db.get_or_404(Employee, employee_id)
        employee.status = "Inactive"
        db.session.commit()
        flash(f"{employee.name} was deactivated. Historical records were preserved.", "success")
        return redirect(url_for("employees"))

    @app.post("/employees/delete/<int:employee_id>")
    def delete_employee(employee_id: int):
        employee = db.get_or_404(Employee, employee_id)
        has_history = any(
            (
                Attendance.query.filter_by(employee_id=employee_id).first(),
                Leave.query.filter_by(employee_id=employee_id).first(),
                Payroll.query.filter_by(employee_id=employee_id).first(),
                Advance.query.filter_by(employee_id=employee_id).first(),
            )
        )
        if has_history:
            employee.status = "Inactive"
            db.session.commit()
            flash(
                "Employee has operational history and cannot be deleted. The record was deactivated instead.",
                "warning",
            )
        else:
            db.session.delete(employee)
            db.session.commit()
            flash("Employee deleted.", "success")
        return redirect(url_for("employees"))

    @app.get("/employees/<int:employee_id>")
    def employee_profile(employee_id: int):
        employee = db.get_or_404(Employee, employee_id, options=[joinedload(Employee.site)])
        recent_att = (
            Attendance.query.filter_by(employee_id=employee_id)
            .order_by(Attendance.att_date.desc())
            .limit(30)
            .all()
        )
        leaves = (
            Leave.query.filter_by(employee_id=employee_id)
            .order_by(Leave.applied_on.desc())
            .limit(20)
            .all()
        )
        payrolls = (
            Payroll.query.filter_by(employee_id=employee_id)
            .order_by(Payroll.year.desc(), Payroll.month.desc())
            .limit(24)
            .all()
        )
        advances = (
            Advance.query.filter_by(employee_id=employee_id)
            .order_by(Advance.date_given.desc())
            .limit(20)
            .all()
        )
        present_days = sum(
            1 if item.status == "Present" else 0.5 if item.status == "Half Day" else 0
            for item in recent_att
        )
        return render_template(
            "employee_profile.html",
            e=employee,
            recent_att=recent_att,
            leaves=leaves,
            payrolls=payrolls,
            advances=advances,
            present_days=present_days,
        )

    @app.get("/employees/export.csv")
    def export_employees():
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "Employee Code",
                "Name",
                "Role",
                "Site",
                "Phone",
                "Email",
                "Join Date",
                "Pay Type",
                "Daily Wage",
                "Monthly Salary",
                "Status",
            ]
        )
        for employee in Employee.query.options(joinedload(Employee.site)).order_by(Employee.emp_code):
            writer.writerow(
                [
                    employee.emp_code,
                    employee.name,
                    employee.role,
                    employee.site.name if employee.site else "",
                    employee.phone or "",
                    employee.email or "",
                    employee.join_date.isoformat() if employee.join_date else "",
                    employee.pay_type,
                    employee.daily_wage,
                    employee.monthly_salary,
                    employee.status,
                ]
            )
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=employees.csv"},
        )

    # ---------------- Attendance ----------------
    @app.route("/attendance", methods=["GET", "POST"])
    def attendance():
        if request.method == "POST":
            att_date = parse_date(request.form.get("att_date"))
            site_id = parse_int(request.form.get("site_id"), None, 1)
            employee_ids = {
                employee_id
                for value in request.form.getlist("emp_id")
                if (employee_id := parse_int(value, None, 1))
            }
            if not att_date:
                flash("Attendance date is invalid.", "danger")
                return redirect(url_for("attendance"))
            if att_date > date.today():
                flash("Future attendance cannot be recorded.", "danger")
                return redirect(url_for("attendance", date=att_date.isoformat(), site_id=site_id or ""))
            employees_by_id = {
                employee.id: employee
                for employee in Employee.query.filter(Employee.id.in_(employee_ids)).all()
            }
            saved = 0
            skipped = 0
            for employee_id in employee_ids:
                employee = employees_by_id.get(employee_id)
                if not employee or employee.status not in {"Active", "On Leave"}:
                    skipped += 1
                    continue
                if employee.join_date and att_date < employee.join_date:
                    skipped += 1
                    continue
                status = request.form.get(f"status_{employee_id}", "Present")
                if status not in ATTENDANCE_STATUSES:
                    status = "Present"
                overtime = parse_float(
                    request.form.get(f"ot_{employee_id}"), 0, minimum=0, maximum=24
                )
                record = Attendance.query.filter_by(
                    employee_id=employee_id, att_date=att_date
                ).first()
                if not record:
                    record = Attendance(employee_id=employee_id, att_date=att_date)
                    db.session.add(record)
                record.status = status
                record.overtime_hours = overtime
                saved += 1
            db.session.commit()
            message = f"Attendance saved for {saved} employee(s) on {att_date:%d %b %Y}."
            if skipped:
                message += f" {skipped} invalid or ineligible row(s) were skipped."
            flash(message, "success" if saved else "warning")
            return redirect(
                url_for("attendance", date=att_date.isoformat(), site_id=site_id or "")
            )

        att_date = parse_date(request.args.get("date"), date.today()) or date.today()
        site_id = parse_int(request.args.get("site_id"), None, 1)
        query = Employee.query.filter(Employee.status.in_(["Active", "On Leave"]))
        if site_id:
            query = query.filter(Employee.site_id == site_id)
        employees_list = query.options(joinedload(Employee.site)).order_by(Employee.name).all()
        employee_ids = [employee.id for employee in employees_list]
        records = (
            Attendance.query.filter(
                Attendance.att_date == att_date,
                Attendance.employee_id.in_(employee_ids),
            ).all()
            if employee_ids
            else []
        )
        existing = {record.employee_id: record for record in records}
        return render_template(
            "attendance.html",
            employees=employees_list,
            sites=Site.query.filter_by(status="Ongoing").order_by(Site.name).all(),
            att_date=att_date,
            existing=existing,
            site_id=site_id or "",
            marked_count=len(existing),
            today=date.today(),
        )

    @app.get("/attendance/history")
    def attendance_history():
        employee_id = parse_int(request.args.get("emp_id"), None, 1)
        month, year = month_year_from_request()
        page = parse_int(request.args.get("page"), 1, 1) or 1
        period_start, period_end = month_bounds(year, month)
        query = Attendance.query.options(joinedload(Attendance.employee)).filter(
            Attendance.att_date.between(period_start, period_end)
        )
        if employee_id:
            query = query.filter(Attendance.employee_id == employee_id)
        pagination = query.order_by(Attendance.att_date.desc(), Attendance.id.desc()).paginate(
            page=page, per_page=31, error_out=False
        )
        return render_template(
            "attendance_history.html",
            records=pagination.items,
            pagination=pagination,
            employees=Employee.query.order_by(Employee.name).all(),
            emp_id=employee_id or "",
            month=month,
            year=year,
            calendar=calendar,
        )

    # ---------------- Leave ----------------
    @app.get("/leave")
    def leave_list():
        status = clean_text(request.args.get("status"), 20)
        page = parse_int(request.args.get("page"), 1, 1) or 1
        query = Leave.query.options(joinedload(Leave.employee))
        if status in LEAVE_STATUSES:
            query = query.filter(Leave.status == status)
        pagination = query.order_by(Leave.applied_on.desc()).paginate(
            page=page, per_page=15, error_out=False
        )
        summary = dict(
            db.session.query(Leave.status, func.count(Leave.id)).group_by(Leave.status).all()
        )
        return render_template(
            "leave.html",
            leaves=pagination.items,
            pagination=pagination,
            employees=Employee.query.filter_by(status="Active").order_by(Employee.name).all(),
            status=status,
            summary=summary,
        )

    @app.post("/leave/apply")
    def apply_leave():
        employee_id = parse_int(request.form.get("emp_id"), None, 1)
        from_date = parse_date(request.form.get("from_date"))
        to_date = parse_date(request.form.get("to_date"))
        reason = clean_text(request.form.get("reason"), 250)
        employee = db.session.get(Employee, employee_id) if employee_id else None
        errors: list[str] = []
        if not employee or employee.status != "Active":
            errors.append("Select an active employee.")
        if not from_date or not to_date:
            errors.append("Both leave dates are required.")
        elif to_date < from_date:
            errors.append("Leave end date cannot be before the start date.")
        elif (to_date - from_date).days > 365:
            errors.append("A single leave request cannot exceed 365 days.")
        if employee and from_date and employee.join_date and from_date < employee.join_date:
            errors.append("Leave cannot start before the employee's joining date.")
        if employee and from_date and to_date:
            overlap = Leave.query.filter(
                Leave.employee_id == employee.id,
                Leave.status.in_(["Pending", "Approved"]),
                Leave.from_date <= to_date,
                Leave.to_date >= from_date,
            ).first()
            if overlap:
                errors.append("This employee already has an overlapping leave request.")
        if errors:
            for error in errors:
                flash(error, "danger")
            return redirect(url_for("leave_list"))

        leave = Leave(
            employee_id=employee.id,
            from_date=from_date,
            to_date=to_date,
            reason=reason,
        )
        db.session.add(leave)
        db.session.commit()
        flash("Leave request submitted for approval.", "success")
        return redirect(url_for("leave_list"))

    @app.post("/leave/decide/<int:leave_id>/<action>")
    def decide_leave(leave_id: int, action: str):
        leave = db.get_or_404(Leave, leave_id)
        if action not in {"approve", "reject"}:
            abort(400)
        if leave.status != "Pending":
            flash("Only pending requests can be changed.", "warning")
            return redirect(url_for("leave_list"))
        leave.status = "Approved" if action == "approve" else "Rejected"
        db.session.commit()
        flash(f"Leave request {leave.status.lower()}.", "success")
        return redirect(url_for("leave_list"))

    # ---------------- Advances ----------------
    @app.route("/advances", methods=["GET", "POST"])
    def advances():
        if request.method == "POST":
            employee_id = parse_int(request.form.get("emp_id"), None, 1)
            amount = parse_float(
                request.form.get("amount"), 0, minimum=0.01, maximum=100_000_000
            )
            date_given = parse_date(request.form.get("date_given"), date.today())
            reason = clean_text(request.form.get("reason"), 200)
            employee = db.session.get(Employee, employee_id) if employee_id else None
            if not employee or employee.status != "Active":
                flash("Select an active employee.", "danger")
            elif amount <= 0:
                flash("Advance amount must be greater than zero.", "danger")
            else:
                advance = Advance(
                    employee_id=employee.id,
                    amount=amount,
                    recovered_amount=0,
                    date_given=date_given,
                    reason=reason,
                )
                db.session.add(advance)
                db.session.commit()
                flash("Salary advance recorded.", "success")
            return redirect(url_for("advances"))

        page = parse_int(request.args.get("page"), 1, 1) or 1
        pagination = (
            Advance.query.options(joinedload(Advance.employee))
            .order_by(Advance.settled.asc(), Advance.date_given.desc())
            .paginate(page=page, per_page=15, error_out=False)
        )
        total_outstanding = sum(
            advance.outstanding_amount
            for advance in Advance.query.filter_by(settled=False).all()
        )
        return render_template(
            "advances.html",
            advances=pagination.items,
            pagination=pagination,
            employees=Employee.query.filter_by(status="Active").order_by(Employee.name).all(),
            total_outstanding=total_outstanding,
        )

    @app.post("/advances/settle/<int:advance_id>")
    def settle_advance(advance_id: int):
        advance = db.get_or_404(Advance, advance_id)
        advance.recovered_amount = advance.amount
        advance.settled = True
        db.session.commit()
        flash("Advance marked as fully settled.", "success")
        return redirect(url_for("advances"))

    # ---------------- Payroll ----------------
    @app.get("/payroll")
    def payroll_list():
        month, year = month_year_from_request()
        page = parse_int(request.args.get("page"), 1, 1) or 1
        pagination = (
            Payroll.query.options(joinedload(Payroll.employee))
            .filter_by(month=month, year=year)
            .order_by(Payroll.paid.asc(), Payroll.net_pay.desc())
            .paginate(page=page, per_page=25, error_out=False)
        )
        period_query = Payroll.query.filter_by(month=month, year=year)
        totals = {
            "gross": period_query.with_entities(func.coalesce(func.sum(Payroll.gross_pay), 0)).scalar()
            or 0,
            "advance": period_query.with_entities(
                func.coalesce(func.sum(Payroll.advance_deduction), 0)
            ).scalar()
            or 0,
            "net": period_query.with_entities(func.coalesce(func.sum(Payroll.net_pay), 0)).scalar()
            or 0,
            "paid": period_query.filter_by(paid=True).count(),
            "unpaid": period_query.filter_by(paid=False).count(),
        }
        return render_template(
            "payroll.html",
            records=pagination.items,
            pagination=pagination,
            month=month,
            year=year,
            calendar=calendar,
            totals=totals,
        )

    @app.post("/payroll/generate")
    def generate_payroll():
        month = parse_int(request.form.get("month"), None, 1, 12)
        year = parse_int(request.form.get("year"), None, 2000, 2100)
        if not month or not year:
            flash("Select a valid payroll month and year.", "danger")
            return redirect(url_for("payroll_list"))

        period_start, period_end = month_bounds(year, month)
        employees_list = (
            Employee.query.filter(
                Employee.status.in_(["Active", "On Leave"]),
                Employee.join_date <= period_end,
            )
            .order_by(Employee.id)
            .all()
        )
        employee_ids = [employee.id for employee in employees_list]
        attendance_records = (
            Attendance.query.filter(
                Attendance.employee_id.in_(employee_ids),
                Attendance.att_date.between(period_start, period_end),
            ).all()
            if employee_ids
            else []
        )
        advances_list = (
            Advance.query.filter(
                Advance.employee_id.in_(employee_ids), Advance.settled.is_(False)
            ).all()
            if employee_ids
            else []
        )
        existing_records = (
            Payroll.query.filter(
                Payroll.employee_id.in_(employee_ids),
                Payroll.month == month,
                Payroll.year == year,
            ).all()
            if employee_ids
            else []
        )
        attendance_map = build_attendance_map(attendance_records)
        advance_totals = outstanding_advances_by_employee(advances_list)
        payroll_map = {record.employee_id: record for record in existing_records}

        generated = 0
        skipped_paid = 0
        for employee in employees_list:
            payroll = payroll_map.get(employee.id)
            if payroll and payroll.paid:
                skipped_paid += 1
                continue
            if not payroll:
                payroll = Payroll(employee_id=employee.id, month=month, year=year)
                db.session.add(payroll)
            calculation = calculate_employee_payroll(
                employee=employee,
                attendance_records=attendance_map.get(employee.id, []),
                outstanding_advance=advance_totals.get(employee.id, 0),
                month=month,
                year=year,
                other_deduction=payroll.other_deduction or 0,
            )
            for key, value in calculation.items():
                setattr(payroll, key, value)
            payroll.generated_on = datetime.now(UTC).replace(tzinfo=None)
            generated += 1

        db.session.commit()
        message = f"Payroll generated for {generated} employee(s) for {calendar.month_name[month]} {year}."
        if skipped_paid:
            message += f" {skipped_paid} paid payroll record(s) were locked and skipped."
        flash(message, "success")
        return redirect(url_for("payroll_list", month=month, year=year))

    @app.post("/payroll/mark-paid/<int:payroll_id>")
    def mark_paid(payroll_id: int):
        payroll = db.get_or_404(Payroll, payroll_id)
        if payroll.paid:
            flash("This payroll is already marked as paid.", "warning")
            return redirect(url_for("payroll_list", month=payroll.month, year=payroll.year))
        outstanding_advances = (
            Advance.query.filter_by(employee_id=payroll.employee_id, settled=False)
            .order_by(Advance.date_given.asc(), Advance.id.asc())
            .all()
        )
        recovered = apply_advance_recovery(payroll, outstanding_advances)
        db.session.commit()
        flash(
            f"Payroll marked paid. ₹{recovered:,.2f} was applied to outstanding advances.",
            "success",
        )
        return redirect(url_for("payroll_list", month=payroll.month, year=payroll.year))

    @app.get("/payroll/export.csv")
    def export_payroll():
        month, year = month_year_from_request()
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "Employee Code",
                "Employee",
                "Month",
                "Year",
                "Present Days",
                "Absent Days",
                "OT Hours",
                "Gross Pay",
                "Advance Deduction",
                "Other Deduction",
                "Net Pay",
                "Paid",
            ]
        )
        records = (
            Payroll.query.options(joinedload(Payroll.employee))
            .filter_by(month=month, year=year)
            .order_by(Payroll.employee_id)
            .all()
        )
        for payroll in records:
            writer.writerow(
                [
                    payroll.employee.emp_code,
                    payroll.employee.name,
                    month,
                    year,
                    payroll.days_present,
                    payroll.days_absent,
                    payroll.overtime_hours,
                    payroll.gross_pay,
                    payroll.advance_deduction,
                    payroll.other_deduction,
                    payroll.net_pay,
                    "Yes" if payroll.paid else "No",
                ]
            )
        filename = f"payroll-{year}-{month:02d}.csv"
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    @app.errorhandler(CSRFError)
    def handle_csrf_error(error: CSRFError):
        return render_template(
            "error.html",
            code=400,
            title="Form expired",
            message="The form security token is missing or expired. Reload the page and submit again.",
        ), 400

    @app.errorhandler(400)
    def bad_request(_error):
        return render_template(
            "error.html",
            code=400,
            title="Invalid request",
            message="The submitted request could not be processed.",
        ), 400

    @app.errorhandler(404)
    def not_found(_error):
        return render_template(
            "error.html",
            code=404,
            title="Page not found",
            message="The requested page or record does not exist.",
        ), 404

    @app.errorhandler(500)
    def server_error(_error):
        db.session.rollback()
        return render_template(
            "error.html",
            code=500,
            title="Unexpected error",
            message="The operation failed safely. No partial database transaction was retained.",
        ), 500

    return app


app = create_app()


if __name__ == "__main__":
    app.run(
        debug=os.getenv("FLASK_DEBUG", "0") == "1",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
    )
