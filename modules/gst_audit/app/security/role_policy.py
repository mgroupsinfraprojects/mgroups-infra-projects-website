def normalize_role(role: str) -> str:
    return str(role or 'VIEWER').strip().upper().replace(' ', '_')
