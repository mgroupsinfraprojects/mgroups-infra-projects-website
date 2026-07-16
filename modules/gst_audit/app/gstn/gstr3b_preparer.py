def build_gstr3b_summary(rows):
    total_tax = sum((getattr(r, 'igst', 0) + getattr(r, 'cgst', 0) + getattr(r, 'sgst', 0) for r in rows), start=0)
    return {"total_tax": str(total_tax), "status": "PREPARED_LOCAL_SUMMARY_ONLY"}
