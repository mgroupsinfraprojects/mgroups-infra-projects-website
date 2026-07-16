from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SAMPLE_DIR = ROOT / "sample_data"


def _valid_gstin(prefix14: str) -> str:
    from app.core.gstin import calculate_gstin_checksum

    return prefix14 + calculate_gstin_checksum(prefix14)


HEADERS = [
    "GSTIN of Supplier",
    "Trade/Legal Name",
    "Invoice Number",
    "Invoice date",
    "Invoice Value",
    "Taxable Value",
    "Integrated Tax",
    "Central Tax",
    "State/UT Tax",
    "Cess",
    "HSN/SAC",
]


def _write_excel(path: Path, rows: list[list[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([HEADERS, *rows]).to_excel(path, index=False, header=False)


def _write_csv(path: Path, rows: list[list[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([HEADERS, *rows]).to_csv(path, index=False, header=False)


def build_sample_data(sample_dir: Path = SAMPLE_DIR) -> list[Path]:
    """Create deterministic audit input files for smoke/regression checks."""
    sample_dir.mkdir(parents=True, exist_ok=True)

    g1 = _valid_gstin("33ABCDE1234F1Z")
    g2 = _valid_gstin("33AAAPL1234C1Z")
    g3 = _valid_gstin("29ABCDE1234F1Z")

    balanced_rows = [
        [g1, "AADD ENTERPRISES", "BAL-001", "01/01/2026", 11800, 10000, 0, 900, 900, 0, "998314"],
        [g2, "LYCEUM TRADERS", "BAL-002", "02/01/2026", 23600, 20000, 0, 1800, 1800, 0, "847130"],
        [g3, "KARNATAKA SUPPLY CO", "BAL-003", "03/01/2026", 5900, 5000, 900, 0, 0, 0, "852351"],
    ]
    review_rows = [
        [g1, "AADD ENTERPRISES", "REV-001", "04/01/2026", 11700, 10000, 0, 900, 900, 0, "998314"],  # mismatch by -100
        [g1, "AADD ENTERPRISES", "DUP-001", "05/01/2026", 11800, 10000, 0, 900, 900, 0, "998314"],
        [g1, "AADD ENTERPRISES", "DUP-001", "05/01/2026", 11800, 10000, 0, 900, 900, 0, "998314"],  # duplicate
        ["33INVALIDGSTIN", "BAD GSTIN SUPPLIER", "BAD-001", "06/01/2026", 11800, 10000, 0, 900, 900, 0, "998314"],
    ]
    csv_rows = [
        [g2, "LYCEUM TRADERS", "CSV-001", "07/01/2026", 17700, 15000, 0, 1350, 1350, 0, "998599"],
        [g3, "KARNATAKA SUPPLY CO", "CSV-002", "08/01/2026", 12000, 10000, 2000, 0, 0, 0, "852351"],
    ]

    outputs = [
        sample_dir / "01_balanced_invoices.xlsx",
        sample_dir / "02_review_and_duplicate_cases.xlsx",
        sample_dir / "03_csv_import_cases.csv",
    ]
    _write_excel(outputs[0], balanced_rows)
    _write_excel(outputs[1], review_rows)
    _write_csv(outputs[2], csv_rows)
    return outputs


if __name__ == "__main__":
    for file_path in build_sample_data():
        print(file_path)
