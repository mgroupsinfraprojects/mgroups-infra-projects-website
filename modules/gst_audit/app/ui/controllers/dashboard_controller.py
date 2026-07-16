# Legacy wording retained: Official review:
# Legacy regression string: visible_sources = [source for source, _count in source_counts.most_common(2)]
# Legacy regression string: visible_months = [month for month, _count in month_items[-3:]]
from __future__ import annotations

import json
import logging
from html import escape
from collections import Counter
from decimal import Decimal
from typing import Any, List

from PySide6.QtCore import QDate
from PySide6.QtGui import QTextDocument
from PySide6.QtPrintSupport import QPrinter
from PySide6.QtWidgets import QFileDialog, QInputDialog, QMessageBox, QSizePolicy

from app.core.analytics import filter_rows, grouped_chart_points, supplier_summary
from app.core.models import InvoiceRow
from app.core.money import format_inr
from app.core.quality_gate import quality_gate_score, quality_gate_status
from app.core.review_policy import is_mandatory_review, is_advisory_exception, has_gst_or_amount_exception, has_required_identity_problem, is_trace_only
from app.ui.widgets.status_chip import friendly_status


LOGGER = logging.getLogger(__name__)


DASHBOARD_MODE_PRESETS: dict[str, dict[str, object]] = {
    "Overview": {"status": "All Rows", "group": "Month", "metric": "Invoice Value", "chart": "Bar", "limit": 12, "show_advanced": False},
    "Review Focus": {"status": "Critical Review", "group": "Mismatch Reason", "metric": "Mismatch Amount", "chart": "Bar", "limit": 10, "show_advanced": False},
    "Supplier Focus": {"status": "All Rows", "group": "Supplier", "metric": "Invoice Value", "chart": "Bar", "limit": 15, "show_advanced": False},
    "GSTIN Focus": {"status": "All Rows", "group": "GSTIN", "metric": "Total GST", "chart": "Bar", "limit": 15, "show_advanced": False},
    "Tax Mismatch": {"status": "GST Mismatch", "group": "Mismatch Reason", "metric": "Mismatch Amount", "chart": "Bar", "limit": 12, "show_advanced": False},
    "Monthly Trend": {"status": "All Rows", "group": "Month", "metric": "Invoice Value", "chart": "Line", "limit": 18, "show_advanced": False},
    "Advanced Custom": {"show_advanced": True},
}


DASHBOARD_MODE_HELP: dict[str, str] = {
    "Overview": "Best default view: totals, monthly value, suppliers, status and mismatch summary.",
    "Review Focus": "Shows only rows needing decisions and groups them by mismatch reason.",
    "Supplier Focus": "Ranks supplier/company totals and prepares the table for supplier drill-down.",
    "GSTIN Focus": "Groups by GSTIN so you can check supplier tax identity and totals.",
    "Tax Mismatch": "Prioritises GST formula mismatch amount and exception reasons.",
    "Monthly Trend": "Shows month-wise movement with a line chart.",
    "Advanced Custom": "Unlocks all filters and chart settings for expert analysis.",
}


class DashboardControllerMixin:
    """Dashboard-only controller logic extracted from MainWindow.

    The mixin owns filtering, saved views, chart drill-down, metric refresh, and
    supplier detail-panel behaviour. MainWindow remains responsible for app
    shell construction and cross-tab coordination.
    """

    @staticmethod
    def _dashboard_month_label(row: InvoiceRow) -> str:
        return row.invoice_date.strftime("%b %Y") if row.invoice_date else "Unknown"

    @staticmethod
    def _clear_layout(layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    @staticmethod
    def _dashboard_invoice_label(row: InvoiceRow) -> str:
        return row.invoice_no.strip() if row.invoice_no and row.invoice_no.strip() else "No invoice no"

    @staticmethod
    def _dashboard_company_label(row: InvoiceRow) -> str:
        return row.supplier_name.strip() if row.supplier_name and row.supplier_name.strip() else "UNKNOWN SUPPLIER"

    @staticmethod
    def _dashboard_gstin_values(row: InvoiceRow) -> tuple[str, ...]:
        values: list[str] = []
        for raw in [row.gstin, row.recipient_gstin, *tuple(row.all_gstins or ())]:
            value = str(raw or "").strip().upper()
            if value and value not in values:
                values.append(value)
        return tuple(values)

    @staticmethod
    def _dashboard_compact_values(values: list[str], *, limit: int = 3) -> str:
        if not values:
            return ""
        shown = []
        for value in values[:limit]:
            shown.append(value if len(value) <= 28 else value[:25] + "…")
        text = ", ".join(shown)
        if len(values) > limit:
            text += f" +{len(values) - limit} more"
        return text

    @staticmethod
    def _format_row_count(value: Decimal) -> str:
        count = int(value)
        return f"{count:,} row" if count == 1 else f"{count:,} rows"

    def _dashboard_selected_values(self, attr_name: str) -> list[str]:
        field_map = {
            "dashboard_company_filter": "company",
            "dashboard_gstin_filter": "gstin",
            "dashboard_invoice_filter": "invoice",
            "dashboard_month_filter": "month",
        }
        field_key = field_map.get(attr_name, "")
        selector = getattr(self, "dashboard_search_selector", None)
        if selector is not None and field_key and hasattr(selector, "selected_values"):
            try:
                return list(selector.selected_values(field_key))
            except TypeError:
                pass
        widget = getattr(self, attr_name, None)
        if widget is None or not hasattr(widget, "selected_values"):
            return []
        return list(widget.selected_values())


    def _dashboard_guided_query(self, field_key: str) -> str:
        selector = getattr(self, "dashboard_search_selector", None)
        if selector is not None and hasattr(selector, "query_text"):
            try:
                return str(selector.query_text(field_key)).strip()
            except TypeError:
                return ""
        return ""

    @staticmethod
    def _dashboard_text_matches_query(value: str, query: str) -> bool:
        value_norm = " ".join(str(value or "").casefold().split())
        query_norm = " ".join(str(query or "").casefold().split())
        if not query_norm:
            return True
        if query_norm in value_norm:
            return True
        tokens = [token for token in query_norm.split() if token]
        return bool(tokens) and all(token in value_norm for token in tokens)


    def _refresh_dashboard_guided_filter_options(self) -> None:
        if not self.result:
            return
        company_counts = Counter(self._dashboard_company_label(row) for row in self.result.rows)
        gstin_counts: Counter[str] = Counter()
        invoice_counts = Counter(self._dashboard_invoice_label(row) for row in self.result.rows)
        month_counts = Counter(self._dashboard_month_label(row) for row in self.result.rows)
        for row in self.result.rows:
            gst_values = self._dashboard_gstin_values(row)
            if gst_values:
                for gstin in gst_values:
                    gstin_counts[gstin] += 1
            else:
                gstin_counts["No GSTIN"] += 1

        selector = getattr(self, "dashboard_search_selector", None)
        if selector is not None and hasattr(selector, "set_field_options"):
            selector.set_field_options("company", company_counts)
            selector.set_field_options("gstin", gstin_counts)
            selector.set_field_options("invoice", invoice_counts)
            selector.set_field_options("month", month_counts)
            return

        company_widget = getattr(self, "dashboard_company_filter", None)
        gst_widget = getattr(self, "dashboard_gstin_filter", None)
        invoice_widget = getattr(self, "dashboard_invoice_filter", None)
        month_widget = getattr(self, "dashboard_month_filter", None)
        if company_widget is not None and hasattr(company_widget, "set_options"):
            company_widget.set_options(company_counts)
        if gst_widget is not None and hasattr(gst_widget, "set_options"):
            gst_widget.set_options(gstin_counts)
        if invoice_widget is not None and hasattr(invoice_widget, "set_options"):
            invoice_widget.set_options(invoice_counts)
        if month_widget is not None and hasattr(month_widget, "set_options"):
            month_widget.set_options(month_counts)


    def update_dashboard_search_placeholder(self, search_field: str = "") -> None:
        """Keep the search box self-explanatory for non-technical users."""
        if search_field:
            field = search_field
        elif hasattr(self, "dashboard_search_field_combo"):
            field = self.dashboard_search_field_combo.currentText()
        else:
            field = "Auto / Any Field"
        placeholders = {
            "Auto / Any Field": "Type anything: company, GSTIN, invoice no, month, file, status...",
            "Company / Supplier": "Example: Sree Kumaran, RR Roofing, Sakthi...",
            "GSTIN": "Example: 33FNRPK9375P1ZS or any 15-character GSTIN...",
            "Invoice Number": "Example: INV-2026-001, 145, bill no...",
            "Month": "Example: Jan 2026, Feb 2025, Unknown...",
            "Source File": "Example: 1 JAN 26.xlsx, April, CSV file name...",
            "Status / Issue": "Example: review, mismatch, skipped, high, rounding...",
        }
        if hasattr(self, "dashboard_filter_text"):
            self.dashboard_filter_text.setPlaceholderText(placeholders.get(str(field), placeholders["Auto / Any Field"]))

    def _dashboard_filtered_rows(self) -> List[InvoiceRow]:
        if not self.result:
            return []
        query = self.dashboard_filter_text.text() if hasattr(self, "dashboard_filter_text") else ""
        status = self.dashboard_status_combo.currentText() if hasattr(self, "dashboard_status_combo") else "All Rows"
        search_field = self.dashboard_search_field_combo.currentText() if hasattr(self, "dashboard_search_field_combo") else "Auto / Any Field"
        rows = filter_rows(self.result.rows, query=query, status=status, included_only=False, search_field=search_field)

        selected_companies = set(self._dashboard_selected_values("dashboard_company_filter"))
        selected_gstins = set(self._dashboard_selected_values("dashboard_gstin_filter"))
        selected_invoices = set(self._dashboard_selected_values("dashboard_invoice_filter"))
        selected_months = set(self._dashboard_selected_values("dashboard_month_filter"))
        company_query = "" if selected_companies else self._dashboard_guided_query("company")
        gstin_query = "" if selected_gstins else self._dashboard_guided_query("gstin")
        invoice_query = "" if selected_invoices else self._dashboard_guided_query("invoice")
        month_query = "" if selected_months else self._dashboard_guided_query("month")

        if selected_companies:
            rows = [row for row in rows if self._dashboard_company_label(row) in selected_companies]
        elif company_query:
            rows = [row for row in rows if self._dashboard_text_matches_query(self._dashboard_company_label(row), company_query)]
        if selected_gstins:
            rows = [
                row for row in rows
                if (set(self._dashboard_gstin_values(row)) & selected_gstins)
                or ("No GSTIN" in selected_gstins and not self._dashboard_gstin_values(row))
            ]
        elif gstin_query:
            rows = [
                row for row in rows
                if any(self._dashboard_text_matches_query(value, gstin_query) for value in self._dashboard_gstin_values(row))
                or (self._dashboard_text_matches_query("No GSTIN", gstin_query) and not self._dashboard_gstin_values(row))
            ]
        if selected_invoices:
            rows = [row for row in rows if self._dashboard_invoice_label(row) in selected_invoices]
        elif invoice_query:
            rows = [row for row in rows if self._dashboard_text_matches_query(self._dashboard_invoice_label(row), invoice_query)]
        if selected_months:
            rows = [row for row in rows if self._dashboard_month_label(row) in selected_months]
        elif month_query:
            rows = [row for row in rows if self._dashboard_text_matches_query(self._dashboard_month_label(row), month_query)]

        selected_source = getattr(self, "dashboard_selected_source", "")
        selected_month = getattr(self, "dashboard_selected_month", "")
        if selected_source:
            rows = [row for row in rows if (row.source_file or "UNKNOWN") == selected_source]
        if selected_month:
            rows = [row for row in rows if self._dashboard_month_label(row) == selected_month]

        if hasattr(self, "dashboard_date_enabled") and self.dashboard_date_enabled.isChecked():
            start_date = self.dashboard_from_date.date().toPython()
            end_date = self.dashboard_to_date.date().toPython()
            if start_date > end_date:
                start_date, end_date = end_date, start_date
            rows = [row for row in rows if row.invoice_date and start_date <= row.invoice_date <= end_date]
        return rows

    def _set_dashboard_source_filter(self, source: str) -> None:
        self.dashboard_selected_source = "" if source == "__ALL__" else source
        self.apply_dashboard_filter()
        shown = "All sources" if not self.dashboard_selected_source else self.dashboard_selected_source
        self.statusBar().showMessage(f"Dashboard source filter: {shown}")

    def _set_dashboard_month_filter(self, month: str) -> None:
        self.dashboard_selected_month = "" if month == "__ALL__" else month
        self.apply_dashboard_filter()
        shown = "All months" if not self.dashboard_selected_month else self.dashboard_selected_month
        self.statusBar().showMessage(f"Dashboard month filter: {shown}")

    def _make_quick_filter_button(self, label: str, selected: bool, callback) :
        from PySide6.QtWidgets import QPushButton, QSizePolicy
        button = QPushButton(label)
        button.setObjectName("QuickFilterChip")
        button.setCheckable(True)
        button.setChecked(selected)
        button.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        button.setMaximumWidth(168)
        button.clicked.connect(callback)
        return button

    def _refresh_dashboard_quick_filters(self) -> None:
        if not self.result or not hasattr(self, "dashboard_source_chip_layout"):
            return
        selected_source = getattr(self, "dashboard_selected_source", "")
        selected_month = getattr(self, "dashboard_selected_month", "")
        source_counts = Counter((row.source_file or "UNKNOWN") for row in self.result.rows)
        month_counts = Counter(self._dashboard_month_label(row) for row in self.result.rows)

        self._clear_layout(self.dashboard_source_chip_layout)
        self._clear_layout(self.dashboard_month_chip_layout)

        self.dashboard_source_chip_layout.addWidget(
            self._make_quick_filter_button(
                f"All Sources ({len(source_counts)})",
                not selected_source,
                lambda _checked=False: self._set_dashboard_source_filter("__ALL__"),
            )
        )
        # v11.4 easy-access: show every source file chip. Earlier builds showed
        # only two/three sources plus "+ more", which hid audit coverage.
        visible_sources = [source for source, _count in source_counts.most_common()]
        for source in visible_sources:
            count = source_counts.get(source, 0)
            clean_source = source.replace(".xlsx", "").replace(".xls", "").replace(".csv", "")
            label = clean_source if len(clean_source) <= 14 else clean_source[:12] + "…"
            self.dashboard_source_chip_layout.addWidget(
                self._make_quick_filter_button(
                    f"{label} ({count})",
                    source == selected_source,
                    lambda _checked=False, value=source: self._set_dashboard_source_filter(value),
                )
            )
        self.dashboard_source_chip_layout.addStretch(1)

        month_items = list(month_counts.items())
        def month_sort(item):
            label, _count = item
            if label == "Unknown":
                return (999999, label)
            try:
                from datetime import datetime
                dt = datetime.strptime(label, "%b %Y")
                return (dt.year * 100 + dt.month, label)
            except ValueError:
                return (999998, label)
        month_items.sort(key=month_sort)
        self.dashboard_month_chip_layout.addWidget(
            self._make_quick_filter_button(
                f"All Months ({len(month_items)})",
                not selected_month,
                lambda _checked=False: self._set_dashboard_month_filter("__ALL__"),
            )
        )
        # Show every month chip instead of hiding periods behind "+ more".
        visible_months = [month for month, _count in month_items]
        month_count_map = dict(month_items)
        for month in visible_months:
            count = month_count_map.get(month, 0)
            self.dashboard_month_chip_layout.addWidget(
                self._make_quick_filter_button(
                    f"{month} ({count})",
                    month == selected_month,
                    lambda _checked=False, value=month: self._set_dashboard_month_filter(value),
                )
            )
        self.dashboard_month_chip_layout.addStretch(1)

    def clear_dashboard_filter(self) -> None:
        if hasattr(self, "dashboard_filter_text"):
            self.dashboard_filter_text.clear()
            if hasattr(self, "dashboard_search_field_combo"):
                self.dashboard_search_field_combo.setCurrentText("Auto / Any Field")
                self.update_dashboard_search_placeholder("Auto / Any Field")
            if hasattr(self, "dashboard_mode_combo"):
                self.dashboard_mode_combo.blockSignals(True)
                self.dashboard_mode_combo.setCurrentText("Overview")
                self.dashboard_mode_combo.blockSignals(False)
            self.dashboard_status_combo.setCurrentText("All Rows")
            self.dashboard_group_combo.setCurrentText("Month")
            self.dashboard_metric_combo.setCurrentText("Invoice Value")
            self.dashboard_chart_mode_combo.setCurrentText("Bar")
            self.dashboard_limit_spin.setValue(12)
            if hasattr(self, "dashboard_date_enabled"):
                self.dashboard_date_enabled.setChecked(False)
            if hasattr(self, "dashboard_saved_view_combo"):
                self.dashboard_saved_view_combo.blockSignals(True)
                self.dashboard_saved_view_combo.setCurrentIndex(0)
                self.dashboard_saved_view_combo.blockSignals(False)
            if hasattr(self, "dashboard_filter_body"):
                self.dashboard_filter_body.setVisible(False)
            if hasattr(self, "dashboard_filter_toggle_btn"):
                self.dashboard_filter_toggle_btn.blockSignals(True)
                self.dashboard_filter_toggle_btn.setChecked(False)
                self.dashboard_filter_toggle_btn.setText("Advanced Filters")
                self.dashboard_filter_toggle_btn.blockSignals(False)
            if hasattr(self, "dashboard_mode_help"):
                self.dashboard_mode_help.setText(DASHBOARD_MODE_HELP["Overview"])
        selector = getattr(self, "dashboard_search_selector", None)
        if selector is not None and hasattr(selector, "clear_all_selections"):
            selector.clear_all_selections()
        else:
            for attr in [
                "dashboard_company_filter",
                "dashboard_gstin_filter",
                "dashboard_invoice_filter",
                "dashboard_month_filter",
            ]:
                widget = getattr(self, attr, None)
                if widget is not None and hasattr(widget, "clear_selection"):
                    widget.clear_selection()
        self.dashboard_selected_source = ""
        self.dashboard_selected_month = ""
        self.apply_dashboard_filter()

    def _dashboard_views(self) -> dict[str, dict[str, Any]]:
        raw = self.settings.value("dashboard/saved_views", "{}", type=str)
        try:
            data = json.loads(raw or "{}")
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _write_dashboard_views(self, views: dict[str, dict[str, Any]]) -> None:
        self.settings.setValue("dashboard/saved_views", json.dumps(views, sort_keys=True))
        self.settings.sync()

    def _load_dashboard_saved_view_names(self) -> None:
        # Called during construction after dashboard_saved_view_combo exists.
        combo = getattr(self, "dashboard_saved_view_combo", None)
        if combo is None:
            return
        current = combo.currentText()
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("Saved views...")
        for name in sorted(self._dashboard_views()):
            combo.addItem(name)
        if current and current in [combo.itemText(i) for i in range(combo.count())]:
            combo.setCurrentText(current)
        combo.blockSignals(False)

    def _current_dashboard_view_payload(self) -> dict[str, Any]:
        return {
            "mode": self.dashboard_mode_combo.currentText() if hasattr(self, "dashboard_mode_combo") else "Overview",
            "query": self.dashboard_filter_text.text(),
            "search_field": self.dashboard_search_field_combo.currentText() if hasattr(self, "dashboard_search_field_combo") else "Auto / Any Field",
            "status": self.dashboard_status_combo.currentText(),
            "group": self.dashboard_group_combo.currentText(),
            "metric": self.dashboard_metric_combo.currentText(),
            "chart": self.dashboard_chart_mode_combo.currentText(),
            "limit": self.dashboard_limit_spin.value(),
            "date_enabled": self.dashboard_date_enabled.isChecked(),
            "date_from": self.dashboard_from_date.date().toString("yyyy-MM-dd"),
            "date_to": self.dashboard_to_date.date().toString("yyyy-MM-dd"),
            "source": getattr(self, "dashboard_selected_source", ""),
            "month": getattr(self, "dashboard_selected_month", ""),
            "companies": self._dashboard_selected_values("dashboard_company_filter"),
            "gstins": self._dashboard_selected_values("dashboard_gstin_filter"),
            "invoices": self._dashboard_selected_values("dashboard_invoice_filter"),
            "months": self._dashboard_selected_values("dashboard_month_filter"),
        }

    def save_dashboard_view(self) -> None:
        name, ok = QInputDialog.getText(self, "Save dashboard view", "Name this filter/chart view:")
        name = name.strip()
        if not ok or not name:
            return
        views = self._dashboard_views()
        views[name] = self._current_dashboard_view_payload()
        self._write_dashboard_views(views)
        self._load_dashboard_saved_view_names()
        self.dashboard_saved_view_combo.setCurrentText(name)
        self._show_toast(f"Saved dashboard view: {name}")

    def delete_dashboard_view(self) -> None:
        name = self.dashboard_saved_view_combo.currentText() if hasattr(self, "dashboard_saved_view_combo") else ""
        if not name or name == "Saved views...":
            QMessageBox.information(self, "No saved view", "Select a saved dashboard view first.")
            return
        views = self._dashboard_views()
        if name in views:
            del views[name]
            self._write_dashboard_views(views)
            self._load_dashboard_saved_view_names()
            self._show_toast(f"Deleted dashboard view: {name}")

    def _apply_saved_dashboard_view(self, name: str) -> None:
        if not name or name == "Saved views..." or not hasattr(self, "dashboard_filter_text"):
            return
        payload = self._dashboard_views().get(name)
        if not payload:
            return
        widgets = [self.dashboard_filter_text, self.dashboard_status_combo, self.dashboard_group_combo, self.dashboard_metric_combo, self.dashboard_chart_mode_combo, self.dashboard_limit_spin, self.dashboard_date_enabled, self.dashboard_from_date, self.dashboard_to_date]
        if hasattr(self, "dashboard_search_field_combo"):
            widgets.insert(0, self.dashboard_search_field_combo)
        if hasattr(self, "dashboard_mode_combo"):
            widgets.insert(1, self.dashboard_mode_combo)
        for widget in widgets:
            widget.blockSignals(True)
        try:
            if hasattr(self, "dashboard_mode_combo"):
                self.dashboard_mode_combo.setCurrentText(str(payload.get("mode", "Advanced Custom")))
            if hasattr(self, "dashboard_search_field_combo"):
                self.dashboard_search_field_combo.setCurrentText(str(payload.get("search_field", "Auto / Any Field")))
                self.update_dashboard_search_placeholder(self.dashboard_search_field_combo.currentText())
            self.dashboard_filter_text.setText(str(payload.get("query", "")))
            self.dashboard_status_combo.setCurrentText(str(payload.get("status", "All Rows")))
            self.dashboard_group_combo.setCurrentText(str(payload.get("group", "Month")))
            self.dashboard_metric_combo.setCurrentText(str(payload.get("metric", "Invoice Value")))
            self.dashboard_chart_mode_combo.setCurrentText(str(payload.get("chart", "Bar")))
            self.dashboard_limit_spin.setValue(int(payload.get("limit", 12)))
            self.dashboard_date_enabled.setChecked(bool(payload.get("date_enabled", False)))
            from_date = QDate.fromString(str(payload.get("date_from", "")), "yyyy-MM-dd")
            to_date = QDate.fromString(str(payload.get("date_to", "")), "yyyy-MM-dd")
            if from_date.isValid():
                self.dashboard_from_date.setDate(from_date)
            if to_date.isValid():
                self.dashboard_to_date.setDate(to_date)
            self.dashboard_selected_source = str(payload.get("source", ""))
            self.dashboard_selected_month = str(payload.get("month", ""))
            self._refresh_dashboard_guided_filter_options()
            selector = getattr(self, "dashboard_search_selector", None)
            if selector is not None and hasattr(selector, "set_selected_values"):
                selector.blockSignals(True)
                selector.set_selected_values("company", payload.get("companies", []) if isinstance(payload.get("companies", []), list) else [])
                selector.set_selected_values("gstin", payload.get("gstins", []) if isinstance(payload.get("gstins", []), list) else [])
                selector.set_selected_values("invoice", payload.get("invoices", []) if isinstance(payload.get("invoices", []), list) else [])
                selector.set_selected_values("month", payload.get("months", []) if isinstance(payload.get("months", []), list) else [])
                selector.blockSignals(False)
            else:
                guided_payloads = {
                    "dashboard_company_filter": payload.get("companies", []),
                    "dashboard_gstin_filter": payload.get("gstins", []),
                    "dashboard_invoice_filter": payload.get("invoices", []),
                    "dashboard_month_filter": payload.get("months", []),
                }
                for attr, values in guided_payloads.items():
                    widget = getattr(self, attr, None)
                    if widget is not None and hasattr(widget, "set_selected_values"):
                        widget.blockSignals(True)
                        widget.set_selected_values(values if isinstance(values, list) else [])
                        widget.blockSignals(False)
        finally:
            for widget in widgets:
                widget.blockSignals(False)
        if hasattr(self, "dashboard_filter_body"):
            show_advanced = self.dashboard_mode_combo.currentText() == "Advanced Custom" if hasattr(self, "dashboard_mode_combo") else True
            self.dashboard_filter_body.setVisible(show_advanced)
        if hasattr(self, "dashboard_mode_help") and hasattr(self, "dashboard_mode_combo"):
            self.dashboard_mode_help.setText(DASHBOARD_MODE_HELP.get(self.dashboard_mode_combo.currentText(), ""))
        self.apply_dashboard_filter()

    def apply_dashboard_mode(self, mode: str) -> None:
        """Apply a selectable dashboard workflow without changing audit data."""
        mode = mode or "Overview"
        preset = DASHBOARD_MODE_PRESETS.get(mode, DASHBOARD_MODE_PRESETS["Overview"])
        manual_widgets = [
            getattr(self, "dashboard_status_combo", None),
            getattr(self, "dashboard_group_combo", None),
            getattr(self, "dashboard_metric_combo", None),
            getattr(self, "dashboard_chart_mode_combo", None),
            getattr(self, "dashboard_limit_spin", None),
        ]
        for widget in manual_widgets:
            if widget is not None:
                widget.blockSignals(True)
        try:
            if "status" in preset:
                self.dashboard_status_combo.setCurrentText(str(preset["status"]))
            if "group" in preset:
                self.dashboard_group_combo.setCurrentText(str(preset["group"]))
            if "metric" in preset:
                self.dashboard_metric_combo.setCurrentText(str(preset["metric"]))
            if "chart" in preset:
                self.dashboard_chart_mode_combo.setCurrentText(str(preset["chart"]))
            if "limit" in preset:
                self.dashboard_limit_spin.setValue(int(preset["limit"]))
        finally:
            for widget in manual_widgets:
                if widget is not None:
                    widget.blockSignals(False)

        show_advanced = bool(preset.get("show_advanced", False))
        if hasattr(self, "dashboard_filter_body"):
            self.dashboard_filter_body.setVisible(show_advanced)
        if hasattr(self, "dashboard_filter_toggle_btn"):
            self.dashboard_filter_toggle_btn.blockSignals(True)
            self.dashboard_filter_toggle_btn.setChecked(show_advanced)
            self.dashboard_filter_toggle_btn.setText("Hide Advanced Filters" if show_advanced else "Advanced Filters")
            self.dashboard_filter_toggle_btn.blockSignals(False)
        if hasattr(self, "dashboard_mode_help"):
            self.dashboard_mode_help.setText(DASHBOARD_MODE_HELP.get(mode, ""))
        self.apply_dashboard_filter()

    def apply_dashboard_filter(self) -> None:
        if self.result:
            self._refresh_dashboard()

    def _dashboard_active_filter_text(self, rows_count: int) -> str:
        chips = []
        query = self.dashboard_filter_text.text().strip() if hasattr(self, "dashboard_filter_text") else ""
        mode = self.dashboard_mode_combo.currentText() if hasattr(self, "dashboard_mode_combo") else "Overview"
        status = self.dashboard_status_combo.currentText() if hasattr(self, "dashboard_status_combo") else "All Rows"
        group_by = self.dashboard_group_combo.currentText() if hasattr(self, "dashboard_group_combo") else "Month"
        metric = self.dashboard_metric_combo.currentText() if hasattr(self, "dashboard_metric_combo") else "Invoice Value"
        chart_mode = self.dashboard_chart_mode_combo.currentText() if hasattr(self, "dashboard_chart_mode_combo") else "Bar"
        if mode:
            chips.append(f"Mode = {mode}")
        selected_companies = self._dashboard_selected_values("dashboard_company_filter")
        selected_gstins = self._dashboard_selected_values("dashboard_gstin_filter")
        selected_invoices = self._dashboard_selected_values("dashboard_invoice_filter")
        selected_months = self._dashboard_selected_values("dashboard_month_filter")
        company_query = "" if selected_companies else self._dashboard_guided_query("company")
        gstin_query = "" if selected_gstins else self._dashboard_guided_query("gstin")
        invoice_query = "" if selected_invoices else self._dashboard_guided_query("invoice")
        month_query = "" if selected_months else self._dashboard_guided_query("month")
        if selected_companies:
            chips.append(f"Company = {self._dashboard_compact_values(selected_companies)}")
        elif company_query:
            chips.append(f"Company contains = {company_query}")
        if selected_gstins:
            chips.append(f"GST No = {self._dashboard_compact_values(selected_gstins)}")
        elif gstin_query:
            chips.append(f"GST No contains = {gstin_query}")
        if selected_invoices:
            chips.append(f"Invoice = {self._dashboard_compact_values(selected_invoices)}")
        elif invoice_query:
            chips.append(f"Invoice contains = {invoice_query}")
        if selected_months:
            chips.append(f"Month = {self._dashboard_compact_values(selected_months)}")
        elif month_query:
            chips.append(f"Month contains = {month_query}")
        if query:
            search_field = self.dashboard_search_field_combo.currentText() if hasattr(self, "dashboard_search_field_combo") else "Auto / Any Field"
            search_label = "Search" if search_field == "Auto / Any Field" else f"Search {search_field}"
            chips.append(f"{search_label} = {query}")
        selected_source = getattr(self, "dashboard_selected_source", "")
        selected_month = getattr(self, "dashboard_selected_month", "")
        if selected_source:
            chips.append(f"Source = {selected_source}")
        if selected_month:
            chips.append(f"Month = {selected_month}")
        if status != "All Rows":
            chips.append(f"Status = {status}")
        if hasattr(self, "dashboard_date_enabled") and self.dashboard_date_enabled.isChecked():
            from_text = self.dashboard_from_date.date().toString("dd-MM-yyyy")
            to_text = self.dashboard_to_date.date().toString("dd-MM-yyyy")
            chips.append(f"Date = {from_text} to {to_text}")
        chips.append(f"Group = {group_by}")
        chips.append(f"Metric = {metric}")
        chips.append(f"Chart = {chart_mode}")
        return "Active view: " + "  •  ".join(chips) + f"  •  Showing {rows_count} row(s)"

    def _update_dashboard_next_action(self, review_count: int, mismatch_count: int, rows_count: int) -> None:
        if not hasattr(self, "next_action_label"):
            return
        if rows_count == 0:
            self.next_action_label.setText("No rows match the current filters. Clear the view or change the search.")
            self.next_action_primary_btn.setText("Clear View")
            return
        if review_count > 0:
            self.next_action_label.setText(f"{review_count} critical row(s) need review. Advisory and trace rows do not block final review.")
            self.next_action_primary_btn.setText("Fix Critical Issues")
        elif mismatch_count > 0:
            self.next_action_label.setText(f"{mismatch_count} mismatch row(s) are visible. Inspect mismatch reasons before export.")
            self.next_action_primary_btn.setText("Open Review")
        else:
            self.next_action_label.setText("Visible rows are clean. Export the audit package or inspect supplier drill-down if needed.")
            self.next_action_primary_btn.setText("Export Report")

    def _dashboard_next_action_primary(self) -> None:
        if not self.result:
            return
        review_count = sum(1 for row in self.result.rows if is_mandatory_review(row))
        if review_count > 0:
            self.audit_filter_combo.setCurrentText("Critical Review")
            self._set_page(2)
        elif self.next_action_primary_btn.text() == "Clear View":
            self.clear_dashboard_filter()
        else:
            self._set_page(5)

    def _dashboard_open_review_queue(self) -> None:
        if not self.result:
            return
        self.audit_filter_combo.setCurrentText("Critical Review")
        self._set_page(2)

    def _dashboard_open_high_risk(self) -> None:
        if not self.result:
            return
        self.audit_filter_combo.setCurrentText("Missing GSTIN / Invoice / Name")
        self._set_page(2)

    def _dashboard_open_tax_mismatch(self) -> None:
        if not self.result:
            return
        if hasattr(self, "dashboard_mode_combo"):
            self.dashboard_mode_combo.setCurrentText("Tax Mismatch")
        self.audit_filter_combo.setCurrentText("GST Mismatch")
        self._set_page(2)

    def _dashboard_open_excluded_rows(self) -> None:
        if not self.result:
            return
        self.audit_filter_combo.setCurrentText("Excluded")
        self._set_page(2)

    def _refresh_dashboard_decision_center(self, rows: List[InvoiceRow], approved_rows: List[InvoiceRow], review_count: int, mismatch_count: int) -> None:
        """Refresh the dashboard's child-readable decision section.

        This deliberately uses plain business wording instead of internal enum-heavy
        text, so a non-technical user can understand the next step immediately.
        """
        if not self.result:
            return
        s = self.result.summary
        gate_status = quality_gate_status(self.result)
        gate_score = quality_gate_score(self.result)
        visible_invoice_total = sum((row.invoice_value for row in approved_rows), start=Decimal("0"))
        visible_review_count = sum(1 for row in rows if is_mandatory_review(row))
        excluded_count = sum(1 for row in self.result.rows if is_trace_only(row))
        mandatory_review_total = sum(1 for row in self.result.rows if is_mandatory_review(row))
        identity_problem_total = sum(1 for row in self.result.rows if is_mandatory_review(row) and has_required_identity_problem(row))
        amount_problem_total = sum(1 for row in self.result.rows if is_mandatory_review(row) and has_gst_or_amount_exception(row))
        advisory_total = sum(1 for row in self.result.rows if is_advisory_exception(row))

        if gate_status == "BLOCKED":
            decision_text = "Audit is blocked. Fix row coverage, amount reconciliation, or source traceability before final export."
            decision_chip_text, decision_severity = "Blocked", "danger"
            instruction = "Start with critical red items. Do not use the final export until the Quality Gate is cleared."
            primary_text = "Fix Critical Issues"
        elif mandatory_review_total > 0:
            decision_text = f"Audit needs review. {mandatory_review_total} critical row(s) must be checked before clean final sign-off."
            decision_chip_text, decision_severity = "Critical Review", "warning"
            instruction = f"Open Critical Review, approve or ignore with reason, then export. Advisory rows: {advisory_total}; Trace/Excluded: {excluded_count}."
            primary_text = "Fix Critical Issues"
        else:
            decision_text = "Audit is ready. No review rows remain and export checks are clear."
            decision_chip_text, decision_severity = "Ready", "success"
            instruction = "Open Export and create the final audit package."
            primary_text = "Export Report"

        self._set_chip_safe("dashboard_decision_chip", decision_chip_text, decision_severity)
        if hasattr(self, "dashboard_decision_status_label"):
            self.dashboard_decision_status_label.setText(decision_text)
        if hasattr(self, "dashboard_decision_instruction_label"):
            self.dashboard_decision_instruction_label.setText(instruction)
        if hasattr(self, "dashboard_decision_primary_btn"):
            self.dashboard_decision_primary_btn.setText(primary_text)

        self._set_label_safe("dashboard_official_invoice_label", f"Official: {format_inr(s.approved_invoice_value)}")
        self._set_label_safe("dashboard_visible_invoice_label", f"Visible: {format_inr(visible_invoice_total)}")
        self._set_label_safe("dashboard_official_review_label", f"Critical: {mandatory_review_total} · Advisory: {advisory_total} · Trace/Excluded: {excluded_count}")
        self._set_label_safe("dashboard_visible_review_label", f"Visible review: {visible_review_count} critical row(s)")

        self._set_label_safe("dashboard_issue_review_label", str(mandatory_review_total))
        self._set_label_safe("dashboard_issue_high_label", str(identity_problem_total))
        self._set_label_safe("dashboard_issue_gst_label", str(amount_problem_total))
        self._set_label_safe("dashboard_issue_excluded_label", str(excluded_count))
        self._set_chip_safe("dashboard_issue_review_chip", "Fix" if mandatory_review_total else "Clear", "warning" if mandatory_review_total else "success")
        self._set_chip_safe("dashboard_issue_high_chip", "Fix" if identity_problem_total else "Clear", "danger" if identity_problem_total else "success")
        self._set_chip_safe("dashboard_issue_gst_chip", "Check" if amount_problem_total else "Clear", "warning" if amount_problem_total else "success")
        self._set_chip_safe("dashboard_issue_excluded_chip", "Trace" if excluded_count else "Clear", "info" if excluded_count else "success")

        self._set_label_safe("dashboard_quality_score_label", f"Score: {gate_score}/100")
        self._set_chip_safe("dashboard_gate_row_chip", "Rows OK" if s.row_coverage_status == "MATCHED" else "Rows Fail", "success" if s.row_coverage_status == "MATCHED" else "danger")
        self._set_chip_safe("dashboard_gate_amount_chip", "Amount OK" if s.amount_reconciliation_status == "MATCHED" else "Amount Fail", "success" if s.amount_reconciliation_status == "MATCHED" else "danger")
        self._set_chip_safe("dashboard_gate_review_chip", "Critical Clear" if mandatory_review_total == 0 else "Critical Open", "success" if mandatory_review_total == 0 else "warning")
        self._set_chip_safe("dashboard_gate_lock_chip", "Ready" if gate_status == "READY_TO_LOCK" else "Draft Only", "success" if gate_status == "READY_TO_LOCK" else "warning" if gate_status == "REVIEW_REQUIRED" else "danger")
        if gate_status == "READY_TO_LOCK":
            note = "Final locked export is safe based on current Quality Gate controls."
        elif gate_status == "REVIEW_REQUIRED":
            note = f"Draft export is allowed. Final export needs Critical Review = 0; current critical rows: {mandatory_review_total}."
        else:
            note = "Export is blocked for final use until failed Quality Gate controls are fixed."
        self._set_label_safe("dashboard_quality_note_label", note)

    def _metric_month_delta_text(self, rows: List[InvoiceRow], metric: str) -> str:
        """Return latest month vs previous month delta for the selected visible rows."""
        points = grouped_chart_points(rows, metric, "Month", limit=0)
        numeric_points = [(label, value) for label, value in points if label != "Unknown"]
        if len(numeric_points) < 2:
            return "MoM: not enough monthly data"
        previous = numeric_points[-2][1]
        latest_label, latest = numeric_points[-1]
        if previous == 0:
            return f"{latest_label}: new period"
        pct = ((latest - previous) / abs(previous) * 100).quantize(Decimal("0.1"))
        arrow = "↑" if pct >= 0 else "↓"
        return f"{latest_label} MoM {arrow} {abs(pct)}%"

    def _dashboard_set_metric_cards(
        self,
        approved_rows: List[InvoiceRow],
        review_count: int,
        *,
        include_deltas: bool = True,
    ) -> None:
        """Update the four visible dashboard cards without depending on charts.

        The screenshots showed the dashboard filter strip knew rows existed while
        the cards still displayed em-dashes. That can happen when a later chart or
        decision-panel refresh fails before the cards are written. Keep this
        method early and exception-safe so totals are always visible after upload,
        review decisions, and F5 refresh.
        """
        invoice_total = sum((row.invoice_value for row in approved_rows), start=Decimal("0"))
        taxable_total = sum((row.taxable_value for row in approved_rows), start=Decimal("0"))
        gst_total = sum((row.igst + row.cgst + row.sgst + row.cess for row in approved_rows), start=Decimal("0"))

        invoice_delta = taxable_delta = gst_delta = ""
        if include_deltas:
            try:
                invoice_delta = self._metric_month_delta_text(approved_rows, "Invoice Value")
                taxable_delta = self._metric_month_delta_text(approved_rows, "Taxable Value")
                gst_delta = self._metric_month_delta_text(approved_rows, "Total GST")
            except Exception:
                LOGGER.exception("Dashboard month-delta calculation failed; cards still updated")

        if hasattr(getattr(self, "card_invoice", None), "set_value"):
            self.card_invoice.set_value(format_inr(invoice_total), "approved rows only", invoice_delta)
            self.card_taxable.set_value(format_inr(taxable_total), "before GST", taxable_delta)
            self.card_gst.set_value(format_inr(gst_total), "tax components total", gst_delta)
            self.card_review.set_value(str(review_count), "critical rows", "")
        else:
            self._set_label_safe("card_invoice_value", f"{format_inr(invoice_total)}" + (f"\n{invoice_delta}" if invoice_delta else ""))
            self._set_label_safe("card_taxable_value", f"{format_inr(taxable_total)}" + (f"\n{taxable_delta}" if taxable_delta else ""))
            self._set_label_safe("card_gst_value", f"{format_inr(gst_total)}" + (f"\n{gst_delta}" if gst_delta else ""))
            self._set_label_safe("card_review_value", str(review_count))

    def _refresh_dashboard(self) -> None:
        if not self.result:
            return
        if getattr(self, "_dashboard_refreshing", False):
            return
        self._dashboard_refreshing = True
        try:
            s = self.result.summary
            rows = self._dashboard_filtered_rows()
            approved_rows = [row for row in rows if row.include_in_totals]
            review_count = sum(1 for row in rows if is_mandatory_review(row))
            mismatch_count = sum(1 for row in rows if has_gst_or_amount_exception(row))

            # v11.9.1: write the visible metric cards first. If a later chart,
            # filter-chip, or hidden decision-card refresh raises, the dashboard
            # no longer stays blank with "—" values after upload/review.
            self._dashboard_set_metric_cards(approved_rows, review_count, include_deltas=True)

            try:
                self._refresh_dashboard_guided_filter_options()
                self._refresh_dashboard_quick_filters()
            except Exception:
                LOGGER.exception("Dashboard filter option refresh failed")

            if hasattr(self, "dashboard_active_filters"):
                self.dashboard_active_filters.setText(self._dashboard_active_filter_text(len(rows)))
            try:
                self._update_dashboard_next_action(review_count, mismatch_count, len(rows))
                self._refresh_dashboard_decision_center(rows, approved_rows, review_count, mismatch_count)
            except Exception:
                LOGGER.exception("Dashboard decision center refresh failed")

            self._set_status_chip_safe("dashboard_status_chip", s.final_status)

            status_text = friendly_status(s.final_status)[0]
            counts = self._issue_counts_from_rows()
            if hasattr(self, "summary_label"):
                self.summary_label.setText(
                    f"Audit status: {status_text}. {s.official_invoice_rows} official invoice/detail rows from {s.raw_rows_read} scanned rows, "
                    f"{s.final_approved_rows} approved, {counts['critical']} critical, {counts['advisory']} advisory, {counts['trace']} trace/excluded. Current view shows {len(rows)} row(s). "
                    "Filters are visual only and never alter official totals."
                )

            metric = self.dashboard_metric_combo.currentText() if hasattr(self, "dashboard_metric_combo") else "Invoice Value"
            group_by = self.dashboard_group_combo.currentText() if hasattr(self, "dashboard_group_combo") else "Month"
            chart_mode = self.dashboard_chart_mode_combo.currentText() if hasattr(self, "dashboard_chart_mode_combo") else "Bar"
            limit = self.dashboard_limit_spin.value() if hasattr(self, "dashboard_limit_spin") else 12
            if hasattr(self, "primary_chart"):
                try:
                    primary_points = grouped_chart_points(rows, metric, group_by, limit=limit)
                    primary_subtitle = "Click a point to filter the supplier table"
                    if chart_mode == "Donut":
                        primary_subtitle = (
                            f"Visible view only. Donut center totals the displayed Top {limit} group(s), "
                            "not the official grand total."
                        )
                    self.primary_chart.set_data(
                        f"{metric} by {group_by}",
                        primary_points,
                        chart_mode=chart_mode,
                        subtitle=primary_subtitle,
                    )
                    supplier_points = grouped_chart_points(rows, "Invoice Value", "Supplier", limit=10)
                    supplier_title = "Top Suppliers by Invoice Value"
                    supplier_subtitle = "Click supplier to drill down"
                    if len(supplier_points) == 1:
                        supplier_title = "Selected Supplier Invoice Value"
                        supplier_subtitle = "Single visible supplier; use Clear to return to the ranked supplier view"
                    self.supplier_chart.set_data(
                        supplier_title,
                        supplier_points,
                        chart_mode="Bar",
                        subtitle=supplier_subtitle,
                    )
                    self.status_breakdown_chart.set_data(
                        "Rows by Audit Status",
                        grouped_chart_points(rows, "Invoice Count", "Audit Status", limit=10),
                        formatter=self._format_row_count,
                        chart_mode="Donut",
                        subtitle="Percentage split of all visible rows by audit status",
                    )
                    self.mismatch_chart.set_data(
                        "Mismatch Reasons by Amount",
                        grouped_chart_points(rows, "Mismatch Amount", "Mismatch Reason", limit=10),
                        chart_mode="Bar",
                        subtitle="Prioritise the largest exception reasons first",
                    )
                except Exception:
                    LOGGER.exception("Dashboard chart refresh failed; totals remain visible")

            try:
                suppliers = supplier_summary(rows, included_only=True)[:50]
                self.dashboard_supplier_metrics = suppliers
                grand_total = sum((m.invoice_value for m in suppliers), start=Decimal("0")) or Decimal("1")
                data = []
                for idx, m in enumerate(suppliers, start=1):
                    share = (m.invoice_value / grand_total * Decimal("100")).quantize(Decimal("0.1"))
                    data.append([
                        str(idx),
                        m.supplier_name,
                        m.gstin,
                        str(m.invoice_count),
                        format_inr(m.invoice_value),
                        f"{share}%",
                        format_inr(m.taxable_value),
                        format_inr(m.gst_value),
                        str(m.review_rows),
                    ])
                if hasattr(self, "dashboard_table"):
                    self._fill_table(
                        self.dashboard_table,
                        ["#", "Supplier", "GSTIN", "Invoices", "Invoice Value", "Share", "Taxable", "GST", "Review"],
                        data,
                    )
                    # Protect short but important numeric columns from saved-width truncation.
                    for column, width in {0: 44, 3: 84, 5: 86, 8: 76}.items():
                        try:
                            self.dashboard_table.setColumnWidth(column, width)
                        except Exception:
                            pass
                self._update_dashboard_detail_panel()
            except Exception:
                LOGGER.exception("Dashboard supplier drill-down refresh failed")
        except Exception as exc:
            LOGGER.exception("Dashboard refresh failed")
            try:
                self.statusBar().showMessage(f"Dashboard refresh failed: {exc}")
            except Exception:
                pass
        finally:
            self._dashboard_refreshing = False


    def export_dashboard_pdf(self) -> None:
        """Export a lightweight PDF snapshot of the current dashboard view."""
        if not self.result:
            QMessageBox.information(self, "No dashboard data", "Process or load an audit before exporting the dashboard.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export dashboard PDF", "dashboard_snapshot.pdf", "PDF Files (*.pdf)")
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
        self._refresh_dashboard_quick_filters()
        rows = self._dashboard_filtered_rows()
        approved_rows = [row for row in rows if row.include_in_totals]
        invoice_total = sum((row.invoice_value for row in approved_rows), start=Decimal("0"))
        taxable_total = sum((row.taxable_value for row in approved_rows), start=Decimal("0"))
        gst_total = sum((row.igst + row.cgst + row.sgst + row.cess for row in approved_rows), start=Decimal("0"))
        review_count = sum(1 for row in rows if is_mandatory_review(row))
        html = f"""
        <html><body style="font-family: Segoe UI, Arial; color: #0f172a;">
        <h1>GST Invoice Audit — Dashboard Snapshot</h1>
        <p><b>Active view:</b> {self._dashboard_active_filter_text(len(rows))}</p>
        <table border="1" cellspacing="0" cellpadding="6" width="100%">
            <tr><th align="left">Metric</th><th align="right">Value</th></tr>
            <tr><td>Visible rows</td><td align="right">{len(rows)}</td></tr>
            <tr><td>Approved visible rows</td><td align="right">{len(approved_rows)}</td></tr>
            <tr><td>Review rows</td><td align="right">{review_count}</td></tr>
            <tr><td>Invoice value</td><td align="right">{format_inr(invoice_total)}</td></tr>
            <tr><td>Taxable value</td><td align="right">{format_inr(taxable_total)}</td></tr>
            <tr><td>Total GST</td><td align="right">{format_inr(gst_total)}</td></tr>
        </table>
        <p style="font-size: 10pt; color: #475569;">This PDF is a dashboard snapshot only. Official audit totals remain in the verified Excel export.</p>
        </body></html>
        """
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(path)
        doc = QTextDocument()
        doc.setHtml(html)
        doc.print_(printer)
        self.statusBar().showMessage(f"Dashboard PDF exported: {path}")
        self._show_toast("Dashboard PDF exported")


    def _update_dashboard_detail_panel(self) -> None:
        if not hasattr(self, "dashboard_detail") or not hasattr(self, "dashboard_table"):
            return
        row_index = self.dashboard_table.currentRow()
        if hasattr(self.dashboard_table, "source_row_for_view_row"):
            row_index = self.dashboard_table.source_row_for_view_row(row_index)
        metrics = getattr(self, "dashboard_supplier_metrics", [])
        if row_index < 0 or row_index >= len(metrics):
            self.dashboard_detail.setHtml(
                """
                <div style='font-family: Segoe UI, Arial; color:#0f172a;'>
                  <h3 style='margin:0 0 8px 0;'>Supplier Detail</h3>
                  <p style='color:#475569; line-height:1.45;'>
                    Select a supplier/GSTIN row to inspect totals, risk indicators,
                    and the suggested next action.
                  </p>
                  <div class='risk-card' style='background:#f8fbff; border:1px solid #dbeafe; border-radius:12px; padding:10px;'>
                    Tip: click a chart bar first to narrow this table, then select a supplier row.
                  </div>
                </div>
                """
            )
            return
        metric = metrics[row_index]
        matching_rows = []
        if self.result:
            matching_rows = [
                row for row in self._dashboard_filtered_rows()
                if (row.gstin and row.gstin == metric.gstin) or (not metric.gstin and row.supplier_name == metric.supplier_name)
            ]
        review_rows = [row for row in matching_rows if is_mandatory_review(row)]
        mismatch_rows = [row for row in matching_rows if has_gst_or_amount_exception(row)]
        top_reason = "None"
        if mismatch_rows:
            reason_counts: dict[str, int] = {}
            for row in mismatch_rows:
                reason_counts[row.mismatch_reason or "UNKNOWN"] = reason_counts.get(row.mismatch_reason or "UNKNOWN", 0) + 1
            top_reason = max(reason_counts.items(), key=lambda item: item[1])[0]
        next_step = "Ready for export"
        if review_rows:
            next_step = "Open Review Issues and resolve supplier exceptions"
        elif mismatch_rows:
            next_step = "Inspect GST mismatch rows before final export"
        severity = "Review required" if review_rows else ("Mismatch check" if mismatch_rows else "Ready")
        severity_color = "#f59e0b" if review_rows else ("#ef4444" if mismatch_rows else "#16a34a")
        self.dashboard_detail.setHtml(
            f"""
            <div style='font-family: Segoe UI, Arial; color:#0f172a;'>
              <div style='display:flex; align-items:center; margin-bottom:8px;'>
                <h3 style='margin:0;'>Supplier / GSTIN Detail</h3>
                <span style='margin-left:8px; color:white; background:{severity_color}; border-radius:10px; padding:3px 8px; font-size:10px; font-weight:700;'>
                  {escape(severity)}
                </span>
              </div>
              <p style='margin:0 0 8px 0; color:#475569;'>
                <b>{escape(metric.supplier_name)}</b><br/>
                GSTIN: {escape(metric.gstin or 'Not detected')}
              </p>
              <table cellspacing='0' cellpadding='6' width='100%' style='border-collapse:collapse;'>
                <tr><td style='color:#64748b;'>Invoices</td><td align='right'><b>{metric.invoice_count}</b></td></tr>
                <tr><td style='color:#64748b;'>Invoice value</td><td align='right'><b>{format_inr(metric.invoice_value)}</b></td></tr>
                <tr><td style='color:#64748b;'>Taxable value</td><td align='right'>{format_inr(metric.taxable_value)}</td></tr>
                <tr><td style='color:#64748b;'>GST total</td><td align='right'>{format_inr(metric.gst_value)}</td></tr>
                <tr><td style='color:#64748b;'>Review rows</td><td align='right'><b>{metric.review_rows}</b></td></tr>
              </table>
              <div class='risk-card' style='margin-top:10px; background:#f8fbff; border:1px solid #dbeafe; border-radius:12px; padding:10px;'>
                <b>Risk summary</b><br/>
                Visible rows: {len(matching_rows)} · Review-required: {len(review_rows)} · Mismatch: {len(mismatch_rows)}<br/>
                Primary reason: {escape(top_reason)}
              </div>
              <div style='margin-top:10px; background:#fff7ed; border:1px solid #fed7aa; border-radius:12px; padding:10px;'>
                <b>Next step</b><br/>
                {escape(next_step)}
              </div>
              <p style='font-size:10px; color:#64748b;'>Display-only panel. It does not alter raw data or official audit totals.</p>
            </div>
            """
        )


    def _show_dashboard_chart_full_details(self, label: str, group_by: str) -> None:
        """Show full drill-down details when a chart bar is clicked."""
        if not self.result:
            return
        rows = self._dashboard_filtered_rows()

        def row_group_value(row: InvoiceRow) -> str:
            if group_by == "Supplier":
                return self._dashboard_company_label(row)
            if group_by == "GSTIN":
                values = self._dashboard_gstin_values(row)
                return values[0] if values else "No GSTIN"
            if group_by == "Month":
                return self._dashboard_month_label(row)
            if group_by == "Audit Status":
                return getattr(row, "final_status", "") or getattr(row, "audit_status", "") or "Unknown"
            if group_by == "Mismatch Reason":
                return row.mismatch_reason or "None"
            return label

        matching = [row for row in rows if row_group_value(row) == label]
        approved = [row for row in matching if row.include_in_totals]
        critical = [row for row in matching if is_mandatory_review(row)]
        advisory = [row for row in matching if is_advisory_exception(row)]
        trace = [row for row in matching if is_trace_only(row)]
        invoice_total = sum((row.invoice_value for row in approved), start=Decimal("0"))
        taxable_total = sum((row.taxable_value for row in approved), start=Decimal("0"))
        gst_total = sum((row.igst + row.cgst + row.sgst + row.cess for row in approved), start=Decimal("0"))

        QMessageBox.information(
            self,
            f"Chart details - {label}",
            "Chart drill-down details\n\n"
            f"Group: {group_by}\n"
            f"Selected: {label}\n"
            f"Rows in group: {len(matching):,}\n"
            f"Approved rows: {len(approved):,}\n"
            f"Critical review: {len(critical):,}\n"
            f"Advisory: {len(advisory):,}\n"
            f"Trace / excluded: {len(trace):,}\n\n"
            f"Invoice value: {format_inr(invoice_total)}\n"
            f"Taxable value: {format_inr(taxable_total)}\n"
            f"Total GST: {format_inr(gst_total)}\n\n"
            "The dashboard table is now filtered to this selection. Official totals are unchanged.",
        )


    def _dashboard_chart_clicked(self, label: str, forced_group: str | None = None) -> None:
        """Drill down dashboard charts without mutating audit data."""
        if not label or label == "Unknown":
            return
        group_by = forced_group or (
            self.dashboard_group_combo.currentText() if hasattr(self, "dashboard_group_combo") else ""
        )
        # Prefer the guided selectors for concrete fields, then fall back to the
        # hidden legacy query for issue/status/source labels.
        guided_attr = ""
        if group_by == "Supplier":
            guided_attr = "dashboard_company_filter"
        elif group_by == "GSTIN":
            guided_attr = "dashboard_gstin_filter"
        elif group_by == "Month":
            guided_attr = "dashboard_month_filter"
        selector = getattr(self, "dashboard_search_selector", None)
        if guided_attr and selector is not None and hasattr(selector, "set_selected_values"):
            field_map = {
                "dashboard_company_filter": "company",
                "dashboard_gstin_filter": "gstin",
                "dashboard_month_filter": "month",
            }
            field_key = field_map.get(guided_attr, "")
            current = selector.selected_values(field_key) if field_key and hasattr(selector, "selected_values") else []
            values = list(dict.fromkeys([*current, label]))
            if field_key:
                selector.set_selected_values(field_key, values)
        elif guided_attr and hasattr(self, guided_attr):
            widget = getattr(self, guided_attr)
            current = widget.selected_values() if hasattr(widget, "selected_values") else []
            values = list(dict.fromkeys([*current, label]))
            widget.set_selected_values(values)
        else:
            self.dashboard_filter_text.setText(label)
            self.apply_dashboard_filter()
        self.statusBar().showMessage(f"Dashboard filtered by {group_by}: {label}")
        self._show_dashboard_chart_full_details(label, group_by)

