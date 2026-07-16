def detect_layout_type(text: str) -> str:
    sample = (text or "").upper()
    if "GSTIN" in sample and "INVOICE" in sample:
        return "GST_INVOICE"
    return "UNKNOWN"
