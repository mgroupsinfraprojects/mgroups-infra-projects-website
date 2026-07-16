REQUIRED_FIELDS = ("supplier_gstin", "recipient_gstin", "invoice_no", "invoice_value", "from_state", "to_state")


def build_eway_payload(data: dict) -> dict:
    missing = [field for field in REQUIRED_FIELDS if not str(data.get(field, "")).strip()]
    if missing:
        raise ValueError(f"Missing e-way bill fields: {', '.join(missing)}")
    return {field: data[field] for field in REQUIRED_FIELDS} | {"schema_status": "LOCAL_VALIDATED"}
