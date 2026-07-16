from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExtractionResult:
    field_name: str
    value: str
    confidence: float
    source_ref: str

    @property
    def requires_human_review(self) -> bool:
        return self.confidence < 0.90
