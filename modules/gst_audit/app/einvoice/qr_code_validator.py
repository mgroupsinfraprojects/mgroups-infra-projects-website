def validate_qr_payload(payload: dict) -> bool:
    required = {"supplier_gstin", "recipient_gstin", "invoice_no", "invoice_value"}
    return required.issubset(set(payload))
