from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

Decision = Literal["BLOCKED", "RCM", "REVIEW", "UNKNOWN"]


@dataclass(frozen=True)
class ComplianceOverride:
    decision: Decision
    reason: str
    source: str


# Conservative starter tables. These are deliberately review signals, not legal
# final decisions. CAs can override the output from the review workflow.
BLOCKED_ITC_HSN_PREFIXES: dict[str, str] = {
    "8703": "Motor cars and motor vehicles normally require Section 17(5) review.",
    "8704": "Motor vehicle category; verify eligibility before ITC claim.",
    "9963": "Restaurant/catering/food service category; possible blocked credit.",
    "9954": "Works contract/construction service category; possible blocked credit.",
    "9971": "Insurance/financial services category; verify blocked-credit conditions.",
}

RCM_HSN_PREFIXES: dict[str, str] = {
    "9965": "Goods transport agency/logistics service may require RCM review.",
    "9982": "Legal/accounting/professional service may require RCM review depending on supplier type.",
    "9985": "Security/manpower/renting service may require RCM review depending on category.",
}


def normalize_hsn_sac(value: object) -> str:
    """Return a 4-8 digit HSN/SAC candidate, or an empty string."""
    text = str(value or "")
    match = re.search(r"\b(\d{4,8})\b", text)
    return match.group(1) if match else ""


def lookup_itc_override(hsn_sac: object) -> ComplianceOverride:
    code = normalize_hsn_sac(hsn_sac)
    for prefix, reason in BLOCKED_ITC_HSN_PREFIXES.items():
        if code.startswith(prefix):
            return ComplianceOverride("BLOCKED", reason, f"HSN/SAC prefix {prefix}")
    if code:
        return ComplianceOverride("REVIEW", "HSN/SAC detected; no blocked-credit table match.", "HSN/SAC table")
    return ComplianceOverride("UNKNOWN", "No HSN/SAC code available for table lookup.", "HSN/SAC table")


def lookup_rcm_override(hsn_sac: object) -> ComplianceOverride:
    code = normalize_hsn_sac(hsn_sac)
    for prefix, reason in RCM_HSN_PREFIXES.items():
        if code.startswith(prefix):
            return ComplianceOverride("RCM", reason, f"HSN/SAC prefix {prefix}")
    if code:
        return ComplianceOverride("REVIEW", "HSN/SAC detected; no RCM table match.", "HSN/SAC table")
    return ComplianceOverride("UNKNOWN", "No HSN/SAC code available for table lookup.", "HSN/SAC table")
