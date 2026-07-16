class OcrEngineContract:
    """Contract marker: critical OCR fields must be human-reviewed below confidence threshold."""
    min_auto_accept_confidence = 0.90
