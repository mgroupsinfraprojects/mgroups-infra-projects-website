from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Tuple

import pandas as pd

FIELD_KEYWORDS = {
    "gstin": ["gstin", "gst no", "gst number", "gstin of supplier", "supplier gstin", "gstin/uin of supplier", "gstin/uin", "gstin/uin no", "gstin of supplier/recipient", "ctin"],
    "supplier_name": ["trade/legal name", "trade name", "legal name", "supplier name", "vendor", "vendor name", "party name", "particulars", "trade/legal name of supplier", "legal name of supplier", "name of supplier", "supplier legal name"],
    "invoice_no": ["invoice number", "invoice no", "inv no", "bill no", "voucher no", "supplier invoice no", "reference no", "document number", "document no", "invoice/document number", "invoice details invoice number", "note number", "note no", "credit note number", "debit note number"],
    "invoice_date": ["invoice date", "bill date", "date", "date of invoice", "document date", "invoice/document date", "invoice details invoice date", "note date", "credit note date", "debit note date"],
    "hsn_sac": ["hsn/sac", "hsn sac", "hsn", "sac", "hsn code", "sac code"],
    "invoice_value": ["invoice value", "invoice amount", "grand total", "gross amount", "total invoice", "total invoice value", "document value", "note value", "note value(₹)", "credit note value", "debit note value"],
    "taxable_value": ["taxable value", "taxable value(₹)", "taxable amount", "txval", "assessable value"],
    "igst": ["integrated tax", "integrated tax(₹)", "integrated tax amount", "igst", "iamt"],
    "cgst": ["central tax", "central tax(₹)", "central tax amount", "cgst", "camt"],
    "sgst": ["state/ut tax", "state/ut tax(₹)", "state tax", "state tax amount", "sgst", "utgst", "samt"],
    "cess": ["cess"],
    "period": ["period", "month", "return period", "tax period", "filing period", "gstr-1", "gstr-2b", "gstr", "fp"],
}

HEADER_WORDS = [word for words in FIELD_KEYWORDS.values() for word in words]


@dataclass(frozen=True)
class HeaderDetection:
    field_map: Dict[str, int]
    header_row: int
    data_start: int
    score: int
    uncertain: bool
    warning: str = ""


def _clean(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value).strip().lower())


def _score_text(text: str) -> int:
    return sum(1 for word in HEADER_WORDS if word in text)


def detect_header_map_with_metadata(
    df: pd.DataFrame,
    max_scan_rows: int = 30,
    *,
    min_score: int = 2,
) -> HeaderDetection:
    """Detect column headers and return confidence metadata.

    A score of zero must not silently select row 0 as a header. In that case we
    start parsing at the first physical row with an empty field map. The row-level
    scanner can still detect GSTINs, but amount/date fields will remain reviewable
    instead of being silently mapped to wrong columns.
    """
    best_row = 0
    best_score = -1
    scan_limit = min(max_scan_rows, len(df))
    for idx in range(scan_limit):
        row_text = " ".join(_clean(v) for v in df.iloc[idx].tolist())
        next_text = ""
        if idx + 1 < len(df):
            next_text = " ".join(_clean(v) for v in df.iloc[idx + 1].tolist())
        score = _score_text(row_text + " " + next_text)
        if score > best_score:
            best_score = score
            best_row = idx

    if best_score < min_score:
        return HeaderDetection(
            field_map={},
            header_row=0,
            data_start=0,
            score=max(best_score, 0),
            uncertain=True,
            warning=(
                f"Header detection confidence too low (score={max(best_score, 0)}, minimum={min_score}). "
                "Columns were not auto-mapped; affected rows require review."
            ),
        )

    field_map: Dict[str, int] = {}
    current_text_for_header = " ".join(_clean(v) for v in df.iloc[best_row].tolist()) if best_row < len(df) else ""
    current_header_score = _score_text(current_text_for_header)
    next_text_for_header = ""
    if best_row + 1 < len(df):
        next_text_for_header = " ".join(_clean(v) for v in df.iloc[best_row + 1].tolist())
    # Combine the next physical row only when the best header row looks like a
    # category band. If the current row already contains direct fields such as
    # GSTIN, Trade/Legal name, Invoice number, Taxable value, and Invoice Value,
    # the next row is often another GSTR-2B section/header band, not a subheader.
    current_cells = [_clean(v) for v in df.iloc[best_row].tolist()] if best_row < len(df) else []
    current_has_header_blanks = any(not cell for cell in current_cells)
    next_row_has_subheader = _score_text(next_text_for_header) >= 2 and (current_header_score < 4 or current_has_header_blanks)
    for col in range(df.shape[1]):
        current = _clean(df.iat[best_row, col]) if best_row < len(df) else ""
        nxt = _clean(df.iat[best_row + 1, col]) if (next_row_has_subheader and best_row + 1 < len(df)) else ""
        combined = f"{current} {nxt}".strip()
        for field, keywords in FIELD_KEYWORDS.items():
            if field in field_map:
                continue
            if any(keyword in combined for keyword in keywords):
                if field == "invoice_date" and "filing date" in combined:
                    continue
                if field == "invoice_value" and "tax amount" in combined:
                    continue
                field_map[field] = col

    data_start = best_row + (2 if next_row_has_subheader else 1)
    return HeaderDetection(field_map=field_map, header_row=best_row, data_start=data_start, score=best_score, uncertain=False)


def detect_header_map(df: pd.DataFrame, max_scan_rows: int = 30) -> Tuple[Dict[str, int], int, int]:
    """Backward-compatible API returning (field_to_column, header_row, data_start)."""
    detection = detect_header_map_with_metadata(df, max_scan_rows=max_scan_rows)
    return detection.field_map, detection.header_row, detection.data_start
