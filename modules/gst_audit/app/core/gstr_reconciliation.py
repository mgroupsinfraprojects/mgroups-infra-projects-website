from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal
import re
from typing import Dict, Iterable, List, Tuple

import pandas as pd

from app.core.models import AuditResult, InvoiceRow
from app.core.money import to_decimal


@dataclass(frozen=True)
class GstrMatchRecord:
    status: str
    severity: str
    supplier_gstin: str
    supplier_name: str
    invoice_no: str
    book_invoice_value: Decimal
    gstr_invoice_value: Decimal
    difference: Decimal
    book_taxable_value: Decimal = Decimal("0.00")
    gstr_taxable_value: Decimal = Decimal("0.00")
    taxable_difference: Decimal = Decimal("0.00")
    book_gst_total: Decimal = Decimal("0.00")
    gstr_gst_total: Decimal = Decimal("0.00")
    gst_difference: Decimal = Decimal("0.00")
    book_invoice_date: str = ""
    gstr_invoice_date: str = ""
    date_status: str = "NOT_CHECKED"
    period_status: str = "NOT_CHECKED"
    itc_status: str = "UNKNOWN"
    rcm_status: str = "UNKNOWN"
    action_required: str = ""
    match_confidence: int = 0
    book_row_id: int | None = None
    gstr_row_id: int | None = None
    book_source: str = ""
    gstr_source: str = ""
    note: str = ""

    def to_dict(self) -> dict:
        data = asdict(self)
        for key in [
            "book_invoice_value", "gstr_invoice_value", "difference",
            "book_taxable_value", "gstr_taxable_value", "taxable_difference",
            "book_gst_total", "gstr_gst_total", "gst_difference",
        ]:
            data[key] = float(data[key])
        return data


@dataclass(frozen=True)
class GstrReconciliationSummary:
    book_rows_compared: int
    gstr_rows_compared: int
    matched_rows: int
    amount_mismatch_rows: int
    missing_in_gstr_rows: int
    missing_in_books_rows: int
    date_mismatch_rows: int
    period_mismatch_rows: int
    taxable_mismatch_rows: int
    gst_mismatch_rows: int
    duplicate_book_keys: int
    duplicate_gstr_keys: int
    book_total: Decimal
    gstr_total: Decimal
    matched_book_total: Decimal
    matched_gstr_total: Decimal
    mismatch_difference_total: Decimal
    final_status: str

    def to_dict(self) -> dict:
        data = asdict(self)
        for key, value in list(data.items()):
            if isinstance(value, Decimal):
                data[key] = float(value)
        return data


@dataclass(frozen=True)
class GstrReconciliationResult:
    records: List[GstrMatchRecord]
    summary: GstrReconciliationSummary

    def records_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame([record.to_dict() for record in self.records])

    def summary_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame([self.summary.to_dict()])


_INVOICE_SEPARATORS = re.compile(r"[^A-Z0-9]+")
_YES_VALUES = {"Y", "YES", "TRUE", "1", "AVAILABLE", "ELIGIBLE"}
_NO_VALUES = {"N", "NO", "FALSE", "0", "UNAVAILABLE", "INELIGIBLE"}


def normalize_invoice_no(value: str) -> str:
    """Stable invoice number normalization for book-vs-GSTR matching."""
    text = str(value or "").upper().strip()
    text = _INVOICE_SEPARATORS.sub("", text)
    if text.isdigit():
        text = str(int(text))
    return text


def reconciliation_key(row: InvoiceRow) -> Tuple[str, str]:
    return (str(row.gstin or "").upper().replace(" ", ""), normalize_invoice_no(row.invoice_no))


def _eligible_rows(rows: Iterable[InvoiceRow]) -> List[InvoiceRow]:
    eligible: List[InvoiceRow] = []
    for row in rows:
        if row.audit_status.startswith("SKIPPED") or row.audit_status.startswith("ERROR"):
            continue
        if not row.gstin or not normalize_invoice_no(row.invoice_no):
            continue
        if row.invoice_value == 0:
            continue
        eligible.append(row)
    return eligible


def _group_by_key(rows: Iterable[InvoiceRow]) -> Dict[Tuple[str, str], List[InvoiceRow]]:
    grouped: Dict[Tuple[str, str], List[InvoiceRow]] = {}
    for row in rows:
        grouped.setdefault(reconciliation_key(row), []).append(row)
    return grouped


def _gst_total(rows: Iterable[InvoiceRow]) -> Decimal:
    return sum((r.igst + r.cgst + r.sgst + r.cess for r in rows), Decimal("0.00"))


def _row_date(row: InvoiceRow | None) -> str:
    return row.invoice_date.isoformat() if row and row.invoice_date else ""


def _period(row: InvoiceRow | None) -> str:
    if not row:
        return ""
    if row.period:
        return row.period
    if row.invoice_date:
        return row.invoice_date.strftime("%Y-%m")
    return ""


def _normalize_flag(value: object) -> str:
    text = str(value or "").strip().upper()
    if text in _YES_VALUES:
        return "YES"
    if text in _NO_VALUES:
        return "NO"
    return "UNKNOWN"


def _snapshot_value(row: InvoiceRow | None, *keys: str) -> object:
    if not row:
        return ""
    for snapshot in (row.detected_snapshot, row.final_snapshot):
        for key in keys:
            if key in snapshot and snapshot[key] not in (None, ""):
                return snapshot[key]
    return ""


def _itc_status(gstr_row: InvoiceRow | None) -> str:
    return _normalize_flag(_snapshot_value(gstr_row, "itc_eligibility", "itc_availability", "eligible_itc", "itc_status"))


def _rcm_status(gstr_row: InvoiceRow | None) -> str:
    return _normalize_flag(_snapshot_value(gstr_row, "reverse_charge", "rcm", "reverse_charge_flag"))


def _action(status: str, severity: str, date_status: str, period_status: str, itc_status: str, rcm_status: str) -> str:
    if status == "MATCHED" and itc_status in {"YES", "UNKNOWN"}:
        return "No major action. Keep source invoice and GSTR evidence with audit file."
    if status == "MISSING_IN_GSTR":
        return "Do not claim ITC blindly. Check supplier filing, period shift, or pending GSTR-2B reflection."
    if status == "MISSING_IN_BOOKS":
        return "Check whether the purchase entry is missing in books or belongs to another GST period."
    if status == "DUPLICATE_KEY_REVIEW":
        return "Group duplicates by invoice number and supplier GSTIN. Confirm amendment/credit/debit note treatment."
    issues = []
    if status == "AMOUNT_MISMATCH":
        issues.append("reconcile invoice/taxable/GST values")
    if date_status == "DATE_MISMATCH":
        issues.append("verify invoice date")
    if period_status == "PERIOD_MISMATCH":
        issues.append("verify return period")
    if itc_status == "NO":
        issues.append("check ITC ineligibility")
    if rcm_status == "YES":
        issues.append("check reverse-charge treatment")
    if not issues:
        issues.append("review row before final sign-off")
    return "Review required: " + "; ".join(issues) + "."


def reconcile_gstr_2a_2b(
    book_result: AuditResult,
    gstr_result: AuditResult,
    *,
    amount_tolerance: Decimal = Decimal("2.00"),
    date_tolerance_days: int = 0,
) -> GstrReconciliationResult:
    """
    Compare purchase/book invoice rows against GST portal GSTR-2A/2B rows.

    Primary matching key: supplier GSTIN + normalized invoice number.
    Extra audit checks: invoice date, period, taxable value, GST value, ITC flag and RCM flag.
    This function never mutates original audit rows and never changes dashboard totals.
    """
    book_rows = _eligible_rows(book_result.rows)
    gstr_rows = _eligible_rows(gstr_result.rows)
    book_groups = _group_by_key(book_rows)
    gstr_groups = _group_by_key(gstr_rows)
    records: List[GstrMatchRecord] = []

    duplicate_book_keys = sum(1 for values in book_groups.values() if len(values) > 1)
    duplicate_gstr_keys = sum(1 for values in gstr_groups.values() if len(values) > 1)

    all_keys = sorted(set(book_groups) | set(gstr_groups))
    for key in all_keys:
        book_list = book_groups.get(key, [])
        gstr_list = gstr_groups.get(key, [])
        supplier_gstin, invoice_no = key
        book_total = sum((r.invoice_value for r in book_list), Decimal("0.00"))
        gstr_total = sum((r.invoice_value for r in gstr_list), Decimal("0.00"))
        book_taxable = sum((r.taxable_value for r in book_list), Decimal("0.00"))
        gstr_taxable = sum((r.taxable_value for r in gstr_list), Decimal("0.00"))
        book_gst = _gst_total(book_list)
        gstr_gst = _gst_total(gstr_list)
        difference = book_total - gstr_total
        taxable_difference = book_taxable - gstr_taxable
        gst_difference = book_gst - gstr_gst
        book_ref = book_list[0] if book_list else None
        gstr_ref = gstr_list[0] if gstr_list else None
        display_ref = book_ref or gstr_ref
        supplier_name = display_ref.supplier_name if display_ref else ""

        book_date = _row_date(book_ref)
        gstr_date = _row_date(gstr_ref)
        if book_ref and gstr_ref and book_date and gstr_date:
            day_delta = abs((book_ref.invoice_date - gstr_ref.invoice_date).days) if book_ref.invoice_date and gstr_ref.invoice_date else 0
            date_status = "DATE_MATCHED" if day_delta <= date_tolerance_days else "DATE_MISMATCH"
        elif book_ref and gstr_ref:
            date_status = "DATE_NOT_AVAILABLE"
        else:
            date_status = "NOT_CHECKED"

        book_period = _period(book_ref)
        gstr_period = _period(gstr_ref)
        period_status = "PERIOD_MATCHED" if book_period and gstr_period and book_period == gstr_period else "PERIOD_MISMATCH" if book_ref and gstr_ref and book_period and gstr_period else "NOT_CHECKED"
        taxable_status_bad = taxable_difference.copy_abs() > amount_tolerance
        gst_status_bad = gst_difference.copy_abs() > amount_tolerance
        itc_status = _itc_status(gstr_ref)
        rcm_status = _rcm_status(gstr_ref)

        if book_list and gstr_list:
            if len(book_list) > 1 or len(gstr_list) > 1:
                status = "DUPLICATE_KEY_REVIEW"
                severity = "HIGH"
                note = "Same supplier GSTIN + invoice number appears more than once in book and/or GSTR data. Review duplicate/amended treatment."
            elif difference.copy_abs() <= amount_tolerance and not taxable_status_bad and not gst_status_bad and date_status != "DATE_MISMATCH" and period_status != "PERIOD_MISMATCH" and itc_status != "NO":
                status = "MATCHED"
                severity = "LOW"
                note = "Book invoice matched with GSTR-2A/2B within tolerance."
            else:
                status = "AMOUNT_MISMATCH"
                high_issue = difference.copy_abs() > Decimal("100.00") or taxable_status_bad or gst_status_bad or itc_status == "NO"
                severity = "HIGH" if high_issue else "MEDIUM"
                note = "Book and GSTR row need review. Check invoice value, taxable value, GST total, invoice date, ITC eligibility and return period."
        elif book_list and not gstr_list:
            status = "MISSING_IN_GSTR"
            severity = "HIGH"
            note = "Invoice exists in books but not in imported GSTR-2A/2B. ITC claim requires review."
        else:
            status = "MISSING_IN_BOOKS"
            severity = "MEDIUM"
            note = "Invoice exists in GSTR-2A/2B but not in uploaded book data. Check missing purchase entry."

        confidence = 0
        if supplier_gstin:
            confidence += 30
        if invoice_no:
            confidence += 30
        if book_ref and gstr_ref:
            if difference.copy_abs() <= amount_tolerance:
                confidence += 20
            if date_status == "DATE_MATCHED":
                confidence += 10
            if period_status == "PERIOD_MATCHED":
                confidence += 10

        records.append(GstrMatchRecord(
            status=status,
            severity=severity,
            supplier_gstin=supplier_gstin,
            supplier_name=supplier_name,
            invoice_no=invoice_no,
            book_invoice_value=book_total,
            gstr_invoice_value=gstr_total,
            difference=difference,
            book_taxable_value=book_taxable,
            gstr_taxable_value=gstr_taxable,
            taxable_difference=taxable_difference,
            book_gst_total=book_gst,
            gstr_gst_total=gstr_gst,
            gst_difference=gst_difference,
            book_invoice_date=book_date,
            gstr_invoice_date=gstr_date,
            date_status=date_status,
            period_status=period_status,
            itc_status=itc_status,
            rcm_status=rcm_status,
            action_required=_action(status, severity, date_status, period_status, itc_status, rcm_status),
            match_confidence=confidence,
            book_row_id=book_ref.row_id if book_ref else None,
            gstr_row_id=gstr_ref.row_id if gstr_ref else None,
            book_source=f"{book_ref.source_file}:{book_ref.sheet_name}:{book_ref.excel_row_number}" if book_ref else "",
            gstr_source=f"{gstr_ref.source_file}:{gstr_ref.sheet_name}:{gstr_ref.excel_row_number}" if gstr_ref else "",
            note=note,
        ))

    matched = [r for r in records if r.status == "MATCHED"]
    mismatched = [r for r in records if r.status == "AMOUNT_MISMATCH"]
    missing_gstr = [r for r in records if r.status == "MISSING_IN_GSTR"]
    missing_books = [r for r in records if r.status == "MISSING_IN_BOOKS"]
    duplicate_records = [r for r in records if r.status == "DUPLICATE_KEY_REVIEW"]

    summary = GstrReconciliationSummary(
        book_rows_compared=len(book_rows),
        gstr_rows_compared=len(gstr_rows),
        matched_rows=len(matched),
        amount_mismatch_rows=len(mismatched),
        missing_in_gstr_rows=len(missing_gstr),
        missing_in_books_rows=len(missing_books),
        date_mismatch_rows=sum(1 for r in records if r.date_status == "DATE_MISMATCH"),
        period_mismatch_rows=sum(1 for r in records if r.period_status == "PERIOD_MISMATCH"),
        taxable_mismatch_rows=sum(1 for r in records if r.taxable_difference.copy_abs() > amount_tolerance),
        gst_mismatch_rows=sum(1 for r in records if r.gst_difference.copy_abs() > amount_tolerance),
        duplicate_book_keys=duplicate_book_keys,
        duplicate_gstr_keys=duplicate_gstr_keys,
        book_total=sum((r.invoice_value for r in book_rows), Decimal("0.00")),
        gstr_total=sum((r.invoice_value for r in gstr_rows), Decimal("0.00")),
        matched_book_total=sum((r.book_invoice_value for r in matched), Decimal("0.00")),
        matched_gstr_total=sum((r.gstr_invoice_value for r in matched), Decimal("0.00")),
        mismatch_difference_total=sum((r.difference for r in mismatched + duplicate_records), Decimal("0.00")),
        final_status="GSTR_REVIEW_REQUIRED" if (mismatched or missing_gstr or missing_books or duplicate_records) else "GSTR_FULLY_MATCHED",
    )
    return GstrReconciliationResult(records=records, summary=summary)
