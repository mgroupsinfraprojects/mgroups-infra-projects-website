from __future__ import annotations

import tempfile
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.audit_engine import InvoiceAuditEngine
from app.core.exporter import export_verified_excel
from scripts.create_sample_data import build_sample_data


def _check_result(label: str, input_paths: list[Path], *, min_rows: int, expect_review: bool = False) -> None:
    engine = InvoiceAuditEngine()
    result = engine.process_files([str(path) for path in input_paths])
    summary = result.summary

    print(f"\n[{label}]")
    print(f"files_processed={summary.files_processed}")
    print(f"raw_rows_read={summary.raw_rows_read}")
    print(f"classified_rows={summary.classified_rows}")
    print(f"approved_rows={summary.final_approved_rows}")
    print(f"review_rows={summary.review_required_rows}")
    print(f"duplicate_rows={summary.duplicate_rows}")
    print(f"row_coverage={summary.row_coverage_status}")
    print(f"amount_reconciliation={summary.amount_reconciliation_status}")
    print(f"final_status={summary.final_status}")

    if summary.raw_rows_read < min_rows:
        raise AssertionError(f"{label}: expected at least {min_rows} raw rows, got {summary.raw_rows_read}")
    if summary.row_coverage_status != "MATCHED":
        raise AssertionError(f"{label}: row coverage failed: {summary.row_coverage_status}")
    if summary.amount_reconciliation_status != "MATCHED":
        raise AssertionError(f"{label}: amount reconciliation failed: {summary.amount_reconciliation_status}")
    if expect_review and summary.review_required_rows == 0:
        raise AssertionError(f"{label}: expected review-required rows")

    output = Path(tempfile.gettempdir()) / f"gst_audit_{label.lower().replace(' ', '_')}.xlsx"
    export_verified_excel(result, output)
    if not output.exists() or output.stat().st_size <= 0:
        raise AssertionError(f"{label}: export was not created")
    print(f"export={output}")


def main() -> int:
    samples = build_sample_data(ROOT / "sample_data")
    balanced, review_cases, csv_cases = samples
    _check_result("balanced_excel", [balanced], min_rows=3)
    _check_result("review_duplicate_excel", [review_cases], min_rows=4, expect_review=True)
    _check_result("csv_import", [csv_cases], min_rows=2)
    _check_result("multi_file_batch", samples, min_rows=9, expect_review=True)
    print("\nSample dataset checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
