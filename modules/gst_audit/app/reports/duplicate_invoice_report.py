def filter_duplicate_items(queue):
    return [item for item in queue if "DUPLICATE" in item.issue_type.upper() or "DUPLICATE" in item.status.upper()]
