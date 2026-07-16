def normalize_period(value: str) -> str:
    text = str(value or "").strip().upper()
    if not text:
        raise ValueError("Period is required")
    return text
