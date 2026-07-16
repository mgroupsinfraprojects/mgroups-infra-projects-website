from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.audit_engine import InvoiceAuditEngine  # noqa: E402
from app.core.gstin import calculate_gstin_checksum  # noqa: E402
from app.core.exporter import export_verified_excel  # noqa: E402


def create_sample_excel(path: Path) -> None:
    gstin_prefix = "33ABCDE1234F1Z"
    gstin = gstin_prefix + calculate_gstin_checksum(gstin_prefix)
    rows = [
        ["GSTIN of Supplier", "Trade/Legal Name", "Invoice Number", "Invoice date", "Invoice Value", "Taxable Value", "Integrated Tax", "Central Tax", "State/UT Tax", "Cess"],
        [gstin, "AADD ENTERPRISES", "INV-001", "01/01/2026", 11800, 10000, 0, 900, 900, 0],
        [gstin, "AADD ENTERPRISES", "INV-002", "02/01/2026", 12000, 10000, 0, 900, 900, 0],
    ]
    pd.DataFrame(rows).to_excel(path, index=False, header=False)


def run(paths: list[str]) -> int:
    engine = InvoiceAuditEngine()
    result = engine.process_files(paths)
    s = result.summary
    print("GST Invoice Audit processor smoke test")
    print(f"Files processed: {s.files_processed}")
    print(f"Sheets processed: {s.sheets_processed}")
    print(f"Raw rows read: {s.raw_rows_read}")
    print(f"Classified rows: {s.classified_rows}")
    print(f"Final approved rows: {s.final_approved_rows}")
    print(f"Review rows: {s.review_required_rows}")
    print(f"Row coverage: {s.row_coverage_status}")
    print(f"Amount reconciliation: {s.amount_reconciliation_status}")
    print(f"Final status: {s.final_status}")
    if s.row_coverage_status != "MATCHED" or s.amount_reconciliation_status != "MATCHED":
        print("FAILED: reconciliation did not match")
        return 2
    output = Path(tempfile.gettempdir()) / "gst_audit_smoke_export.xlsx"
    export_verified_excel(result, output)
    if not output.exists() or output.stat().st_size == 0:
        print("FAILED: verified Excel export was not created")
        return 3
    print(f"Export check: {output}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="*", help="Excel files to test")
    parser.add_argument("--self-check", action="store_true", help="Generate a temporary sample Excel and test it")
    args = parser.parse_args()
    if args.self_check:
        with tempfile.TemporaryDirectory() as tmp:
            sample = Path(tmp) / "sample_gst.xlsx"
            create_sample_excel(sample)
            return run([str(sample)])
    if not args.files:
        print("Provide Excel files or use --self-check")
        return 1
    return run(args.files)


if __name__ == "__main__":
    raise SystemExit(main())
