class ReturnStatusTracker:
    def __init__(self) -> None:
        self.status = {}
    def set_status(self, key, value): self.status[key] = value
    def get_status(self, key): return self.status.get(key, 'UNKNOWN')
