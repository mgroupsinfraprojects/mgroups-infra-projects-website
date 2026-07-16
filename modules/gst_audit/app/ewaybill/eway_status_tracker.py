class EWayStatusTracker:
    def __init__(self): self.status={}
    def update(self, ewb_no, status): self.status[ewb_no]=status
    def get(self, ewb_no): return self.status.get(ewb_no, 'UNKNOWN')
