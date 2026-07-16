from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GstinBranch:
    gstin: str
    state: str
    trade_name: str = ""


def validate_branch(branch: GstinBranch) -> bool:
    return len(branch.gstin.strip()) == 15 and bool(branch.state.strip())
