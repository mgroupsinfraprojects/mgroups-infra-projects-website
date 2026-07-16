from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Iterable

from app.core.models import InvoiceRow
from app.core.review_queue_engine import ReviewQueueItem, build_review_queue


@dataclass(frozen=True)
class SupplierDrilldown:
    supplier_key: str
    supplier_name: str
    gstin: str
    invoice_count: int
    approved_invoice_count: int
    mandatory_review_count: int
    advisory_review_count: int
    trace_only_count: int
    taxable_value: Decimal
    gst_value: Decimal
    invoice_value: Decimal
    first_invoice_date: date | None
    last_invoice_date: date | None
    invoices: tuple[ReviewQueueItem, ...] = field(default_factory=tuple)

    @property
    def needs_attention(self) -> bool:
        return self.mandatory_review_count > 0


def _supplier_key(row: InvoiceRow) -> str:
    if row.gstin:
        return f"GSTIN::{row.gstin.upper()}"
    return f"SUPPLIER::{(row.supplier_name or 'UNKNOWN').strip().upper()}"


def _gst_total(row: InvoiceRow) -> Decimal:
    return row.igst + row.cgst + row.sgst + row.cess


def build_supplier_drilldowns(rows: Iterable[InvoiceRow]) -> list[SupplierDrilldown]:
    row_list = list(rows)
    items_by_row_id = {item.row_id: item for item in build_review_queue(row_list, include_non_blocking=True)}
    grouped: dict[str, dict[str, object]] = {}
    row_groups: dict[str, list[InvoiceRow]] = {}

    for row in row_list:
        key = _supplier_key(row)
        row_groups.setdefault(key, []).append(row)
        data = grouped.setdefault(
            key,
            {
                "supplier_key": key,
                "supplier_name": row.supplier_name or "UNKNOWN SUPPLIER",
                "gstin": row.gstin or "",
                "invoice_count": 0,
                "approved_invoice_count": 0,
                "mandatory_review_count": 0,
                "advisory_review_count": 0,
                "trace_only_count": 0,
                "taxable_value": Decimal("0.00"),
                "gst_value": Decimal("0.00"),
                "invoice_value": Decimal("0.00"),
                "first_invoice_date": None,
                "last_invoice_date": None,
            },
        )
        item = items_by_row_id[row.row_id]
        data["invoice_count"] = int(data["invoice_count"]) + 1
        data["approved_invoice_count"] = int(data["approved_invoice_count"]) + (1 if row.include_in_totals else 0)
        data["mandatory_review_count"] = int(data["mandatory_review_count"]) + (1 if item.bucket == "MANDATORY_REVIEW" else 0)
        data["advisory_review_count"] = int(data["advisory_review_count"]) + (1 if item.bucket == "ADVISORY_REVIEW" else 0)
        data["trace_only_count"] = int(data["trace_only_count"]) + (1 if item.bucket == "TRACE_ONLY" else 0)
        if row.include_in_totals:
            data["taxable_value"] = data["taxable_value"] + row.taxable_value  # type: ignore[operator]
            data["gst_value"] = data["gst_value"] + _gst_total(row)  # type: ignore[operator]
            data["invoice_value"] = data["invoice_value"] + row.invoice_value  # type: ignore[operator]
        if row.invoice_date:
            first = data["first_invoice_date"]
            last = data["last_invoice_date"]
            data["first_invoice_date"] = row.invoice_date if first is None or row.invoice_date < first else first
            data["last_invoice_date"] = row.invoice_date if last is None or row.invoice_date > last else last

    drilldowns: list[SupplierDrilldown] = []
    for key, data in grouped.items():
        invoices = tuple(
            sorted(
                (items_by_row_id[row.row_id] for row in row_groups[key]),
                key=lambda item: (0 if item.can_block_export else 1, -item.priority_score, item.invoice_no, item.row_id),
            )
        )
        drilldowns.append(SupplierDrilldown(**data, invoices=invoices))  # type: ignore[arg-type]

    return sorted(
        drilldowns,
        key=lambda supplier: (
            -supplier.mandatory_review_count,
            -supplier.invoice_value,
            supplier.supplier_name,
            supplier.gstin,
        ),
    )
