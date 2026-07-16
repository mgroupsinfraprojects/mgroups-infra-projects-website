from __future__ import annotations

import math
import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Optional

NUMERIC_RE = re.compile(r"[-+]?\d[\d,]*(?:\.\d+)?")


def to_decimal(value: object) -> Decimal:
    if value is None:
        return Decimal("0.00")
    if isinstance(value, Decimal):
        return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if isinstance(value, (int, float)):
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return Decimal("0.00")
        return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "nat"}:
        return Decimal("0.00")
    text = text.replace("₹", "").replace(",", "").replace(" ", "")
    match = NUMERIC_RE.search(text)
    if not match:
        return Decimal("0.00")
    try:
        return Decimal(match.group(0).replace(",", "")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except InvalidOperation:
        return Decimal("0.00")


def money_float(value: object) -> float:
    return float(to_decimal(value))


def _indian_group_number(number_text: str) -> str:
    """Return a whole-number string using Indian comma grouping."""
    if len(number_text) <= 3:
        return number_text

    last_three = number_text[-3:]
    remaining = number_text[:-3]
    groups: list[str] = []

    while len(remaining) > 2:
        groups.insert(0, remaining[-2:])
        remaining = remaining[:-2]

    if remaining:
        groups.insert(0, remaining)

    return ",".join(groups + [last_three])


def format_inr_full(value: object) -> str:
    """
    Full exact INR display with Indian comma grouping.

    Example:
        193800000 -> ₹19,38,00,000.00
    """
    amount = to_decimal(value)
    sign = "-" if amount < 0 else ""
    amount = abs(amount)

    whole, decimal = f"{amount:.2f}".split(".")
    return f"{sign}₹{_indian_group_number(whole)}.{decimal}"


def format_inr_compact(value: object) -> str:
    """
    Compact INR display for small dashboard/chart labels.

    Example:
        193800000 -> ₹19.38Cr
    """
    amount_decimal = to_decimal(value)
    sign = "-" if amount_decimal < 0 else ""
    amount = abs(float(amount_decimal))

    if amount >= 10_000_000:
        return f"{sign}₹{amount / 10_000_000:.2f}Cr"
    if amount >= 100_000:
        return f"{sign}₹{amount / 100_000:.2f}L"
    if amount >= 1_000:
        return f"{sign}₹{amount / 1_000:.1f}K"
    return f"{sign}₹{amount:.2f}"


def format_inr(value: object) -> str:
    """Default UI money formatter: full amount, no Cr/L/K abbreviation."""
    return format_inr_full(value)
