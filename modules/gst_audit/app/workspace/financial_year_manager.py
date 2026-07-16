def normalize_financial_year(value: str) -> str:
    text = str(value or "").strip().replace(" ", "")
    if len(text) == 7 and text[4] == "-" and text[:4].isdigit() and text[5:].isdigit():
        return text
    raise ValueError("Financial year must look like 2025-26")
