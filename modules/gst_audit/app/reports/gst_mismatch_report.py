def filter_gst_mismatch_items(queue):
    return [item for item in queue if "GST" in item.issue_type.upper() or "GSTIN" in item.issue_type.upper()]
