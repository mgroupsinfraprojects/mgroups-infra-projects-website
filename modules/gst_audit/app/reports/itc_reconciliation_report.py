def build_itc_risk_summary(items):
    mandatory = [item for item in items if item.bucket == "MANDATORY_REVIEW"]
    return {"mandatory_itc_risk_count": len(mandatory), "blocking_difference_value": str(sum((i.difference_amount for i in mandatory), start=0))}
