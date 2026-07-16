from uuid import uuid4


class SessionManager:
    def __init__(self): self.sessions={}
    def create(self, username):
        token=str(uuid4()); self.sessions[token]=username; return token
    def actor(self, token): return self.sessions.get(token)
