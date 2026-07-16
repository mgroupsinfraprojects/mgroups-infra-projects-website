from __future__ import annotations

from decimal import Decimal
from app.core.models import InvoiceRow
from app.core.review_thresholds import DEFAULT_REVIEW_THRESHOLDS, load_review_thresholds

CLEAN_REASONS = {
    "",
    "BALANCED_OR_ROUNDING",
    "MINOR_ROUNDING_OR_DECIMAL_ISSUE",
    "AUTO_ACCEPT_SMALL_DIFFERENCE",
    "AUTO_ACCEPT_SMALL_EXPENSE_OR_ROUNDING",
    "CREDIT_NOTE_BALANCED",
    "CREDIT_NOTE_ZERO_RATED",
}

ADVISORY_REASONS = {
    "POSSIBLE_FREIGHT_OR_DISCOUNT",
    "INVOICE_VALUE_INCLUDES_EXPENSES",
    "ROUNDING_IN_MULTIPLE_COMPONENTS",
    "SMALL_PERCENTAGE_DIFFERENCE_CHECK_FREIGHT_ROUNDING",
    "TCS_TDS_DETECTED",
}

CRITICAL_REASONS = {
    "UNEXPLAINED_GST_MISMATCH",
    "GST_COMPONENT_MISSING_OR_EXEMPT_CHECK",
    "INVOICE_LESS_THAN_TAXABLE_POSSIBLE_COLUMN_SHIFT",
    "COMPONENT_SIGN_MISMATCH",
    "CREDIT_NOTE_MISMATCH",
}

MANDATORY_REVIEW_AMOUNT = DEFAULT_REVIEW_THRESHOLDS["critical_amount"]



def _money_values(row: InvoiceRow) -> list[Decimal]:
    return [
        getattr(row, "taxable_value", Decimal("0")),
        getattr(row, "igst", Decimal("0")),
        getattr(row, "cgst", Decimal("0")),
        getattr(row, "sgst", Decimal("0")),
        getattr(row, "cess", Decimal("0")),
        getattr(row, "invoice_value", Decimal("0")),
        getattr(row, "expected_invoice_value", Decimal("0")),
        getattr(row, "difference_amount", Decimal("0")),
    ]


def has_financial_value(row: InvoiceRow) -> bool:
    return any(abs(value) > Decimal("0.00") for value in _money_values(row))


def has_supplier_identity(row: InvoiceRow) -> bool:
    return bool((getattr(row, "supplier_name", "") or "").strip() and (getattr(row, "gstin", "") or "").strip())


def has_invoice_identity(row: InvoiceRow) -> bool:
    return bool((getattr(row, "invoice_no", "") or "").strip() or getattr(row, "invoice_date", None))


def is_real_invoice_candidate(row: InvoiceRow) -> bool:
    """True only for rows that can represent a supplier invoice/note.

    The human review queue must not contain read-me rows, summary rows, empty
    rows, ITC explanation lines, or formula/helper rows. Supplier identity is
    preferred, but a row with an invoice number and explicit GSTIN/supplier
    missing notes is still a real review item.
    """
    if is_support_or_summary_row(row) or is_empty_or_noise_row(row):
        return False
    if has_supplier_identity(row) and (has_invoice_identity(row) or has_financial_value(row)):
        return True
    # A row with supplier name but missing GSTIN/invoice fields can still be a
    # real review item when it carries value and the engine marked it critical.
    if (getattr(row, "supplier_name", "") or "").strip() and bool(getattr(row, "review_required", False)) and has_financial_value(row):
        return True
    notes = _notes(row)
    explicit_identity_issue = (
        "GSTIN NOT DETECTED" in notes
        or "GSTIN CHECKSUM" in notes
        or "SUPPLIER NAME MISSING" in notes
        or "INVOICE NUMBER MISSING" in notes
    )
    return bool(explicit_identity_issue and (has_invoice_identity(row) or has_financial_value(row)))


def is_meaningful_duplicate_row(row: InvoiceRow) -> bool:
    """Duplicate tab/count should show only real duplicate supplier invoices.

    Do not treat every excluded row with a duplicate key as a human-review duplicate.
    In GSTR files, helper/reconstructed rows can carry repeated keys even when the
    true issue is only a small rounding variance. A duplicate is reviewable only
    when the engine explicitly marked the row/status/note as duplicate and the
    invoice amount crosses the admin duplicate threshold.
    """
    thresholds = load_review_thresholds()
    status = _status(row)
    reason = _reason(row)
    notes = _notes(row)
    explicitly_duplicate = "DUPLICATE" in status or "DUPLICATE" in reason or "DUPLICATE" in notes
    if not (explicitly_duplicate and is_real_invoice_candidate(row)):
        return False
    if reason in ADVISORY_REASONS and abs(getattr(row, "difference_amount", Decimal("0"))) < thresholds["critical_amount"]:
        return False
    row_value = max(abs(getattr(row, "invoice_value", Decimal("0"))), abs(getattr(row, "expected_invoice_value", Decimal("0"))))
    return row_value >= thresholds.get("duplicate_min_amount", Decimal("100.00"))


def has_required_date_problem(row: InvoiceRow) -> bool:
    if not is_real_invoice_candidate(row):
        return False
    notes = _notes(row)
    reason = _reason(row)
    return bool(not getattr(row, "invoice_date", None) or "DATE" in notes or "DATE" in reason)


SUPPORT_SHEET_KEYWORDS = {
    "READ ME", "README", "ALL TABLES", "ELIGIBILITY", "ITC", "ISD", "IMPG", "IMPGSEZ",
    "AMENDMENT", "B2BA", "CDNRA", "CDNR", "CREDIT NOTES", "DEBIT NOTES", "REJECTION", "REVERSAL",
}

SUPPORT_ROW_KEYWORDS = {
    "PART A", "PART B", "ELIGIBILITY OF ITC", "WHETHER ITC", "ISD", "CREDIT NOTES", "DEBIT NOTES",
    "AMENDMENT", "REVERSE CHARGE", "SUPPLIES FROM REGISTERED", "RULE 37A",
}


def is_support_or_summary_row(row: InvoiceRow) -> bool:
    """GSTR-2B support/read-me/ITC summary rows must not be treated as invoice-critical.

    These rows are useful evidence, but they are not supplier invoice rows. Earlier
    builds marked many such rows as Missing ID because they naturally do not have
    GSTIN/invoice number fields. That made the review queue look broken.
    """
    sheet = str(getattr(row, "sheet_name", "") or "").upper()
    supplier = str(getattr(row, "supplier_name", "") or "").upper()
    notes = _notes(row)
    raw = " ".join(str(v or "") for v in getattr(row, "raw_snapshot", [])[:12]).upper()
    text = " ".join([sheet, supplier, notes, raw])
    if any(key in sheet for key in SUPPORT_SHEET_KEYWORDS):
        # B2B/CDNR sheets can still contain real invoice rows if identity exists.
        has_identity = bool(getattr(row, "gstin", "") and getattr(row, "invoice_no", ""))
        if not has_identity:
            return True
    if any(key in text for key in SUPPORT_ROW_KEYWORDS):
        has_invoice_identity = bool(getattr(row, "gstin", "") and getattr(row, "invoice_no", ""))
        if not has_invoice_identity:
            return True
    # No identity and zero financial value is not an invoice, even if reconstructed.
    amount_fields = [
        getattr(row, "taxable_value", Decimal("0")), getattr(row, "igst", Decimal("0")),
        getattr(row, "cgst", Decimal("0")), getattr(row, "sgst", Decimal("0")),
        getattr(row, "cess", Decimal("0")), getattr(row, "invoice_value", Decimal("0")),
    ]
    if not any([getattr(row, "gstin", ""), getattr(row, "invoice_no", "")]) and not any(abs(v) > Decimal("0.00") for v in amount_fields):
        return True
    return False


def _reason(row: InvoiceRow) -> str:
    return str(getattr(row, "mismatch_reason", "") or "").upper()


def _notes(row: InvoiceRow) -> str:
    return str(getattr(row, "audit_notes", "") or "").upper()


def _status(row: InvoiceRow) -> str:
    return str(getattr(row, "audit_status", "") or "").upper()


def _severity(row: InvoiceRow) -> str:
    return str(getattr(row, "audit_severity", "") or "").upper()


def is_empty_or_noise_row(row: InvoiceRow) -> bool:
    """Rows that should be traceable but should not enter the human review queue."""
    status = _status(row)
    reason = _reason(row)
    if status.startswith("SKIPPED") or status.startswith("ERROR"):
        return True
    if reason == "NO_AMOUNT_DETECTED" and not any([
        getattr(row, "supplier_name", ""), getattr(row, "gstin", ""), getattr(row, "invoice_no", "")
    ]):
        return True
    # Fully blank/helper rows are not reviewable even if a parser reconstructed a placeholder.
    if not any([getattr(row, "supplier_name", ""), getattr(row, "gstin", ""), getattr(row, "invoice_no", "")]) and not has_financial_value(row):
        return True
    return False


def has_required_identity_problem(row: InvoiceRow) -> bool:
    if is_support_or_summary_row(row):
        return False
    notes = _notes(row)
    if "GSTIN NOT DETECTED" in notes or "GSTIN CHECKSUM" in notes or "FORMAT INVALID" in notes:
        return True
    if "SUPPLIER NAME MISSING" in notes or "INVOICE NUMBER MISSING" in notes:
        return True
    if not getattr(row, "supplier_name", "") or not getattr(row, "gstin", "") or not getattr(row, "invoice_no", ""):
        return bool(getattr(row, "review_required", False))
    return False


def has_required_amount_problem(row: InvoiceRow) -> bool:
    """Return True only when the value/GST variance crosses admin thresholds.

    Identity and duplicate errors are handled separately. This prevents small
    rounding/freight/TDS/TCS differences from flooding Fix Issues.
    """
    thresholds = load_review_thresholds()
    reason = _reason(row)
    diff = abs(getattr(row, "difference_amount", Decimal("0")))
    diff_pct = abs(getattr(row, "difference_percent", Decimal("0")))
    invoice_value = getattr(row, "invoice_value", Decimal("0"))
    taxable_value = getattr(row, "taxable_value", Decimal("0"))

    if reason in CLEAN_REASONS and diff < thresholds["critical_amount"]:
        return False
    if diff < thresholds["ignore_amount"]:
        return False
    # Low/freight/rounding/TDS/TCS advisory reasons must not block review unless
    # the variance itself crosses the admin critical range.
    if reason in ADVISORY_REASONS and diff < thresholds["critical_amount"]:
        return False
    if invoice_value < taxable_value and diff >= thresholds["critical_amount"]:
        return True
    if reason in CRITICAL_REASONS:
        gst_like = "GST" in reason or "COMPONENT" in reason
        limit = thresholds.get("gst_critical_amount", thresholds["critical_amount"]) if gst_like else thresholds["critical_amount"]
        return diff >= limit
    if _severity(row) in {"HIGH", "CRITICAL"} and (diff >= thresholds["critical_amount"] or diff_pct >= thresholds["critical_percent"]):
        return True
    return False


def is_mandatory_review(row: InvoiceRow) -> bool:
    """Human queue policy: only important rows should block the reviewer.

    Minor rounding, tiny freight/TCS/TDS-style differences, duplicates already
    excluded from totals, and empty/noise rows stay traceable but are not put in
    the default review queue.
    """
    if not bool(getattr(row, "review_required", False)):
        return False
    if is_empty_or_noise_row(row) or is_support_or_summary_row(row):
        return False
    if not is_real_invoice_candidate(row):
        return False
    if is_meaningful_duplicate_row(row):
        return True
    # Identity errors must remain mandatory even when the amount formula itself
    # is otherwise clean. Missing GSTIN/supplier/invoice number makes the row
    # unverifiable for audit purposes.
    if has_required_identity_problem(row):
        return True
    if _reason(row) in CLEAN_REASONS:
        return False
    if has_required_amount_problem(row):
        return True
    return False


def is_advisory_exception(row: InvoiceRow) -> bool:
    if is_empty_or_noise_row(row):
        return False
    if is_support_or_summary_row(row):
        return False
    if not is_real_invoice_candidate(row):
        return False
    reason = _reason(row)
    if reason in CLEAN_REASONS:
        return False
    if is_mandatory_review(row):
        return False
    thresholds = load_review_thresholds()
    diff = abs(getattr(row, "difference_amount", Decimal("0")))
    # Small value variance stays trace-only unless there is an actual identity/date issue.
    if diff < thresholds["advisory_amount"] and not has_required_identity_problem(row) and not has_required_date_problem(row) and not is_meaningful_duplicate_row(row):
        return False
    # Non-included invoice rows with no real reason should remain trace-only, not advisory noise.
    return bool(reason or getattr(row, "review_required", False))


def has_gst_or_amount_exception(row: InvoiceRow) -> bool:
    if is_empty_or_noise_row(row) or not is_real_invoice_candidate(row):
        return False
    thresholds = load_review_thresholds()
    reason = _reason(row)
    diff = abs(getattr(row, "difference_amount", Decimal("0")))
    if reason in CLEAN_REASONS:
        return False
    # This helper is used for analytics/search labels. It may identify a low-risk
    # exception, but Fix Issues/mandatory review still uses admin thresholds in
    # is_mandatory_review().
    if reason in CRITICAL_REASONS or reason in ADVISORY_REASONS:
        return True
    return diff >= thresholds["advisory_amount"]


def is_trace_only(row: InvoiceRow) -> bool:
    if is_meaningful_duplicate_row(row):
        return False
    return (
        is_support_or_summary_row(row)
        or is_empty_or_noise_row(row)
        or (not getattr(row, "include_in_totals", True) and not is_real_invoice_candidate(row))
        or _status(row).startswith("SKIPPED")
    )
