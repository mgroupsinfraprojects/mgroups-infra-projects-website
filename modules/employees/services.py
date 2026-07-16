from __future__ import annotations

import calendar
from collections import defaultdict
from datetime import UTC, date, datetime
from typing import Iterable

from models import Advance, Attendance, Employee, Payroll


def month_bounds(year: int, month: int) -> tuple[date, date]:
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)


def calculate_employee_payroll(
    employee: Employee,
    attendance_records: Iterable[Attendance],
    outstanding_advance: float,
    month: int,
    year: int,
    other_deduction: float = 0,
) -> dict[str, float]:
    """Calculate payroll without mutating database state.

    Daily workers are paid only for Present/Half Day attendance plus OT.
    Monthly workers receive prorated monthly salary, with explicit absences and
    half-day absence portions deducted. Leave/Holiday and unmarked calendar days
    remain paid for monthly staff.
    """

    days_in_month = calendar.monthrange(year, month)[1]
    period_start, period_end = month_bounds(year, month)
    records = list(attendance_records)

    present_full = sum(1 for item in records if item.status == "Present")
    half_days = sum(1 for item in records if item.status == "Half Day")
    absent_full = sum(1 for item in records if item.status == "Absent")
    overtime_hours = round(sum(max(item.overtime_hours or 0, 0) for item in records), 2)

    present_equivalent = present_full + (half_days * 0.5)
    absent_equivalent = absent_full + (half_days * 0.5)

    if employee.pay_type == "Monthly":
        join_date = employee.join_date or period_start
        eligible_start = max(join_date, period_start)
        eligible_days = 0 if eligible_start > period_end else (period_end - eligible_start).days + 1
        base_salary = (employee.monthly_salary or 0) * eligible_days / days_in_month
        per_day = (employee.monthly_salary or 0) / days_in_month if days_in_month else 0
        base_after_absence = max(base_salary - (per_day * absent_equivalent), 0)
        hourly_rate = per_day / 8 if per_day else 0
        overtime_pay = overtime_hours * hourly_rate * 1.5
        gross_pay = base_after_absence + overtime_pay
    else:
        wage = employee.daily_wage or 0
        hourly_rate = wage / 8 if wage else 0
        overtime_pay = overtime_hours * hourly_rate * 1.5
        gross_pay = (present_equivalent * wage) + overtime_pay

    gross_pay = round(max(gross_pay, 0), 2)
    other_deduction = round(max(other_deduction or 0, 0), 2)
    recoverable = max(gross_pay - other_deduction, 0)
    advance_deduction = round(min(max(outstanding_advance, 0), recoverable), 2)
    net_pay = round(max(gross_pay - other_deduction - advance_deduction, 0), 2)

    return {
        "days_present": round(present_equivalent, 2),
        "days_absent": round(absent_equivalent, 2),
        "overtime_hours": overtime_hours,
        "gross_pay": gross_pay,
        "advance_deduction": advance_deduction,
        "other_deduction": other_deduction,
        "net_pay": net_pay,
    }


def build_attendance_map(records: Iterable[Attendance]) -> dict[int, list[Attendance]]:
    grouped: dict[int, list[Attendance]] = defaultdict(list)
    for record in records:
        grouped[record.employee_id].append(record)
    return grouped


def outstanding_advances_by_employee(advances: Iterable[Advance]) -> dict[int, float]:
    totals: dict[int, float] = defaultdict(float)
    for advance in advances:
        totals[advance.employee_id] += advance.outstanding_amount
    return {employee_id: round(amount, 2) for employee_id, amount in totals.items()}


def apply_advance_recovery(payroll: Payroll, advances: list[Advance]) -> float:
    """Apply a payroll's advance deduction to oldest outstanding advances."""

    remaining = round(max(payroll.advance_deduction or 0, 0), 2)
    recovered = 0.0

    for advance in sorted(advances, key=lambda item: (item.date_given, item.id)):
        if remaining <= 0:
            break
        outstanding = advance.outstanding_amount
        if outstanding <= 0:
            advance.settled = True
            continue
        allocation = min(outstanding, remaining)
        advance.recovered_amount = round((advance.recovered_amount or 0) + allocation, 2)
        advance.settled = advance.outstanding_amount <= 0.009
        recovered += allocation
        remaining -= allocation

    recovered = round(recovered, 2)
    payroll.advance_deduction = recovered
    payroll.net_pay = round(
        max((payroll.gross_pay or 0) - (payroll.other_deduction or 0) - recovered, 0), 2
    )
    payroll.paid = True
    payroll.generated_on = datetime.now(UTC).replace(tzinfo=None)
    return recovered
