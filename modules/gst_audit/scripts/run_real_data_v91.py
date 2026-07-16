from __future__ import annotations

import csv
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.audit_engine import InvoiceAuditEngine
from app.core.config import AuditConfig


def money(v):
    return f"₹{v:,.2f}"


def summarize_result(result):
    s = result.summary
    return {
        "files_processed": s.files_processed,
        "sheets_processed": s.sheets_processed,
        "raw_rows_read": s.raw_rows_read,
        "final_approved_rows": s.final_approved_rows,
        "review_required_rows": s.review_required_rows,
        "duplicate_rows": s.duplicate_rows,
        "skipped_rows": s.skipped_rows,
        "approved_invoice_value": str(s.approved_invoice_value),
        "approved_taxable_value": str(s.approved_taxable_value),
        "approved_total_gst": str(s.approved_total_gst),
        "unique_suppliers": s.unique_suppliers,
        "unique_gstins": s.unique_gstins,
        "row_coverage_status": s.row_coverage_status,
        "amount_reconciliation_status": s.amount_reconciliation_status,
        "final_status": s.final_status,
    }


def main():
    data_root = Path(sys.argv[1])
    out_dir = Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)
    files = sorted([p for p in data_root.rglob("*") if p.is_file()])
    engine = InvoiceAuditEngine(AuditConfig())

    per_file = []
    errors = []
    start = time.time()
    for p in files:
        t0 = time.time()
        try:
            r = engine.process_files([p])
            status_counts = Counter(row.audit_status for row in r.rows)
            error_rows = [row for row in r.rows if row.audit_status.startswith("ERROR")]
            per_file.append({
                "file": p.name,
                "ext": p.suffix.lower(),
                "status": "ERROR" if error_rows else "OK",
                "error_status": error_rows[0].audit_status if error_rows else "",
                "error_note": error_rows[0].audit_notes if error_rows else "",
                "rows": r.summary.raw_rows_read,
                "approved": r.summary.final_approved_rows,
                "review": r.summary.review_required_rows,
                "duplicates": r.summary.duplicate_rows,
                "skipped": r.summary.skipped_rows,
                "approved_invoice_value": str(r.summary.approved_invoice_value),
                "row_coverage": r.summary.row_coverage_status,
                "amount_reconciliation": r.summary.amount_reconciliation_status,
                "final_status": r.summary.final_status,
                "seconds": f"{time.time()-t0:.3f}",
            })
            for er in error_rows:
                errors.append({"file": p.name, "ext": p.suffix.lower(), "status": er.audit_status, "note": er.audit_notes})
        except Exception as e:
            per_file.append({
                "file": p.name,
                "ext": p.suffix.lower(),
                "status": "CRASH",
                "error_status": type(e).__name__,
                "error_note": str(e),
                "rows": 0,
                "approved": 0,
                "review": 0,
                "duplicates": 0,
                "skipped": 0,
                "approved_invoice_value": "0",
                "row_coverage": "",
                "amount_reconciliation": "",
                "final_status": "",
                "seconds": f"{time.time()-t0:.3f}",
            })
            errors.append({"file": p.name, "ext": p.suffix.lower(), "status": type(e).__name__, "note": str(e)})

    all_result = engine.process_files(files)
    xlsx_files = [p for p in files if p.suffix.lower() == ".xlsx"]
    csv_files = [p for p in files if p.suffix.lower() == ".csv"]
    xlsx_result = engine.process_files(xlsx_files)
    csv_result = engine.process_files(csv_files)

    # write CSVs
    per_path = out_dir / "gst_v91_test_per_file_status.csv"
    err_path = out_dir / "gst_v91_test_error_files.csv"
    with per_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(per_file[0].keys()))
        w.writeheader(); w.writerows(per_file)
    with err_path.open("w", newline="", encoding="utf-8") as f:
        fields = ["file", "ext", "status", "note"]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(errors)

    ext_counts = Counter(p.suffix.lower() for p in files)
    err_counts = Counter(e["status"] for e in errors)
    md = []
    md.append("# GST Audit Pro v9.1 — real data test report\n")
    md.append(f"Total files tested: **{len(files)}**\n")
    md.append("\n## File type distribution\n")
    for ext, count in sorted(ext_counts.items()):
        md.append(f"- `{ext or '<none>'}`: {count}\n")
    md.append("\n## XLSX-only result\n")
    for k, v in summarize_result(xlsx_result).items():
        md.append(f"- {k}: **{v}**\n")
    md.append("\n## CSV-only result\n")
    for k, v in summarize_result(csv_result).items():
        md.append(f"- {k}: **{v}**\n")
    md.append("\n## Full mixed-folder result\n")
    for k, v in summarize_result(all_result).items():
        md.append(f"- {k}: **{v}**\n")
    md.append("\n## Isolated error rows\n")
    if not errors:
        md.append("- None\n")
    else:
        for status, count in err_counts.items():
            md.append(f"- {status}: **{count}**\n")
    md.append(f"\nRuntime seconds: **{time.time()-start:.2f}**\n")
    md.append(f"\nPer-file CSV: `{per_path.name}`\n")
    md.append(f"\nError CSV: `{err_path.name}`\n")
    report_path = out_dir / "gst_v91_real_data_test_report.md"
    report_path.write_text("".join(md), encoding="utf-8")
    print(report_path)
    print(per_path)
    print(err_path)
    print(summarize_result(all_result))
    print("errors", err_counts)

if __name__ == "__main__":
    main()
