from __future__ import annotations

import re
from dataclasses import dataclass

HSN_SAC_PATTERN = re.compile(r"\b\d{4,8}\b")

# Basic sanity range. HSN chapters generally use 01-99; SAC services commonly begin with 99.
_VALID_PREFIXES = {f"{i:02d}" for i in range(1, 100)}


@dataclass(frozen=True)
class HsnValidation:
    code: str = ""
    is_valid: bool = False
    note: str = "HSN/SAC not detected"


def extract_hsn_sac(text: object) -> str:
    match = HSN_SAC_PATTERN.search(str(text or ""))
    return match.group(0) if match else ""


def validate_hsn_sac(code: object) -> HsnValidation:
    value = str(code or "").strip()
    if not value:
        return HsnValidation("", False, "HSN/SAC not detected")
    if not value.isdigit():
        return HsnValidation(value, False, "HSN/SAC must contain digits only")
    if len(value) < 4 or len(value) > 8:
        return HsnValidation(value, False, "HSN/SAC length must be 4 to 8 digits")
    if value[:2] not in _VALID_PREFIXES:
        return HsnValidation(value, False, "HSN/SAC chapter prefix is outside 01-99")
    return HsnValidation(value, True, "HSN/SAC basic validation passed")
