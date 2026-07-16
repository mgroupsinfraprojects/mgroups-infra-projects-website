from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CompanyProfile:
    company_id: str
    legal_name: str
    pan: str
    gstins: tuple[str, ...]
    state: str = ""
    financial_years: tuple[str, ...] = field(default_factory=tuple)

    def validate(self) -> None:
        if not self.company_id.strip() or not self.legal_name.strip():
            raise ValueError("Company id and legal name are required")
        if self.pan and len(self.pan.strip()) != 10:
            raise ValueError("PAN must be 10 characters")
        if not self.gstins:
            raise ValueError("At least one GSTIN is required")


class CompanyManager:
    def __init__(self) -> None:
        self._companies: dict[str, CompanyProfile] = {}

    def add_company(self, company: CompanyProfile) -> None:
        company.validate()
        self._companies[company.company_id] = company

    def get_company(self, company_id: str) -> CompanyProfile | None:
        return self._companies.get(company_id)

    def list_companies(self) -> list[CompanyProfile]:
        return sorted(self._companies.values(), key=lambda c: c.legal_name)
