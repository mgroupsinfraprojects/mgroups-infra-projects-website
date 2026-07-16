from __future__ import annotations

from datetime import UTC, date, datetime

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import CheckConstraint, Index


db = SQLAlchemy()


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)

ROLES = [
    "Engineer",
    "Supervisor",
    "Mason",
    "Electrician",
    "Plumber",
    "Carpenter",
    "Helper",
    "Driver",
    "Security",
    "Admin Staff",
    "Other",
]

EMPLOYEE_STATUSES = ["Active", "On Leave", "Inactive", "Terminated"]
SITE_STATUSES = ["Ongoing", "Completed", "Halted"]
ATTENDANCE_STATUSES = ["Present", "Absent", "Half Day", "Leave", "Holiday"]
LEAVE_STATUSES = ["Pending", "Approved", "Rejected"]
PAY_TYPES = ["Daily", "Monthly"]

# Backward-compatible alias used by the original application.
STATUS = EMPLOYEE_STATUSES


class Site(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    location = db.Column(db.String(200))
    client_name = db.Column(db.String(120))
    start_date = db.Column(db.Date)
    status = db.Column(db.String(30), default="Ongoing", nullable=False)

    employees = db.relationship("Employee", backref="site", lazy="select")

    __table_args__ = (
        Index("ix_site_status", "status"),
        CheckConstraint("status IN ('Ongoing','Completed','Halted')", name="ck_site_status"),
    )


class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    emp_code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    address = db.Column(db.String(250))
    role = db.Column(db.String(50), default="Helper", nullable=False)
    site_id = db.Column(db.Integer, db.ForeignKey("site.id"))
    join_date = db.Column(db.Date, default=date.today, nullable=False)
    daily_wage = db.Column(db.Float, default=0, nullable=False)
    monthly_salary = db.Column(db.Float, default=0, nullable=False)
    pay_type = db.Column(db.String(20), default="Daily", nullable=False)
    status = db.Column(db.String(20), default="Active", nullable=False)
    aadhaar = db.Column(db.String(20))
    bank_account = db.Column(db.String(30))
    ifsc = db.Column(db.String(20))

    attendance = db.relationship(
        "Attendance", backref="employee", lazy="select", cascade="all, delete-orphan"
    )
    leaves = db.relationship(
        "Leave", backref="employee", lazy="select", cascade="all, delete-orphan"
    )
    payrolls = db.relationship(
        "Payroll", backref="employee", lazy="select", cascade="all, delete-orphan"
    )
    advances = db.relationship(
        "Advance", back_populates="employee", lazy="select", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_employee_status_site", "status", "site_id"),
        Index("ix_employee_name", "name"),
        CheckConstraint("daily_wage >= 0", name="ck_employee_daily_wage"),
        CheckConstraint("monthly_salary >= 0", name="ck_employee_monthly_salary"),
        CheckConstraint("pay_type IN ('Daily','Monthly')", name="ck_employee_pay_type"),
    )


class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employee.id"), nullable=False)
    att_date = db.Column(db.Date, nullable=False, default=date.today)
    status = db.Column(db.String(20), default="Present", nullable=False)
    overtime_hours = db.Column(db.Float, default=0, nullable=False)
    remarks = db.Column(db.String(200))

    __table_args__ = (
        db.UniqueConstraint("employee_id", "att_date", name="uq_emp_date"),
        Index("ix_attendance_date_status", "att_date", "status"),
        CheckConstraint("overtime_hours >= 0 AND overtime_hours <= 24", name="ck_attendance_ot"),
    )


class Leave(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employee.id"), nullable=False)
    from_date = db.Column(db.Date, nullable=False)
    to_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.String(250))
    status = db.Column(db.String(20), default="Pending", nullable=False)
    applied_on = db.Column(db.DateTime, default=utcnow_naive, nullable=False)

    __table_args__ = (
        Index("ix_leave_status_dates", "status", "from_date", "to_date"),
        CheckConstraint("to_date >= from_date", name="ck_leave_date_order"),
    )


class Payroll(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employee.id"), nullable=False)
    month = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    days_present = db.Column(db.Float, default=0, nullable=False)
    days_absent = db.Column(db.Float, default=0, nullable=False)
    overtime_hours = db.Column(db.Float, default=0, nullable=False)
    gross_pay = db.Column(db.Float, default=0, nullable=False)
    advance_deduction = db.Column(db.Float, default=0, nullable=False)
    other_deduction = db.Column(db.Float, default=0, nullable=False)
    net_pay = db.Column(db.Float, default=0, nullable=False)
    generated_on = db.Column(db.DateTime, default=utcnow_naive, nullable=False)
    paid = db.Column(db.Boolean, default=False, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("employee_id", "month", "year", name="uq_emp_month_year"),
        Index("ix_payroll_period_paid", "year", "month", "paid"),
        CheckConstraint("month >= 1 AND month <= 12", name="ck_payroll_month"),
    )


class Advance(db.Model):
    """Salary advance with recovery tracked across paid payroll records."""

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employee.id"), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    recovered_amount = db.Column(db.Float, nullable=False, default=0)
    date_given = db.Column(db.Date, default=date.today, nullable=False)
    reason = db.Column(db.String(200))
    settled = db.Column(db.Boolean, default=False, nullable=False)

    employee = db.relationship("Employee", back_populates="advances")

    __table_args__ = (
        Index("ix_advance_employee_settled", "employee_id", "settled"),
        CheckConstraint("amount > 0", name="ck_advance_amount"),
        CheckConstraint("recovered_amount >= 0", name="ck_advance_recovered"),
    )

    @property
    def outstanding_amount(self) -> float:
        return max(round((self.amount or 0) - (self.recovered_amount or 0), 2), 0)
