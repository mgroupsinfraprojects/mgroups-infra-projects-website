from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.core.audit_engine import InvoiceAuditEngine
from app.core.exporter import export_verified_excel
from app.version import APP_VERSION

ROOT = Path(__file__).resolve().parents[1]


def test_v993_version_and_single_launcher_contract() -> None:
    assert APP_VERSION == "11.13.0"
    assert (ROOT / "START_GST_AUDIT_PRO.bat").exists()
    assert not (ROOT / "run_app.bat").exists()
    text = (ROOT / "START_GST_AUDIT_PRO.bat").read_text(encoding="utf-8")
    assert "One Click Launcher" in text
    assert r"scripts\preflight_windows.py" in text
    assert "main.py" in text


def test_export_contains_quality_gate_sheet(tmp_path: Path) -> None:
    result = InvoiceAuditEngine().process_files([str(ROOT / "sample_data" / "01_balanced_invoices.xlsx")])
    output = export_verified_excel(result, tmp_path / "quality_gate.xlsx")
    workbook = pd.ExcelFile(output)
    assert "Quality Gate" in workbook.sheet_names
    df = pd.read_excel(output, sheet_name="Quality Gate", header=1)
    assert {"gate", "status", "evidence", "required_action"}.issubset(df.columns)
    assert "Row coverage" in set(df["gate"])
    assert "Amount reconciliation" in set(df["gate"])
    assert "Final lock readiness" in set(df["gate"])
