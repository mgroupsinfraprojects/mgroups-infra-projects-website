from __future__ import annotations

from decimal import Decimal
from time import perf_counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.models import InvoiceRow
from app.core.review_queue_engine import build_review_queue


def main() -> int:
    rows = [InvoiceRow(row_id=i, source_file="bench.xlsx", sheet_name="S", excel_row_number=i, raw_snapshot=[], supplier_name="S", gstin="29ABCDE1234F1Z5", invoice_no=f"INV{i}", taxable_value=Decimal("100.00"), invoice_value=Decimal("118.00"), expected_invoice_value=Decimal("118.00"), include_in_totals=True) for i in range(50000)]
    start = perf_counter(); queue = build_review_queue(rows); seconds = perf_counter() - start
    print({"rows": len(rows), "queue_items": len(queue), "seconds": round(seconds, 3)})
    return 0 if len(queue) == 50000 else 1


if __name__ == "__main__":
    raise SystemExit(main())
