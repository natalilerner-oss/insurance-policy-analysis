"""Flexible document schema that supports multiple financial document types.

Extends PolicyLens beyond insurance policies to handle invoices, receipts,
quotes, purchase orders, and tax documents.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Supported document types
# ---------------------------------------------------------------------------

DOCUMENT_TYPES = (
    "policy",
    "invoice",
    "receipt",
    "quote",
    "purchase_order",
    "tax_document",
    "document",  # generic fallback
)

# Hebrew labels are defined in document_helpers to avoid circular imports
# and to keep this module free from lightweight-consumer dependencies.
# Re-export here for backward compatibility.
from src.document_helpers import DOCUMENT_TYPE_LABELS_HE  # noqa: F401


# ---------------------------------------------------------------------------
# Shared sub-models
# ---------------------------------------------------------------------------

class Party(BaseModel):
    """Represents a party (person or organisation) in a financial document."""
    name: Optional[str] = None
    name_en: Optional[str] = None
    id_number: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    fax: Optional[str] = None
    email: Optional[str] = None


class LineItem(BaseModel):
    """A single line item on an invoice, receipt, or quote."""
    item_number: Optional[int] = None
    code: Optional[str] = None
    description: Optional[str] = None
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    total: Optional[float] = None


class DocumentMetadata(BaseModel):
    source_language: Optional[str] = None
    extraction_confidence: Optional[float] = None
    pages_processed: Optional[int] = None
    source_file: Optional[str] = None
    extraction_date: Optional[str] = None


# ---------------------------------------------------------------------------
# Flexible document model
# ---------------------------------------------------------------------------

class FinancialDocument(BaseModel):
    """A flexible document model that can represent any financial document type.

    For *policies* the policy-specific fields (carrier, policyholder, coverages,
    exclusions, etc.) are populated.  For other document types the party and
    line-item fields are used instead.
    """

    # -- Core identification --------------------------------------------------
    document_type: str = Field(default="document", description="One of: " + ", ".join(DOCUMENT_TYPES))
    document_number: Optional[str] = None
    document_date: Optional[str] = None

    # -- Party information (invoices, receipts, quotes, POs) ------------------
    from_party: Optional[Party] = None
    to_party: Optional[Party] = None

    # -- Financial line items -------------------------------------------------
    line_items: List[LineItem] = Field(default_factory=list)
    subtotal: Optional[float] = None
    discount: Optional[float] = None
    tax: Optional[float] = None
    total: Optional[float] = None
    currency: Optional[str] = Field(default="ILS")

    # -- Order / delivery details ---------------------------------------------
    po_number: Optional[str] = None
    delivery_date: Optional[str] = None
    payment_terms: Optional[str] = None
    payment_method: Optional[str] = None

    # -- Policy-specific (kept for backward compatibility) --------------------
    policy_number: Optional[str] = None
    carrier: Optional[Dict[str, Any]] = None
    policyholder: Optional[Dict[str, Any]] = None
    effective_dates: Optional[Dict[str, Any]] = None
    coverages: List[Dict[str, Any]] = Field(default_factory=list)
    exclusions: List[Dict[str, Any]] = Field(default_factory=list)
    premium_projections: List[Dict[str, Any]] = Field(default_factory=list)
    total_monthly_premium: Optional[float] = None
    payment: Optional[Dict[str, Any]] = None
    agent: Optional[Dict[str, Any]] = None
    special_conditions: List[str] = Field(default_factory=list)

    # -- Metadata -------------------------------------------------------------
    metadata: Optional[DocumentMetadata] = None
