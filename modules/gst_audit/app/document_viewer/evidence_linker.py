from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EvidenceLink:
    source_file: str
    sheet_name: str = ""
    row_number: int = 0
    field_name: str = ""
    extracted_value: str = ""

    def label(self) -> str:
        location = f"{self.sheet_name}:{self.row_number}" if self.sheet_name else self.source_file
        return f"{location} -> {self.field_name} = {self.extracted_value}"
