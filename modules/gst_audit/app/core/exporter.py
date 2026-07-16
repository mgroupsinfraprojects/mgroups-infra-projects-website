from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable

import pandas as pd

from app.core.models import AuditResult, InvoiceRow
from app.core.gstr_reconciliation import GstrReconciliationResult
from app.core.exception_workflow import exception_summary_dataframe, final_lock_checklist, review_queue_dataframe
from app.core.import_profiles import profiles_dataframe
from app.core.quality_gate import quality_gate_dataframe, quality_gate_score, quality_gate_status
from app.core.gst_compliance import compliance_dataframe
from app.version import APP_VERSION, RELEASE_NAME


EXCEL_FORMULA_PREFIXES = ("=", "+", "-", "@")


def sanitize_excel_value(value: Any) -> Any:
    """Neutralize spreadsheet formula injection in user-controlled text.

    Accounting imports are untrusted input. Excel treats strings beginning with
    =, +, -, or @ as formulas in many contexts, so exported text is prefixed
    with a single quote when it could execute as a formula. Numeric/date values
    are left unchanged.
    """
    if isinstance(value, str):
        text = value
        stripped = text.lstrip()
        if stripped.startswith(EXCEL_FORMULA_PREFIXES):
            return "'" + text
        if text.startswith(("\t", "\r", "\n")):
            return "'" + text
    return value


def sanitize_excel_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    safe_df = df.copy()
    object_columns = list(safe_df.select_dtypes(include=["object", "string"]).columns)
    for column in object_columns:
        safe_df[column] = safe_df[column].map(sanitize_excel_value)
    return safe_df


def _safe_excel_text(value: Any, limit: int | None = None) -> str:
    text = str(sanitize_excel_value("" if value is None else value))
    return text[:limit] if limit is not None else text

MONEY_COLUMNS = {
    "taxable_value", "igst", "cgst", "sgst", "cess", "invoice_value",
    "expected_invoice_value", "difference_amount", "invoice_value_total",
}


def rows_to_dataframe(rows: Iterable[InvoiceRow]) -> pd.DataFrame:
    return pd.DataFrame([row.to_dict() for row in rows])


STANDARD_ROW_COLUMNS = [
    "row_id", "source_file", "sheet_name", "excel_row_number",
    "supplier_name", "gstin", "invoice_no", "invoice_date", "period",
    "hsn_sac", "hsn_valid", "recipient_gstin", "self_invoice_flag",
    "taxable_value", "igst", "cgst", "sgst", "cess", "invoice_value",
    "expected_invoice_value", "difference_amount", "difference_percent",
    "mismatch_reason", "audit_status", "audit_severity", "audit_notes",
    "review_required", "review_decision", "include_in_totals",
    "invoice_series", "invoice_sequence_no", "invoice_gap_note", "anomaly_note",
    "duplicate_key", "reconstructed",
]

ROW_VIEW_COLUMNS = [
    "row_id", "source_file", "sheet_name", "excel_row_number",
    "supplier_name", "gstin", "invoice_no", "invoice_date",
    "taxable_value", "igst", "cgst", "sgst", "cess", "invoice_value",
    "difference_amount", "mismatch_reason", "audit_status", "audit_severity",
    "audit_notes", "review_required", "review_decision", "include_in_totals",
]


def _standard_rows_dataframe(df: pd.DataFrame, *, include_forensic_columns: bool = False) -> pd.DataFrame:
    """Return the default export row table.

    Raw snapshots and nested detected/final snapshots are useful for forensic debugging,
    but they are large object columns and made the full real-data workbook stall in v9.4.
    The standard client report keeps audit-critical fields and can optionally include
    the heavy forensic columns when explicitly requested.
    """
    if df.empty or include_forensic_columns:
        return df.copy()
    columns = [col for col in STANDARD_ROW_COLUMNS if col in df.columns]
    return df.loc[:, columns].copy()


def _row_view_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    columns = [col for col in ROW_VIEW_COLUMNS if col in df.columns]
    return df.loc[:, columns].copy()


def _compliance_export_dataframe(rows: Iterable[InvoiceRow]) -> pd.DataFrame:
    df = compliance_dataframe(rows)
    if df.empty:
        return df
    # IRN_NOT_FOUND is common in portal exports and should not by itself create
    # thousands of low-value compliance rows. Keep only rows with a material signal.
    keep = (
        df["itc_flag"].astype(str).ne("ITC_ELIGIBLE_REVIEWED")
        | df["rcm_flag"].astype(str).eq("POSSIBLE_RCM")
        | df["place_of_supply_flag"].astype(str).eq("POSSIBLE_TAX_TYPE_ERROR")
        | df["note_type"].astype(str).isin(["CREDIT_NOTE", "DEBIT_NOTE"])
    )
    return df.loc[keep].copy()


def export_verified_excel(
    result: AuditResult,
    output_path: str | Path,
    protection_password: str | None = None,
    include_charts: bool = True,
    gstr_reconciliation: GstrReconciliationResult | None = None,
    include_forensic_columns: bool = False,
) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    all_full_df = rows_to_dataframe(result.rows)
    all_df = _standard_rows_dataframe(all_full_df, include_forensic_columns=include_forensic_columns)
    row_view_df = _row_view_dataframe(all_df)
    approved_df = row_view_df[row_view_df["include_in_totals"]].copy() if not row_view_df.empty else pd.DataFrame()
    review_df = row_view_df[row_view_df["review_required"]].copy() if not row_view_df.empty else pd.DataFrame()
    skipped_df = row_view_df[row_view_df["audit_status"].astype(str).str.startswith("SKIPPED", na=False)].copy() if not row_view_df.empty else pd.DataFrame()
    _CLEAN_REASONS = {"", "BALANCED_OR_ROUNDING", "MINOR_ROUNDING_OR_DECIMAL_ISSUE", "CREDIT_NOTE_BALANCED", "CREDIT_NOTE_ZERO_RATED"}
    mismatch_df = row_view_df[~row_view_df["mismatch_reason"].isin(_CLEAN_REASONS)].copy() if not row_view_df.empty else pd.DataFrame()
    supplier_df = _totals_to_df(result.supplier_totals, "supplier_name")
    source_df = _totals_to_df(result.source_totals, "source_file")
    month_df = _totals_to_df(result.month_totals, "month")
    summary_df = pd.DataFrame([result.summary.to_dict()])
    cover_df = _cover_sheet_df(result)
    executive_df = _executive_summary_df(result)
    review_checklist_df = _review_checklist_df(result)
    exception_df = exception_summary_dataframe(result)
    review_queue_df = review_queue_dataframe(result.rows)
    final_lock_df = final_lock_checklist(result)
    quality_gate_df = quality_gate_dataframe(result)
    source_file_df = _source_file_list_df(result)
    sign_off_df = _sign_off_df(result)
    mismatch_reason_df = _mismatch_reason_df(mismatch_df)
    compliance_df = _compliance_export_dataframe(result.rows)
    security_df = pd.DataFrame([
        {"note": "Worksheet protection prevents accidental edits only. It is not encryption or secure access control."},
        {"note": "Use encrypted file storage or encrypted ZIP/PDF workflows for confidential client transmission."},
        {"note": "Dashboard totals count only rows where include_in_totals=True. Review rows remain visible but excluded until manually accepted."},
        {"note": "Default export omits raw/detected/final snapshot blobs for performance. Pass include_forensic_columns=True for a heavier forensic workbook."},
    ])

    sheets = {
        "Cover Sheet": cover_df,
        "Executive Summary": executive_df,
        "Audit Summary": summary_df,
        "Quality Gate": quality_gate_df,
        "Final Lock Checklist": final_lock_df,
        "Review Checklist": review_checklist_df,
        "Exception Summary": exception_df,
        "Review Queue": review_queue_df,
        "Approved Rows": approved_df,
        "Review Required": review_df,
        "Skipped Rows": skipped_df,
        "GST Mismatches": mismatch_df,
        "Mismatch Reasons": mismatch_reason_df,
        "GST Compliance Checks": compliance_df,
        "Supplier Summary": supplier_df,
        "Source Reconciliation": source_df,
        "Source File List": source_file_df,
        "Month Reconciliation": month_df,
        "All Classified Rows": all_df,
        "Import Profile Guide": profiles_dataframe(),
        "Sign Off": sign_off_df,
        "Security Notes": security_df,
    }
    if gstr_reconciliation is not None:
        sheets["GSTR Reco Summary"] = gstr_reconciliation.summary_dataframe()
        sheets["GSTR Reco Details"] = gstr_reconciliation.records_dataframe()

    with pd.ExcelWriter(
        output,
        engine="xlsxwriter",
        engine_kwargs={"options": {"strings_to_formulas": False, "strings_to_urls": False}},
    ) as writer:
        for sheet_name, df in sheets.items():
            safe_df = sanitize_excel_dataframe(df)
            safe_df.to_excel(writer, sheet_name=sheet_name, index=False, startrow=1)
            _format_sheet(writer, sheet_name, safe_df, protection_password=protection_password)
        if include_charts:
            _add_charts_sheet(writer, supplier_df, month_df, mismatch_reason_df)
    return output



def _cover_sheet_df(result: AuditResult) -> pd.DataFrame:
    s = result.summary
    rows = [
        ("Report", "GST Invoice Audit Package"),
        ("Version", f"v{APP_VERSION} — {RELEASE_NAME}"),
        ("Purpose", "Client-ready audit pack: row proof, exception queue, reconciliation and sign-off controls."),
        ("Final audit status", s.final_status),
        ("Files processed", s.files_processed),
        ("Raw rows read", s.raw_rows_read),
        ("Official invoice/detail rows", s.official_invoice_rows),
        ("Approved rows counted", s.final_approved_rows),
        ("Review rows", s.review_required_rows),
        ("Detected suppliers / GSTINs", f"{s.detected_unique_suppliers} / {s.detected_unique_gstins}"),
        ("Approved suppliers / GSTINs", f"{s.unique_suppliers} / {s.unique_gstins}"),
        ("Approved invoice value", float(s.approved_invoice_value)),
        ("Total GST counted", float(s.approved_total_gst)),
        ("Quality gate status", quality_gate_status(result)),
        ("Quality gate score", quality_gate_score(result)),
        ("Control rule", "No dashboard total is accepted unless row coverage and amount reconciliation can be traced to source file/sheet/Excel row."),
    ]
    return pd.DataFrame(rows, columns=["field", "value"])


def _source_file_list_df(result: AuditResult) -> pd.DataFrame:
    rows = []
    for source, total in result.source_totals.items():
        source_rows = [row for row in result.rows if row.source_file == source]
        rows.append({
            "source_file": source,
            "row_count": len(source_rows),
            "approved_rows": sum(1 for row in source_rows if row.include_in_totals),
            "review_rows": sum(1 for row in source_rows if row.review_required),
            "invoice_value_total": float(total),
            "sheets_seen": ", ".join(sorted({row.sheet_name for row in source_rows if row.sheet_name})),
        })
    return pd.DataFrame(rows)


def _sign_off_df(result: AuditResult) -> pd.DataFrame:
    rows = [
        ("Prepared by", ""),
        ("Reviewed by", ""),
        ("Client / company", ""),
        ("GSTIN", ""),
        ("Audit period", ""),
        ("Review date", ""),
        ("Reviewer notes", ""),
        ("Final decision", "Approved / Review Required / Rejected"),
        ("Declaration", "Reviewer confirms source files, exception rows, reconciliation controls and GSTR matching have been checked."),
    ]
    return pd.DataFrame(rows, columns=["sign_off_field", "value"])


def _executive_summary_df(result: AuditResult) -> pd.DataFrame:
    s = result.summary
    rows = [
        ("Final audit status", s.final_status),
        ("Files processed", s.files_processed),
        ("Sheets processed", s.sheets_processed),
        ("Raw rows read", s.raw_rows_read),
        ("Classified rows", s.classified_rows),
        ("Official invoice/detail rows", s.official_invoice_rows),
        ("Approved rows counted", s.final_approved_rows),
        ("Review-required rows", s.review_required_rows),
        ("Skipped/excluded rows", s.skipped_rows),
        ("Detected suppliers", s.detected_unique_suppliers),
        ("Detected GSTINs", s.detected_unique_gstins),
        ("Approved suppliers", s.unique_suppliers),
        ("Approved GSTINs", s.unique_gstins),
        ("Duplicate rows", s.duplicate_rows),
        ("Approved invoice value", float(s.approved_invoice_value)),
        ("Review invoice value", float(s.review_invoice_value)),
        ("Excluded invoice value", float(s.excluded_invoice_value)),
        ("Raw detected invoice total", float(s.raw_detected_invoice_value)),
        ("Row coverage status", s.row_coverage_status),
        ("Amount reconciliation status", s.amount_reconciliation_status),
        ("Control rule", "Approved + Review + Excluded must equal Raw detected invoice total."),
    ]
    return pd.DataFrame(rows, columns=["metric", "value"])


def _review_checklist_df(result: AuditResult) -> pd.DataFrame:
    checks = [
        ("Row coverage", result.summary.row_coverage_status, "Raw rows read must equal classified rows."),
        ("Amount reconciliation", result.summary.amount_reconciliation_status, "Approved + review + excluded totals must equal raw detected total."),
        ("GST mismatch review", result.summary.gst_mismatch_rows, "Check all GST mismatch rows before final submission."),
        ("High severity review", result.summary.high_severity_rows, "Resolve or document all high-severity rows."),
        ("Critical errors", result.summary.critical_rows, "Critical rows should be zero for final use."),
    ]
    return pd.DataFrame(checks, columns=["check", "result", "action_required"])


def _mismatch_reason_df(mismatch_df: pd.DataFrame) -> pd.DataFrame:
    if mismatch_df.empty or "mismatch_reason" not in mismatch_df.columns:
        return pd.DataFrame(columns=["mismatch_reason", "row_count", "difference_total", "invoice_value_total"])
    df = mismatch_df.copy()
    for col in ["difference_amount", "invoice_value"]:
        if col not in df.columns:
            df[col] = 0
    grouped = df.groupby("mismatch_reason", dropna=False).agg(
        row_count=("mismatch_reason", "size"),
        difference_total=("difference_amount", "sum"),
        invoice_value_total=("invoice_value", "sum"),
    ).reset_index().sort_values(["row_count", "invoice_value_total"], ascending=[False, False])
    return grouped

def _format_sheet(writer: pd.ExcelWriter, sheet_name: str, df: pd.DataFrame, protection_password: str | None = None) -> None:
    workbook = writer.book
    worksheet = writer.sheets[sheet_name]
    header_fmt = workbook.add_format({
        "bold": True,
        "font_color": "white",
        "bg_color": "#1F4E78",
        "border": 1,
        "align": "center",
        "valign": "vcenter",
    })
    title_fmt = workbook.add_format({"bold": True, "font_size": 14, "font_color": "#1F4E78"})
    money_fmt = workbook.add_format({"num_format": '₹#,##,##0.00;[Red]-₹#,##,##0.00', "border": 1})
    text_fmt = workbook.add_format({"border": 1, "valign": "top"})
    date_fmt = workbook.add_format({"num_format": "dd-mm-yyyy", "border": 1})

    if len(df.columns) > 1:
        worksheet.merge_range(0, 0, 0, len(df.columns) - 1, sheet_name, title_fmt)
    else:
        worksheet.write(0, 0, sheet_name, title_fmt)
    worksheet.freeze_panes(2, 0)
    worksheet.autofilter(1, 0, max(len(df) + 1, 1), max(len(df.columns) - 1, 0))
    if protection_password:
        # This protects sheets from accidental edits. It is not workbook-file encryption.
        worksheet.protect(protection_password, {"autofilter": True, "sort": True, "select_locked_cells": True, "select_unlocked_cells": True})

    for col_idx, col_name in enumerate(df.columns):
        worksheet.write(1, col_idx, col_name, header_fmt)
        preview = df[col_name].head(200).astype(object)
        preview = preview.where(pd.notna(preview), "")
        sample_values = [str(col_name)] + [str(v) for v in preview.tolist()]
        width = min(max(max((len(v) for v in sample_values), default=10) + 2, 12), 42)
        col_lower = str(col_name).lower()
        if col_lower in MONEY_COLUMNS or any(token in col_lower for token in ["value", "igst", "cgst", "sgst", "cess", "amount"]):
            worksheet.set_column(col_idx, col_idx, max(width, 15), money_fmt)
        elif "date" in col_lower:
            worksheet.set_column(col_idx, col_idx, max(width, 14), date_fmt)
        else:
            worksheet.set_column(col_idx, col_idx, width, text_fmt)


def _add_charts_sheet(writer: pd.ExcelWriter, supplier_df: pd.DataFrame, month_df: pd.DataFrame, mismatch_reason_df: pd.DataFrame | None = None) -> None:
    workbook = writer.book
    worksheet = workbook.add_worksheet("Charts")
    title_fmt = workbook.add_format({"bold": True, "font_size": 14, "font_color": "#1F4E78"})
    worksheet.write(0, 0, "GST Audit Charts", title_fmt)

    if not supplier_df.empty and {"supplier_name", "invoice_value_total"}.issubset(supplier_df.columns):
        top = supplier_df.head(10).copy()
        worksheet.write(2, 0, "Top Suppliers")
        for idx, row in top.iterrows():
            excel_row = 3 + int(idx)
            worksheet.write(excel_row, 0, _safe_excel_text(row["supplier_name"], 80))
            worksheet.write_number(excel_row, 1, float(row["invoice_value_total"]))
        chart = workbook.add_chart({"type": "bar"})
        chart.add_series({
            "name": "Top supplier invoice value",
            "categories": ["Charts", 3, 0, 3 + len(top) - 1, 0],
            "values": ["Charts", 3, 1, 3 + len(top) - 1, 1],
        })
        chart.set_title({"name": "Top Suppliers by Approved Invoice Value"})
        chart.set_x_axis({"name": "Invoice value"})
        chart.set_y_axis({"name": "Supplier"})
        worksheet.insert_chart(2, 3, chart, {"x_scale": 1.4, "y_scale": 1.2})

    if not month_df.empty and {"month", "invoice_value_total"}.issubset(month_df.columns):
        start = 18
        worksheet.write(start, 0, "Month-wise Trend")
        for idx, row in month_df.reset_index(drop=True).iterrows():
            excel_row = start + 1 + int(idx)
            worksheet.write(excel_row, 0, _safe_excel_text(row["month"]))
            worksheet.write_number(excel_row, 1, float(row["invoice_value_total"]))
        chart = workbook.add_chart({"type": "line"})
        chart.add_series({
            "name": "Month-wise approved invoice value",
            "categories": ["Charts", start + 1, 0, start + len(month_df), 0],
            "values": ["Charts", start + 1, 1, start + len(month_df), 1],
        })
        chart.set_title({"name": "Month-wise Approved Invoice Value"})
        chart.set_x_axis({"name": "Month"})
        chart.set_y_axis({"name": "Invoice value"})
        worksheet.insert_chart(start, 3, chart, {"x_scale": 1.4, "y_scale": 1.2})

    if mismatch_reason_df is not None and not mismatch_reason_df.empty and {"mismatch_reason", "row_count"}.issubset(mismatch_reason_df.columns):
        start = 36
        worksheet.write(start, 0, "Mismatch Reasons")
        top = mismatch_reason_df.head(10).reset_index(drop=True)
        for idx, row in top.iterrows():
            excel_row = start + 1 + int(idx)
            worksheet.write(excel_row, 0, _safe_excel_text(row["mismatch_reason"], 80))
            worksheet.write_number(excel_row, 1, float(row["row_count"]))
        chart = workbook.add_chart({"type": "column"})
        chart.add_series({
            "name": "Mismatch reason row count",
            "categories": ["Charts", start + 1, 0, start + len(top), 0],
            "values": ["Charts", start + 1, 1, start + len(top), 1],
        })
        chart.set_title({"name": "Top GST Mismatch Reasons"})
        worksheet.insert_chart(start, 3, chart, {"x_scale": 1.4, "y_scale": 1.2})

    worksheet.set_column(0, 0, 30)
    worksheet.set_column(1, 1, 18)


def _totals_to_df(totals: Dict[str, object], name: str) -> pd.DataFrame:
    return pd.DataFrame([{name: key, "invoice_value_total": float(value)} for key, value in totals.items()])
