from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, Mapping, Sequence
import re

import pandas as pd

CANONICAL_FIELDS: tuple[str, ...] = (
    "supplier_gstin",
    "supplier_name",
    "invoice_no",
    "invoice_date",
    "hsn_sac",
    "taxable_value",
    "igst",
    "cgst",
    "sgst",
    "cess",
    "invoice_value",
    "recipient_gstin",
    "itc_eligibility",
    "reverse_charge",
    "period",
)

_HEADER_NORMALIZER = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class ImportProfile:
    """Column-name mapping profile for common GST/accounting exports."""

    name: str
    description: str
    aliases: Mapping[str, tuple[str, ...]] = field(default_factory=dict)

    def normalized_aliases(self) -> dict[str, tuple[str, ...]]:
        return {field: tuple(normalize_header(alias) for alias in values) for field, values in self.aliases.items()}


def normalize_header(value: object) -> str:
    """Normalize messy headers into a comparison-safe token."""
    return _HEADER_NORMALIZER.sub("", str(value or "").strip().lower())


STANDARD_PROFILE = ImportProfile(
    name="Standard GST Invoice Excel",
    description="Generic GST purchase/sales invoice format used by this app.",
    aliases={
        "supplier_gstin": ("supplier gstin", "gstin of supplier", "gst no", "gstin", "vendor gstin"),
        "supplier_name": ("supplier name", "trade/legal name", "party name", "vendor name", "particulars"),
        "invoice_no": ("invoice no", "invoice number", "bill no", "voucher no", "document number"),
        "invoice_date": ("invoice date", "bill date", "voucher date", "document date", "date"),
        "hsn_sac": ("hsn", "hsn/sac", "sac", "item hsn"),
        "taxable_value": ("taxable value", "assessable value", "taxable amount", "taxable amt"),
        "igst": ("igst", "integrated tax", "igst amount"),
        "cgst": ("cgst", "central tax", "cgst amount"),
        "sgst": ("sgst", "state tax", "sgst amount", "utgst"),
        "cess": ("cess", "cess amount"),
        "invoice_value": ("invoice value", "total invoice value", "gross total", "total amount", "net amount"),
        "recipient_gstin": ("recipient gstin", "my gstin", "receiver gstin", "customer gstin"),
        "itc_eligibility": ("itc availability", "itc eligibility", "eligible itc", "itc available"),
        "reverse_charge": ("reverse charge", "rcm", "reverse charge flag"),
        "period": ("return period", "period", "month"),
    },
)

TALLY_PROFILE = ImportProfile(
    name="Tally Prime / Tally ERP Export",
    description="Typical Tally purchase register/GST report headers.",
    aliases={
        **STANDARD_PROFILE.aliases,
        "supplier_name": ("party name", "particulars", "ledger name", "supplier name"),
        "invoice_no": ("voucher no", "voucher number", "supplier invoice no", "reference no"),
        "invoice_date": ("voucher date", "date", "supplier invoice date"),
        "invoice_value": ("gross total", "net total", "bill amount", "total"),
    },
)

GST_PORTAL_PROFILE = ImportProfile(
    name="GST Portal GSTR-2A/2B",
    description="GST portal GSTR-2A/2B downloaded data.",
    aliases={
        **STANDARD_PROFILE.aliases,
        "supplier_gstin": ("gstin of supplier", "supplier gstin", "ctin"),
        "supplier_name": ("trade/legal name", "supplier name", "legal name"),
        "invoice_no": ("invoice number", "inum", "invoice no"),
        "invoice_date": ("invoice date", "idt"),
        "invoice_value": ("invoice value", "val"),
        "taxable_value": ("taxable value", "txval"),
        "igst": ("integrated tax", "iamt", "igst"),
        "cgst": ("central tax", "camt", "cgst"),
        "sgst": ("state/ut tax", "samt", "sgst"),
        "itc_eligibility": ("itc availability", "itc available", "eligible itc"),
        "reverse_charge": ("reverse charge", "rchrg", "rcm"),
        "period": ("return period", "period", "fp"),
    },
)

BUSY_PROFILE = ImportProfile(
    name="Busy Accounting Export",
    description="Common Busy accounting invoice/GST register headers.",
    aliases={
        **STANDARD_PROFILE.aliases,
        "supplier_name": ("party", "party name", "account name", "supplier name"),
        "invoice_no": ("bill no", "bill number", "voucher no", "invoice no"),
        "invoice_date": ("bill date", "date", "voucher date"),
    },
)

ZOHO_PROFILE = ImportProfile(
    name="Zoho Books Export",
    description="Common Zoho Books invoice/bill export headers.",
    aliases={
        **STANDARD_PROFILE.aliases,
        "supplier_name": ("vendor name", "customer name", "supplier name"),
        "invoice_no": ("bill number", "invoice number", "reference number"),
        "invoice_date": ("bill date", "invoice date", "date"),
        "invoice_value": ("total", "balance", "amount"),
    },
)

SAP_PROFILE = ImportProfile(
    name="SAP / ERP Export",
    description="Generic SAP/custom ERP purchase register export profile.",
    aliases={
        **STANDARD_PROFILE.aliases,
        "supplier_name": ("vendor", "vendor name", "name 1", "supplier name"),
        "invoice_no": ("reference", "document number", "invoice reference", "invoice no"),
        "invoice_date": ("document date", "posting date", "invoice date"),
    },
)

PROFILES: tuple[ImportProfile, ...] = (
    STANDARD_PROFILE,
    TALLY_PROFILE,
    GST_PORTAL_PROFILE,
    BUSY_PROFILE,
    ZOHO_PROFILE,
    SAP_PROFILE,
)


def detect_profile(columns: Sequence[object], profiles: Sequence[ImportProfile] = PROFILES) -> tuple[ImportProfile, int]:
    """Return the best matching profile and its confidence score."""
    normalized_columns = {normalize_header(col) for col in columns}
    best_profile = STANDARD_PROFILE
    best_score = -1
    for profile in profiles:
        score = 0
        for aliases in profile.normalized_aliases().values():
            if any(alias in normalized_columns for alias in aliases):
                score += 1
        if score > best_score:
            best_profile = profile
            best_score = score
    return best_profile, best_score


def map_columns(columns: Sequence[object], profile: ImportProfile | None = None) -> dict[str, str]:
    """Map dataframe columns to canonical audit fields using the chosen profile."""
    selected_profile = profile or detect_profile(columns)[0]
    normalized_to_original = {normalize_header(col): str(col) for col in columns}
    mapped: dict[str, str] = {}
    for field_name, aliases in selected_profile.normalized_aliases().items():
        for alias in aliases:
            if alias in normalized_to_original:
                mapped[field_name] = normalized_to_original[alias]
                break
    return mapped


def validate_required_mapping(mapping: Mapping[str, str]) -> list[str]:
    """Return mandatory canonical fields that are missing from a mapping."""
    required = ("supplier_gstin", "supplier_name", "invoice_no", "invoice_date", "invoice_value")
    return [field for field in required if field not in mapping]


def apply_mapping(df: pd.DataFrame, mapping: Mapping[str, str]) -> pd.DataFrame:
    """Return a canonical-column dataframe without mutating the source dataframe."""
    canonical = pd.DataFrame(index=df.index)
    for field in CANONICAL_FIELDS:
        source = mapping.get(field)
        canonical[field] = df[source] if source in df.columns else ""
    return canonical


def profiles_dataframe() -> pd.DataFrame:
    rows = []
    for profile in PROFILES:
        rows.append({
            "profile": profile.name,
            "description": profile.description,
            "supported_fields": ", ".join(sorted(profile.aliases.keys())),
        })
    return pd.DataFrame(rows)
