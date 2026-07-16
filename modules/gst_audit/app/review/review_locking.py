class ReviewLockRegistry:
    def __init__(self) -> None:
        self._locks: dict[tuple[str, int], str] = {}

    def acquire(self, session_id: str, row_id: int, actor: str) -> bool:
        key = (session_id, row_id)
        owner = self._locks.get(key)
        if owner and owner != actor:
            return False
        self._locks[key] = actor
        return True

    def release(self, session_id: str, row_id: int, actor: str) -> None:
        key = (session_id, row_id)
        if self._locks.get(key) == actor:
            del self._locks[key]
