from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable, Sequence

from app.core.models import InvoiceRow
from app.core.review_policy import is_mandatory_review, has_gst_or_amount_exception, is_trace_only, is_real_invoice_candidate


@dataclass(frozen=True)
class SupplierMetric:
    supplier_name: str
    gstin: str
    invoice_count: int
    invoice_value: Decimal
    taxable_value: Decimal
    gst_value: Decimal
    review_rows: int


@dataclass(frozen=True)
class MonthlyMetric:
    month_key: str
    invoice_count: int
    invoice_value: Decimal
    taxable_value: Decimal
    gst_value: Decimal
    review_rows: int


def gst_total(row: InvoiceRow) -> Decimal:
    return row.igst + row.cgst + row.sgst + row.cess


def row_search_blob(row: InvoiceRow) -> str:
    month_label = row.invoice_date.strftime("%b %Y") if row.invoice_date else ""
    date_label = row.invoice_date.isoformat() if row.invoice_date else ""
    parts = [
        row.supplier_name,
        row.gstin,
        getattr(row, "recipient_gstin", ""),
        row.invoice_no,
        row.hsn_sac,
        row.source_file,
        row.sheet_name,
        row.audit_status,
        row.audit_severity,
        row.mismatch_reason,
        row.audit_notes,
        row.period,
        month_label,
        date_label,
    ]
    return " ".join(str(part or "") for part in parts).lower()


def scoped_search_blob(row: InvoiceRow, search_field: str = "Auto") -> str:
    """Return only the fields relevant to the selected dashboard search mode."""
    field = (search_field or "Auto").strip().lower()
    month_label = row.invoice_date.strftime("%b %Y") if row.invoice_date else "Unknown"
    date_label = row.invoice_date.isoformat() if row.invoice_date else ""

    if field.startswith("company") or field.startswith("supplier"):
        parts = [row.supplier_name]
    elif "gst" in field:
        parts = [row.gstin, row.recipient_gstin, *row.all_gstins, row.gstin_roles_note]
    elif "invoice" in field and "number" in field:
        parts = [row.invoice_no, row.invoice_series, str(row.invoice_sequence_no or "")]
    elif "month" in field:
        parts = [month_label, row.period, date_label]
    elif "source" in field or "file" in field:
        parts = [row.source_file, row.sheet_name]
    elif "status" in field or "issue" in field:
        parts = [
            row.audit_status,
            row.audit_severity,
            row.audit_indicator,
            row.mismatch_reason,
            row.audit_notes,
            row.review_decision,
            row.invoice_gap_note,
            row.anomaly_note,
        ]
    else:
        return row_search_blob(row)
    return " ".join(str(part or "") for part in parts).lower()


def filter_rows(
    rows: Sequence[InvoiceRow],
    *,
    query: str = "",
    status: str = "All Rows",
    included_only: bool = False,
    search_field: str = "Auto",
) -> list[InvoiceRow]:
    query_norm = query.strip().lower()
    filtered: Iterable[InvoiceRow] = rows
    if included_only:
        filtered = [row for row in filtered if row.include_in_totals]

    if status and status != "All Rows":
        if status == "Approved":
            filtered = [row for row in filtered if row.include_in_totals]
        elif status in {"Review Required", "Critical Review"}:
            filtered = [row for row in filtered if is_mandatory_review(row)]
        elif status in {"Advisory / Accepted Differences", "Advisory Review"}:
            from app.core.review_policy import is_advisory_exception
            filtered = [row for row in filtered if is_advisory_exception(row)]
        elif status == "GST Mismatch":
            filtered = [row for row in filtered if has_gst_or_amount_exception(row)]
        elif status in {"Skipped / Excluded", "Trace / Excluded"}:
            from app.core.review_policy import is_advisory_exception
            filtered = [row for row in filtered if is_trace_only(row) and not is_mandatory_review(row) and not is_advisory_exception(row)]
        elif status == "High Severity":
            filtered = [row for row in filtered if row.audit_severity in {"HIGH", "CRITICAL"}]

    if query_norm:
        filtered = [row for row in filtered if query_norm in scoped_search_blob(row, search_field)]
    return list(filtered)


def supplier_summary(rows: Sequence[InvoiceRow], *, included_only: bool = True) -> list[SupplierMetric]:
    grouped: dict[str, dict[str, object]] = {}
    for row in rows:
        if included_only and not row.include_in_totals:
            continue
        if not is_real_invoice_candidate(row):
            continue
        key = row.gstin or f"NO_GSTIN::{row.supplier_name or 'UNKNOWN'}"
        item = grouped.setdefault(
            key,
            {
                "supplier_name": row.supplier_name or "UNKNOWN",
                "gstin": row.gstin or "",
                "invoice_count": 0,
                "invoice_value": Decimal("0"),
                "taxable_value": Decimal("0"),
                "gst_value": Decimal("0"),
                "review_rows": 0,
            },
        )
        item["invoice_count"] = int(item["invoice_count"]) + 1
        item["invoice_value"] = item["invoice_value"] + row.invoice_value  # type: ignore[operator]
        item["taxable_value"] = item["taxable_value"] + row.taxable_value  # type: ignore[operator]
        item["gst_value"] = item["gst_value"] + gst_total(row)  # type: ignore[operator]
        item["review_rows"] = int(item["review_rows"]) + (1 if is_mandatory_review(row) else 0)

    metrics = [SupplierMetric(**item) for item in grouped.values()]  # type: ignore[arg-type]
    return sorted(metrics, key=lambda metric: metric.invoice_value, reverse=True)


def monthly_summary(rows: Sequence[InvoiceRow], *, included_only: bool = True) -> list[MonthlyMetric]:
    grouped: dict[str, dict[str, object]] = defaultdict(lambda: {
        "month_key": "Unknown",
        "invoice_count": 0,
        "invoice_value": Decimal("0"),
        "taxable_value": Decimal("0"),
        "gst_value": Decimal("0"),
        "review_rows": 0,
    })
    sort_index: dict[str, int] = {}
    for row in rows:
        if included_only and not row.include_in_totals:
            continue
        if row.invoice_date:
            month_key = row.invoice_date.strftime("%b %Y")
            sort_index[month_key] = row.invoice_date.year * 100 + row.invoice_date.month
        else:
            month_key = "Unknown"
            sort_index[month_key] = 999999
        item = grouped[month_key]
        item["month_key"] = month_key
        item["invoice_count"] = int(item["invoice_count"]) + 1
        item["invoice_value"] = item["invoice_value"] + row.invoice_value  # type: ignore[operator]
        item["taxable_value"] = item["taxable_value"] + row.taxable_value  # type: ignore[operator]
        item["gst_value"] = item["gst_value"] + gst_total(row)  # type: ignore[operator]
        item["review_rows"] = int(item["review_rows"]) + (1 if is_mandatory_review(row) else 0)

    metrics = [MonthlyMetric(**item) for item in grouped.values()]  # type: ignore[arg-type]
    return sorted(metrics, key=lambda metric: (sort_index.get(metric.month_key, 999999), metric.month_key))


def _metric_value(row: InvoiceRow, metric: str) -> Decimal:
    if metric == "Taxable Value":
        return row.taxable_value
    if metric == "Total GST":
        return gst_total(row)
    if metric == "Invoice Count":
        return Decimal("1")
    if metric == "Review Rows":
        return Decimal("1") if is_mandatory_review(row) else Decimal("0")
    if metric == "Mismatch Amount":
        return abs(row.difference_amount)
    return row.invoice_value


def _group_key(row: InvoiceRow, group_by: str) -> tuple[str, int]:
    if group_by == "Supplier":
        return (row.supplier_name or "UNKNOWN", 0)
    if group_by == "GSTIN":
        return (row.gstin or "NO GSTIN", 0)
    if group_by == "Source File":
        return (row.source_file or "UNKNOWN", 0)
    if group_by == "Audit Status":
        return (row.audit_status or "UNKNOWN", 0)
    if group_by == "Mismatch Reason":
        return (row.mismatch_reason or "NO MISMATCH", 0)
    if group_by == "HSN/SAC":
        return (row.hsn_sac or "NO HSN/SAC", 0)
    if row.invoice_date:
        return (row.invoice_date.strftime("%b %Y"), row.invoice_date.year * 100 + row.invoice_date.month)
    return ("Unknown", 999999)


def grouped_chart_points(
    rows: Sequence[InvoiceRow],
    metric: str,
    group_by: str = "Month",
    *,
    limit: int = 12,
    included_only: bool = False,
) -> list[tuple[str, Decimal]]:
    """Return chart-ready points for a selected dashboard grouping.

    The function groups already-filtered rows only. It does not classify rows,
    recalculate official audit truth, or mutate input rows.
    """
    grouped: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    sort_index: dict[str, int] = {}
    for row in rows:
        if included_only and not row.include_in_totals:
            continue
        label, index = _group_key(row, group_by)
        grouped[label] += _metric_value(row, metric)
        if label not in sort_index or index < sort_index[label]:
            sort_index[label] = index

    points = list(grouped.items())
    if group_by == "Month":
        points.sort(key=lambda item: (sort_index.get(item[0], 999999), item[0]))
    else:
        points.sort(key=lambda item: item[1], reverse=True)
    if limit and limit > 0:
        points = points[:limit]
    return points


def chart_points(rows: Sequence[InvoiceRow], metric: str) -> list[tuple[str, Decimal]]:
    # Backward-compatible helper: old dashboard/tests expect month grouping.
    return grouped_chart_points(rows, metric, "Month", included_only=True, limit=0)
