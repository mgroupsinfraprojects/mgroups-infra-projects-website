def map_gstn_error(code: str) -> str:
    return {"AUTH": "Authentication failed", "SCHEMA": "Payload schema failed"}.get(str(code).upper(), "Unknown GSTN/GSP error")
