def validate_gstin_for_auth(gstin: str) -> bool:
    return len(str(gstin or '').strip()) == 15
