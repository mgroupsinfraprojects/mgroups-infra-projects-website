from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Iterable, List, Optional, Tuple

GSTIN_PATTERN = re.compile(r"\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b", re.IGNORECASE)
_CODEPOINT_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_CODEPOINTS = {char: index for index, char in enumerate(_CODEPOINT_CHARS)}


def normalize_text(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none", "nat"}:
        return ""
    return text


def normalize_gstin(value: object) -> str:
    text = normalize_text(value).upper().replace(" ", "")
    match = GSTIN_PATTERN.search(text)
    return match.group(0).upper() if match else ""


def find_all_gstins(values: Iterable[object]) -> List[str]:
    """Return unique GSTINs in row order from dirty cells."""
    seen: set[str] = set()
    found: List[str] = []
    for value in values:
        text = normalize_text(value).upper().replace(" ", "")
        for match in GSTIN_PATTERN.finditer(text):
            gstin = match.group(0).upper()
            if gstin not in seen:
                seen.add(gstin)
                found.append(gstin)
    return found


@lru_cache(maxsize=8192)
def calculate_gstin_checksum(first_14_chars: str) -> str:
    """Return the official GSTIN mod-36 checksum character for 14 chars."""
    text = normalize_text(first_14_chars).upper().replace(" ", "")
    if len(text) != 14:
        raise ValueError("GSTIN checksum requires exactly 14 characters")
    total = 0
    factor = 2
    for char in reversed(text):
        if char not in _CODEPOINTS:
            raise ValueError(f"Invalid GSTIN character: {char!r}")
        product = _CODEPOINTS[char] * factor
        total += (product // 36) + (product % 36)
        factor = 1 if factor == 2 else 2
    check_code_point = (36 - (total % 36)) % 36
    return _CODEPOINT_CHARS[check_code_point]


@lru_cache(maxsize=8192)
def has_valid_gstin_checksum(value: object) -> bool:
    text = normalize_text(value).upper().replace(" ", "")
    if not GSTIN_PATTERN.fullmatch(text):
        return False
    try:
        return calculate_gstin_checksum(text[:14]) == text[14]
    except ValueError:
        return False


def is_valid_gstin(value: object, *, require_checksum: bool = True) -> bool:
    text = normalize_text(value).upper().replace(" ", "")
    if not GSTIN_PATTERN.fullmatch(text):
        return False
    return has_valid_gstin_checksum(text) if require_checksum else True


def find_gstin(values: Iterable[object]) -> Optional[str]:
    matches = find_all_gstins(values)
    return matches[0] if matches else None


@dataclass(frozen=True)
class GstinRoleDetection:
    all_gstins: Tuple[str, ...] = field(default_factory=tuple)
    supplier_gstin: str = ""
    recipient_gstin: str = ""
    self_invoice: bool = False
    note: str = ""


def detect_gstin_roles(values: Iterable[object], *, self_gstins: Iterable[str] | None = None) -> GstinRoleDetection:
    """Detect supplier/recipient GSTINs without relying only on first match.

    Heuristic:
    - If configured self GSTIN appears, classify it as recipient/self GSTIN.
    - Supplier GSTIN is the first GSTIN that is not configured as self.
    - If all GSTINs equal self GSTIN, flag a self-invoice/same-party row.
    """
    all_gstins = find_all_gstins(values)
    configured_self = {str(g).strip().upper().replace(" ", "") for g in (self_gstins or []) if str(g).strip()}
    recipient = next((g for g in all_gstins if g in configured_self), "")
    supplier = next((g for g in all_gstins if g not in configured_self), "")
    self_invoice = bool(all_gstins and configured_self and all(g in configured_self for g in all_gstins))
    if not supplier and all_gstins:
        supplier = all_gstins[0]
    if len(all_gstins) >= 2 and not recipient:
        recipient = all_gstins[1]
    if self_invoice:
        note = "Only configured self GSTIN detected; possible self-invoice/self-entry."
    elif recipient and supplier:
        note = "Supplier and recipient/self GSTIN detected."
    elif supplier:
        note = "Supplier GSTIN detected."
    else:
        note = "GSTIN not detected."
    return GstinRoleDetection(all_gstins=tuple(all_gstins), supplier_gstin=supplier, recipient_gstin=recipient, self_invoice=self_invoice, note=note)
