from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import date
from decimal import Decimal

class Coverage(BaseModel):
    """Individual coverage line item"""
    name: str                          # ניתוחים שקל ראשון, תרופות מיוחדות
    start_date: Optional[date] = None  # Some coverages added later
    premium: Decimal

class InsuranceProduct(BaseModel):
    """Single insurance product/policy"""
    member_name: str                   # שם המבוטח
    policy_number: Optional[str] = None
    start_date: date                   # תחילת ביטוח
    company: str                       # שם חברת ביטוח
    product_name: str                  # שם המוצר (בריאות, מחלות קשות, etc.)
    details: Optional[str] = None      # For non-health: סכום ביטוח XXX ₪
    coverages: Optional[List[Coverage]] = None  # For health products
    premium: Optional[Decimal] = None  # Total premium (if no coverage breakdown)
    exclusions: Optional[str] = None   # החרגות
    discounts: Optional[str] = None    # הנחות (e.g., "15% עד 06/2026")
    premium_projections: Optional[List[Any]] = None  # Optional projection data

class FamilyMember(BaseModel):
    name: str
    role: Optional[str] = None

class InsurancePortfolioRequest(BaseModel):
    family_name: str
    report_date: date
    family_members: List[FamilyMember]
    insurance_products: List[InsuranceProduct]