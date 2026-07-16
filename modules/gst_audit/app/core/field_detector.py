from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from app.core.header_detector import detect_header_map_with_metadata


@dataclass(frozen=True)
class FieldDetectionResult:
    field_map: Dict[str, int]
    header_row: int
    data_start: int
    confidence_score: int = 0
    uncertain: bool = False
    warning: str = ""


class FieldDetector:
    """Small service wrapper around header/value detection."""

    def detect(self, frame, max_scan_rows: int = 40, min_score: int = 2) -> FieldDetectionResult:
        detection = detect_header_map_with_metadata(frame, max_scan_rows=max_scan_rows, min_score=min_score)
        return FieldDetectionResult(
            field_map=detection.field_map,
            header_row=detection.header_row,
            data_start=detection.data_start,
            confidence_score=detection.score,
            uncertain=detection.uncertain,
            warning=detection.warning,
        )

    @staticmethod
    def get(values: List[str], field_map: Dict[str, int], field: str) -> str:
        col = field_map.get(field)
        if col is None or col >= len(values):
            return ""
        return values[col]
