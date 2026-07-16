def build_gstr1_summary(rows):
    return {"invoice_count": len(list(rows)), "status": "PREPARED_LOCAL_SUMMARY_ONLY"}
