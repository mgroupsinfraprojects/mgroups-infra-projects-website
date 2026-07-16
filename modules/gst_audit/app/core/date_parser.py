from __future__ import annotations

from datetime import date, datetime
from typing import Optional, Tuple

import pandas as pd

DATE_FORMATS = [
    "%d-%m-%Y",
    "%d/%m/%Y",
    "%Y-%m-%d",
    "%d.%m.%Y",
    "%d-%b-%Y",
    "%d/%b/%Y",
    "%d-%B-%Y",
    "%d/%B/%Y",
]


def parse_invoice_date(value: object) -> Tuple[Optional[date], str]:
    if value is None or pd.isna(value):
        return None, "MISSING_DATE"
    if isinstance(value, date) and not isinstance(value, datetime):
        return value, "DATE_OK"
    if isinstance(value, datetime):
        return value.date(), "DATE_OK"
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "nat"}:
        return None, "MISSING_DATE"
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date(), "DATE_OK"
        except ValueError:
            continue
    # Pandas fallback, fixed Indian day-first interpretation.
    parsed = pd.to_datetime(text, errors="coerce", dayfirst=True)
    if pd.isna(parsed):
        return None, "INVALID_DATE_FORMAT"
    return parsed.date(), "DATE_OK_FALLBACK"
