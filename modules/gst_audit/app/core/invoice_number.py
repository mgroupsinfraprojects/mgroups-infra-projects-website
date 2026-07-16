from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

SERIES_PATTERN = re.compile(r"^(?P<prefix>.*?)(?P<num>\d+)(?P<suffix>\D*)$")


@dataclass(frozen=True)
class InvoiceNumberInfo:
    series: str = ""
    sequence: Optional[int] = None
    padded_width: int = 0


def parse_invoice_number(value: object) -> InvoiceNumberInfo:
    text = str(value or "").strip()
    if not text:
        return InvoiceNumberInfo()
    match = SERIES_PATTERN.match(text)
    if not match:
        return InvoiceNumberInfo(series=text.upper(), sequence=None, padded_width=0)
    num_text = match.group("num")
    prefix = (match.group("prefix") or "").strip().upper()
    suffix = (match.group("suffix") or "").strip().upper()
    series = f"{prefix}#{{n}}{suffix}"
    try:
        return InvoiceNumberInfo(series=series, sequence=int(num_text), padded_width=len(num_text))
    except ValueError:
        return InvoiceNumberInfo(series=series, sequence=None, padded_width=len(num_text))
