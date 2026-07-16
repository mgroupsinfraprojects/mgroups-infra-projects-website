from __future__ import annotations

from PySide6.QtCore import Qt, QStringListModel
from PySide6.QtWidgets import QAbstractItemView, QComboBox, QCompleter, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QSplitter, QVBoxLayout, QWidget

from app.ui.widgets.data_table import DataTable


def build_supplier_tab(window) -> None:
    tab = QWidget()
    layout = QVBoxLayout(tab)
    layout.setSpacing(10)

    title = QLabel("Suppliers")
    title.setObjectName("PageTitle")
    note = QLabel("Supplier-only list. Search supports supplier name, GSTIN, invoice number, file, status, value, taxable value, and GST value. Select one or more suppliers to see combined invoice details below.")
    note.setObjectName("MutedText")
    note.setWordWrap(True)

    row = QHBoxLayout()
    window.supplier_search = QLineEdit()
    window.supplier_search.setPlaceholderText("Type supplier name or GSTIN — suggestions appear after audit")
    window.supplier_search_model = QStringListModel([])
    window.supplier_search_completer = QCompleter(window.supplier_search_model, window.supplier_search)
    window.supplier_search_completer.setCaseSensitivity(Qt.CaseInsensitive)
    window.supplier_search_completer.setFilterMode(Qt.MatchContains)
    window.supplier_search.setCompleter(window.supplier_search_completer)
    window.supplier_search.textChanged.connect(lambda _text: window.search_supplier())
    window.supplier_filter_combo = QComboBox()
    window.supplier_filter_combo.addItems(["All suppliers", "With review", "Clean only", "High value", "Has duplicates", "Selected only"])
    window.supplier_filter_combo.currentTextChanged.connect(lambda _text: window.search_supplier())
    btn = QPushButton("Search")
    btn.setObjectName("PrimaryActionButton")
    btn.clicked.connect(window.search_supplier)
    row.addWidget(window.supplier_search, 1)
    row.addWidget(window.supplier_filter_combo)
    row.addWidget(btn)

    window.supplier_cards_layout = QHBoxLayout()
    window.supplier_card_count, window.supplier_card_count_value = window._make_metric_card("Suppliers")
    window.supplier_card_invoices, window.supplier_card_invoices_value = window._make_metric_card("Invoices")
    window.supplier_card_value, window.supplier_card_value_value = window._make_metric_card("Invoice Value")
    window.supplier_card_review, window.supplier_card_review_value = window._make_metric_card("Suppliers Needing Review")
    for card in [window.supplier_card_count, window.supplier_card_invoices, window.supplier_card_value, window.supplier_card_review]:
        card.setToolTip("Click a supplier row below to see the invoice list and verification detail.")
        window.supplier_cards_layout.addWidget(card)

    window.supplier_summary_label = QLabel("Process data to view supplier totals. Then click a supplier row for invoice details.")
    window.supplier_summary_label.setObjectName("SummaryCards")
    window.supplier_summary_label.setWordWrap(True)

    window.supplier_table = DataTable()
    window.supplier_table.setObjectName("supplier_table")
    window.supplier_table.setSelectionBehavior(QAbstractItemView.SelectRows)
    window.supplier_table.setSelectionMode(QAbstractItemView.ExtendedSelection)

    invoice_panel = QFrame()
    invoice_panel.setObjectName("SupplierInvoicePanel")
    invoice_layout = QVBoxLayout(invoice_panel)
    invoice_layout.setContentsMargins(12, 12, 12, 12)
    invoice_layout.setSpacing(8)
    invoice_title = QLabel("Selected Supplier — Invoice Details")
    invoice_title.setObjectName("SectionTitle")
    window.supplier_detail_label = QLabel("Select a supplier/GSTIN row to view all invoice values, GST values, and review status.")
    window.supplier_detail_label.setObjectName("MutedText")
    window.supplier_detail_label.setWordWrap(True)
    window.supplier_invoice_table = DataTable()
    window.supplier_invoice_table.setObjectName("supplier_invoice_table")
    invoice_layout.addWidget(invoice_title)
    invoice_layout.addWidget(window.supplier_detail_label)
    invoice_layout.addWidget(window.supplier_invoice_table, 1)

    splitter = QSplitter(Qt.Vertical)
    supplier_table_box = QFrame()
    supplier_table_box.setObjectName("SupplierTablePanel")
    supplier_box_layout = QVBoxLayout(supplier_table_box)
    supplier_box_layout.setContentsMargins(0, 0, 0, 0)
    supplier_box_layout.addWidget(window.supplier_table)
    splitter.addWidget(supplier_table_box)
    splitter.addWidget(invoice_panel)
    splitter.setSizes([430, 300])
    window.supplier_table.itemSelectionChanged.connect(window._update_supplier_invoice_details)

    layout.addWidget(title)
    layout.addWidget(note)
    layout.addLayout(row)
    layout.addLayout(window.supplier_cards_layout)
    layout.addWidget(window.supplier_summary_label)
    layout.addWidget(splitter, 1)
    window.tabs.addTab(tab, "4. Supplier / GSTIN")
