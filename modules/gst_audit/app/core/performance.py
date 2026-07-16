from __future__ import annotations

import os
import time
from dataclasses import dataclass


@dataclass
class ProcessingStats:
    rows_processed: int = 0
    started_at: float = 0.0
    memory_mb: float = 0.0

    @classmethod
    def start(cls) -> "ProcessingStats":
        return cls(started_at=time.perf_counter())

    @property
    def elapsed_seconds(self) -> float:
        return max(time.perf_counter() - self.started_at, 0.001)

    @property
    def rows_per_second(self) -> float:
        return self.rows_processed / self.elapsed_seconds

    def update_memory(self) -> None:
        self.memory_mb = current_memory_mb()

    def progress_message(self, base: str) -> str:
        self.update_memory()
        return f"{base} | rows: {self.rows_processed:,} | speed: {self.rows_per_second:,.0f}/s | memory: {self.memory_mb:,.0f} MB"


def current_memory_mb() -> float:
    try:
        import psutil  # type: ignore
        return float(psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024))
    except Exception:
        try:
            import resource
            usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            # Linux returns KB, macOS returns bytes. This environment is Linux; keep fallback defensive.
            return float(usage / 1024 if usage > 10_000_000 else usage / 1024)
        except Exception:
            return 0.0
