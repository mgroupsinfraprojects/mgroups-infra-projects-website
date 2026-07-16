def requires_eway_bill(invoice_value, threshold=50000):
    try:
        return float(invoice_value) >= float(threshold)
    except (TypeError, ValueError):
        return False
