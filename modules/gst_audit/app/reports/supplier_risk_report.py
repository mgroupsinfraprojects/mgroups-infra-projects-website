def rank_supplier_risk(suppliers):
    return sorted(suppliers, key=lambda s: (-getattr(s, 'mandatory_review_count', 0), -getattr(s, 'invoice_value', 0)))
