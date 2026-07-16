from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable, Sequence

import pandas as pd

from app.core.models import InvoiceRow
from app.core.gst_override_tables import lookup_itc_override, lookup_rcm_override

IRN_RE = re.compile(r"\b[a-fA-F0-9]{64}\b")
BLOCKED_ITC_KEYWORDS = {
    "motor vehicle",
    "car hire",
    "cab",
    "health insurance",
    "life insurance",
    "club membership",
    "food",
    "canteen",
    "works contract",
    "construction",
    "personal use",
}
RCM_KEYWORDS = {
    "reverse charge",
    "rcm",
    "goods transport agency",
    "gta",
    "advocate",
    "legal service",
    "security service",
    "renting motor vehicle",
    "import of service",
}
CREDIT_NOTE_TOKENS = {"CRN", "CREDIT", "CN", "CREDIT NOTE"}
DEBIT_NOTE_TOKENS = {"DBN", "DEBIT", "DN", "DEBIT NOTE"}


@dataclass(frozen=True)
class ComplianceCheck:
    row_id: int
    supplier_name: str
    gstin: str
    invoice_no: str
    itc_flag: str
    rcm_flag: str
    place_of_supply_flag: str
    note_type: str
    irn_flag: str
    notes: str


def _state_code(gstin: str) -> str:
    gstin = (gstin or "").strip().upper()
    return gstin[:2] if len(gstin) >= 2 and gstin[:2].isdigit() else ""


def detect_credit_debit_note(row: InvoiceRow) -> str:
    text = f"{row.invoice_no} {row.audit_notes} {' '.join(map(str, row.raw_snapshot or []))}".upper()
    if any(token in text for token in CREDIT_NOTE_TOKENS) or row.invoice_value < Decimal("0"):
        return "CREDIT_NOTE"
    if any(token in text for token in DEBIT_NOTE_TOKENS):
        return "DEBIT_NOTE"
    return "REGULAR_INVOICE"


def detect_itc_flag(row: InvoiceRow) -> tuple[str, str]:
    table_result = lookup_itc_override(row.hsn_sac)
    if table_result.decision == "BLOCKED":
        return "BLOCKED_ITC_REVIEW", f"{table_result.source}: {table_result.reason}"
    text = f"{row.supplier_name} {row.hsn_sac} {row.audit_notes} {' '.join(map(str, row.raw_snapshot or []))}".lower()
    matched = sorted(keyword for keyword in BLOCKED_ITC_KEYWORDS if keyword in text)
    if matched:
        return "BLOCKED_ITC_REVIEW", f"Possible Section 17(5) blocked-credit keyword(s): {', '.join(matched[:4])}"
    if not row.include_in_totals:
        return "NOT_COUNTED", "Row is not included in dashboard totals."
    if table_result.decision == "REVIEW":
        return "ITC_ELIGIBLE_REVIEWED", f"{table_result.source}: {table_result.reason} Accountant review still required."
    return "ITC_ELIGIBLE_REVIEWED", "No blocked-credit keyword or HSN/SAC table signal detected; accountant review still required."


def detect_rcm_flag(row: InvoiceRow) -> tuple[str, str]:
    table_result = lookup_rcm_override(row.hsn_sac)
    if table_result.decision == "RCM":
        return "POSSIBLE_RCM", f"{table_result.source}: {table_result.reason}"
    text = f"{row.supplier_name} {row.audit_notes} {' '.join(map(str, row.raw_snapshot or []))}".lower()
    matched = sorted(keyword for keyword in RCM_KEYWORDS if keyword in text)
    if matched:
        return "POSSIBLE_RCM", f"Possible reverse-charge keyword(s): {', '.join(matched[:4])}"
    if table_result.decision == "REVIEW":
        return "NO_RCM_SIGNAL", f"{table_result.source}: {table_result.reason}"
    return "NO_RCM_SIGNAL", "No reverse-charge keyword or HSN/SAC table signal detected."


def check_place_of_supply(row: InvoiceRow, self_gstins: Sequence[str] = ()) -> tuple[str, str]:
    supplier_state = _state_code(row.gstin)
    recipient_gstin = row.recipient_gstin or (self_gstins[0] if self_gstins else "")
    recipient_state = _state_code(recipient_gstin)
    if not supplier_state or not recipient_state:
        return "POS_UNKNOWN", "Supplier or recipient GSTIN state code is missing."
    has_igst = row.igst > 0
    has_cgst_sgst = row.cgst > 0 or row.sgst > 0
    if supplier_state == recipient_state and has_igst and not has_cgst_sgst:
        return "POSSIBLE_TAX_TYPE_ERROR", "Same-state GSTINs normally use CGST+SGST, but row has IGST only."
    if supplier_state != recipient_state and has_cgst_sgst and not has_igst:
        return "POSSIBLE_TAX_TYPE_ERROR", "Different-state GSTINs normally use IGST, but row has CGST/SGST."
    return "POS_TAX_TYPE_OK", "Tax type appears consistent with GSTIN state codes."


def detect_irn_flag(row: InvoiceRow) -> tuple[str, str]:
    text = f"{row.audit_notes} {' '.join(map(str, row.raw_snapshot or []))}"
    if IRN_RE.search(text):
        return "IRN_PRESENT_FORMAT_OK", "64-character hex IRN-like value detected."
    return "IRN_NOT_FOUND", "No 64-character IRN detected in the visible row text."


def compliance_check(row: InvoiceRow, self_gstins: Sequence[str] = ()) -> ComplianceCheck:
    itc_flag, itc_note = detect_itc_flag(row)
    rcm_flag, rcm_note = detect_rcm_flag(row)
    pos_flag, pos_note = check_place_of_supply(row, self_gstins=self_gstins)
    irn_flag, irn_note = detect_irn_flag(row)
    note_type = detect_credit_debit_note(row)
    return ComplianceCheck(
        row_id=row.row_id,
        supplier_name=row.supplier_name,
        gstin=row.gstin,
        invoice_no=row.invoice_no,
        itc_flag=itc_flag,
        rcm_flag=rcm_flag,
        place_of_supply_flag=pos_flag,
        note_type=note_type,
        irn_flag=irn_flag,
        notes=" | ".join([itc_note, rcm_note, pos_note, irn_note]),
    )


def compliance_checks(rows: Iterable[InvoiceRow], self_gstins: Sequence[str] = ()) -> list[ComplianceCheck]:
    return [compliance_check(row, self_gstins=self_gstins) for row in rows]


def compliance_dataframe(rows: Iterable[InvoiceRow], self_gstins: Sequence[str] = ()) -> pd.DataFrame:
    return pd.DataFrame([check.__dict__ for check in compliance_checks(rows, self_gstins=self_gstins)])
