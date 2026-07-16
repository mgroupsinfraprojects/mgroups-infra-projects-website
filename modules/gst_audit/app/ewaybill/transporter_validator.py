def validate_vehicle_number(value: str) -> bool:
    return len(str(value or '').replace(' ', '')) >= 6
