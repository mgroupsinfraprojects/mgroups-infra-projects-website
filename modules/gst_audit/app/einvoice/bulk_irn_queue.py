class BulkIrnQueue:
    def __init__(self): self.items=[]
    def add(self, payload): self.items.append(payload)
    def __len__(self): return len(self.items)
