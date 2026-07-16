from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FieldMapping:
    source_to_target: dict[str, str]
    required_targets: tuple[str, ...] = ("supplier_name", "gstin", "invoice_no", "invoice_value")

    def validate(self) -> None:
        targets = set(self.source_to_target.values())
        missing = [target for target in self.required_targets if target not in targets]
        if missing:
            raise ValueError(f"Missing mapped targets: {', '.join(missing)}")


def map_row(row: dict, mapping: FieldMapping) -> dict:
    mapping.validate()
    return {target: row.get(source, "") for source, target in mapping.source_to_target.items()}
