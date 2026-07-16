from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import FrozenSet


@dataclass(frozen=True)
class AuditConfig:
    """Central configuration for parsing, validation, safety, and review rules."""

    ignored_gstins: FrozenSet[str] = field(default_factory=frozenset)
    self_gstins: FrozenSet[str] = field(default_factory=frozenset)
    chunk_size: int = 50_000
    header_scan_rows: int = 40
    header_min_score: int = 2
    low_rounding_limit: Decimal = Decimal("1.00")
    minor_rounding_limit: Decimal = Decimal("5.00")
    auto_accept_small_difference_limit: Decimal = Decimal("100.00")
    auto_accept_small_percent_limit: Decimal = Decimal("0.25")
    mandatory_review_amount_limit: Decimal = Decimal("500.00")
    medium_percent_limit: Decimal = Decimal("1.00")
    enable_invoice_gap_detection: bool = True
    enable_supplier_anomaly_detection: bool = True
    supplier_anomaly_multiplier: Decimal = Decimal("3.00")
    classify_self_invoices_as_review: bool = True
    max_mismatch_reasonable_expense: Decimal = Decimal("5000.00")

    # Safety limits. These prevent accidental or malicious resource exhaustion.
    max_file_size_mb: int = 500
    max_rows_per_file: int = 500_000
    max_sheets_per_file: int = 200
    max_columns_per_sheet: int = 256

    @staticmethod
    def normalize_gstin_set(values) -> FrozenSet[str]:
        return frozenset(str(v).strip().upper().replace(" ", "") for v in (values or []) if str(v).strip())

    def with_runtime_values(self, *, ignored_gstins=None, self_gstins=None) -> "AuditConfig":
        return AuditConfig(
            ignored_gstins=self.normalize_gstin_set(ignored_gstins) if ignored_gstins is not None else self.ignored_gstins,
            self_gstins=self.normalize_gstin_set(self_gstins) if self_gstins is not None else self.self_gstins,
            chunk_size=self.chunk_size,
            header_scan_rows=self.header_scan_rows,
            header_min_score=self.header_min_score,
            low_rounding_limit=self.low_rounding_limit,
            minor_rounding_limit=self.minor_rounding_limit,
            auto_accept_small_difference_limit=self.auto_accept_small_difference_limit,
            auto_accept_small_percent_limit=self.auto_accept_small_percent_limit,
            mandatory_review_amount_limit=self.mandatory_review_amount_limit,
            medium_percent_limit=self.medium_percent_limit,
            enable_invoice_gap_detection=self.enable_invoice_gap_detection,
            enable_supplier_anomaly_detection=self.enable_supplier_anomaly_detection,
            supplier_anomaly_multiplier=self.supplier_anomaly_multiplier,
            classify_self_invoices_as_review=self.classify_self_invoices_as_review,
            max_mismatch_reasonable_expense=self.max_mismatch_reasonable_expense,
            max_file_size_mb=self.max_file_size_mb,
            max_rows_per_file=self.max_rows_per_file,
            max_sheets_per_file=self.max_sheets_per_file,
            max_columns_per_sheet=self.max_columns_per_sheet,
        )
