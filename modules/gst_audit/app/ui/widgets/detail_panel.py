from __future__ import annotations

from PySide6.QtWidgets import QFrame, QLabel, QTextEdit, QVBoxLayout
from app.core.models import InvoiceRow
from app.core.money import format_inr
from app.ui.widgets.status_chip import friendly_status


class RowDetailPanel(QFrame):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("DetailPanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)
        title = QLabel("Row Detail")
        title.setObjectName("SectionTitle")
        self.status = QLabel("Select a row")
        self.status.setObjectName("StatusChip")
        self.text = QTextEdit()
        self.text.setReadOnly(True)
        self.text.setPlaceholderText("Click an audit row to inspect raw, detected, and final values.")
        layout.addWidget(title)
        layout.addWidget(self.status)
        layout.addWidget(self.text, 1)

    def clear_detail(self) -> None:
        self.status.setText("Select a row")
        self.status.setProperty("variant", "neutral")
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)
        self.text.clear()

    def set_row(self, row: InvoiceRow) -> None:
        label, variant = friendly_status(row.audit_status)
        self.status.setText(label)
        self.status.setProperty("variant", variant)
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)
        self.text.setPlainText(
            "SOURCE\n"
            f"File: {row.source_file}\nSheet: {row.sheet_name}\nExcel Row: {row.excel_row_number}\n\n"
            "KEY FIELDS\n"
            f"Supplier: {row.supplier_name}\nGSTIN: {row.gstin}\nInvoice No: {row.invoice_no}\nDate: {row.invoice_date or ''}\nHSN/SAC: {row.hsn_sac}\n\n"
            "AMOUNTS\n"
            f"Taxable: {format_inr(row.taxable_value)}\nGST: {format_inr(row.igst + row.cgst + row.sgst + row.cess)}\n"
            f"Actual Invoice: {format_inr(row.invoice_value)}\nExpected Invoice: {format_inr(row.expected_invoice_value)}\n"
            f"Difference: {format_inr(row.difference_amount)}\n\n"
            "AUDIT\n"
            f"Severity: {row.audit_severity}\nReview Required: {row.review_required}\nIncluded in Totals: {row.include_in_totals}\n"
            f"Review Decision: {row.review_decision}\nMismatch Reason: {row.mismatch_reason}\nNotes: {row.audit_notes}\n\n"
            "RAW SNAPSHOT\n"
            f"{row.raw_snapshot}\n\nDETECTED SNAPSHOT\n{row.detected_snapshot}\n\nFINAL SNAPSHOT\n{row.final_snapshot}"
        )
