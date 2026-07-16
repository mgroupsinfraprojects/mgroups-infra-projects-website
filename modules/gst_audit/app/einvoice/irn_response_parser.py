def parse_irn_response(response: dict) -> dict:
    return {"irn": response.get("Irn", ""), "ack_no": response.get("AckNo", ""), "qr": response.get("SignedQRCode", "")}
