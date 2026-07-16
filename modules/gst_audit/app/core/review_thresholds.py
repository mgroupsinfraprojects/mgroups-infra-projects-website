from __future__ import annotations

import json
import os
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

DEFAULT_REVIEW_THRESHOLDS: dict[str, Decimal] = {
    # Admin-controlled ranges. Defaults are deliberately strict so tiny
    # rounding/freight/TDS/TCS differences do not flood Fix Issues.
    "critical_amount": Decimal("10000.00"),
    "advisory_amount": Decimal("2500.00"),
    "ignore_amount": Decimal("500.00"),
    "critical_percent": Decimal("10.00"),
    "gst_critical_amount": Decimal("2500.00"),
    "duplicate_min_amount": Decimal("10000.00"),
    "high_value_supplier": Decimal("100000.00"),
}


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def review_threshold_path() -> Path:
    configured = os.environ.get("GST_AUDIT_REVIEW_RULES", "").strip()
    if configured:
        return Path(configured)
    return _project_root() / "config" / "review_thresholds.json"


def _decimal(value: Any, default: Decimal) -> Decimal:
    try:
        if value is None or value == "":
            return default
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError, TypeError):
        return default


def load_review_thresholds() -> dict[str, Decimal]:
    """Load admin-controlled review thresholds.

    Defaults are intentionally conservative. If the settings file is missing or
    invalid, review logic still works with safe values.
    """
    values = dict(DEFAULT_REVIEW_THRESHOLDS)
    path = review_threshold_path()
    try:
        payload = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except Exception:
        payload = {}
    for key, default in DEFAULT_REVIEW_THRESHOLDS.items():
        values[key] = _decimal(payload.get(key), default)
    # Keep the ranges sane even if a user types an invalid JSON manually.
    if values["advisory_amount"] > values["critical_amount"]:
        values["advisory_amount"] = values["critical_amount"]
    if values["ignore_amount"] > values["advisory_amount"]:
        values["ignore_amount"] = values["advisory_amount"]
    if values["critical_percent"] < Decimal("0.00"):
        values["critical_percent"] = DEFAULT_REVIEW_THRESHOLDS["critical_percent"]
    if values.get("gst_critical_amount", Decimal("0.00")) < Decimal("0.00"):
        values["gst_critical_amount"] = DEFAULT_REVIEW_THRESHOLDS["gst_critical_amount"]
    if values.get("duplicate_min_amount", Decimal("0.00")) < Decimal("0.00"):
        values["duplicate_min_amount"] = DEFAULT_REVIEW_THRESHOLDS["duplicate_min_amount"]
    return values


def save_review_thresholds(payload: dict[str, Any]) -> Path:
    path = review_threshold_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    values = load_review_thresholds()
    for key, default in DEFAULT_REVIEW_THRESHOLDS.items():
        values[key] = _decimal(payload.get(key), values.get(key, default))
    if values["advisory_amount"] > values["critical_amount"]:
        values["advisory_amount"] = values["critical_amount"]
    if values["ignore_amount"] > values["advisory_amount"]:
        values["ignore_amount"] = values["advisory_amount"]
    serializable = {key: str(value) for key, value in values.items()}
    path.write_text(json.dumps(serializable, indent=2), encoding="utf-8")
    return path
