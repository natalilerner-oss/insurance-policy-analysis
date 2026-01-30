from __future__ import annotations

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class Carrier(BaseModel):
    name: Optional[str] = Field(default=None, description="Carrier name in Hebrew or original language")
    name_en: Optional[str] = Field(default=None, description="Carrier name in English")
    phone: Optional[str] = None
    website: Optional[str] = None
    email: Optional[str] = None


class Policyholder(BaseModel):
    name: Optional[str] = None
    name_en: Optional[str] = None
    id_number: Optional[str] = None
    date_of_birth: Optional[date] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None


class EffectiveDates(BaseModel):
    print_date: Optional[date] = None
    renewal_date: Optional[date] = None
    index_date: Optional[str] = Field(default=None, description="YYYY-MM if available")


class CoveragePeriod(BaseModel):
    start: Optional[date] = None
    end: Optional[date] = None
    type: Optional[str] = None


class Premium(BaseModel):
    base_monthly: Optional[float] = None
    discount_percent: Optional[float] = None
    final_monthly: Optional[float] = None

    @field_validator("discount_percent")
    @classmethod
    def validate_discount(cls, value: Optional[float]) -> Optional[float]:
        if value is not None and (value < 0 or value > 100):
            raise ValueError("Discount must be between 0 and 100")
        return value


class Coverage(BaseModel):
    type: Optional[str] = None
    type_en: Optional[str] = None
    product_name: Optional[str] = None
    appendix_number: Optional[str] = None
    coverage_amount: Optional[float] = None
    period: Optional[CoveragePeriod] = None
    premium: Optional[Premium] = None


class Exclusion(BaseModel):
    coverage: Optional[str] = None
    appendix: Optional[str] = None
    conditions: List[str] = Field(default_factory=list)
    conditions_en: List[str] = Field(default_factory=list)


class PremiumProjectionPoint(BaseModel):
    age: Optional[int] = None
    date: Optional[str] = Field(default=None, description="YYYY-MM if available")
    monthly: Optional[float] = None


class PremiumProjectionGroup(BaseModel):
    coverage: Optional[str] = None
    appendix: Optional[str] = None
    projections: List[PremiumProjectionPoint] = Field(default_factory=list)


class Payment(BaseModel):
    method: Optional[str] = None
    frequency: Optional[str] = None


class Agent(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    license: Optional[str] = None
    address: Optional[str] = None


class Metadata(BaseModel):
    source_language: Optional[str] = None
    extraction_confidence: Optional[float] = None
    pages_processed: Optional[int] = None


class PolicyDocument(BaseModel):
    policy_number: Optional[str] = None
    carrier: Optional[Carrier] = None
    policyholder: Optional[Policyholder] = None
    effective_dates: Optional[EffectiveDates] = None
    coverages: List[Coverage] = Field(default_factory=list)
    exclusions: List[Exclusion] = Field(default_factory=list)
    premium_projections: List[PremiumProjectionGroup] = Field(default_factory=list)
    total_monthly_premium: Optional[float] = None
    payment: Optional[Payment] = None
    agent: Optional[Agent] = None
    special_conditions: List[str] = Field(default_factory=list)
    metadata: Optional[Metadata] = None
