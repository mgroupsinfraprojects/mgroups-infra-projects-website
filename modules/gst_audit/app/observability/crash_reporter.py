def format_crash_report(exc: BaseException) -> dict:
    return {"error_type": type(exc).__name__, "message": str(exc)}
