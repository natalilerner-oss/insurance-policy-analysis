"""Helper functions for working with any financial document type.

These utilities provide a uniform interface regardless of whether the
document is an insurance policy, invoice, receipt, quote, etc.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from src.document_schema import DOCUMENT_TYPE_LABELS_HE


# ---------------------------------------------------------------------------
# Document type detection
# ---------------------------------------------------------------------------

def detect_document_type(data: Dict[str, Any]) -> str:
    """Detect the document type from extracted data.

    Returns one of: ``policy``, ``invoice``, ``receipt``, ``quote``,
    ``purchase_order``, ``tax_document``, or ``document`` (fallback).
    """
    # If the extractor already set a type, trust it.
    explicit = data.get("document_type")
    if explicit and explicit != "document":
        return explicit

    # Heuristic detection based on field presence (check key existence, not just truthy values,
    # since fields like policyholder may be present but set to None).
    if "policy_number" in data or "carrier" in data or "policyholder" in data:
        return "policy"

    if data.get("line_items"):
        # Distinguish invoice vs receipt vs quote vs PO
        if data.get("receipt_number") or data.get("payment_method"):
            return "receipt"
        if data.get("po_number") and not data.get("invoice_number"):
            return "purchase_order"
        # Default line-item document is invoice
        return "invoice"

    if data.get("invoice_number"):
        return "invoice"
    if data.get("receipt_number"):
        return "receipt"
    if data.get("quote_number"):
        return "quote"

    return "document"


# ---------------------------------------------------------------------------
# Unified accessors
# ---------------------------------------------------------------------------

def get_party_name(doc: Dict[str, Any]) -> str:
    """Return the main party/client name regardless of document type."""
    doc_type = doc.get("document_type", detect_document_type(doc))

    if doc_type == "policy":
        holder = doc.get("policyholder")
        if isinstance(holder, dict):
            return holder.get("name") or holder.get("name_en") or "Unknown"
        return "Unknown"

    # For invoices/receipts/quotes/POs, use to_party (the recipient/customer).
    to_party = doc.get("to_party")
    if isinstance(to_party, dict):
        return to_party.get("name") or to_party.get("name_en") or "Unknown"
    return "Unknown"


def get_issuer_name(doc: Dict[str, Any]) -> str:
    """Return the issuing party (carrier for policies, supplier for invoices)."""
    doc_type = doc.get("document_type", detect_document_type(doc))

    if doc_type == "policy":
        carrier = doc.get("carrier")
        if isinstance(carrier, dict):
            return carrier.get("name") or carrier.get("name_en") or "Unknown"
        return "Unknown"

    from_party = doc.get("from_party")
    if isinstance(from_party, dict):
        return from_party.get("name") or from_party.get("name_en") or "Unknown"
    return "Unknown"


def get_document_number(doc: Dict[str, Any]) -> str:
    """Return the document's primary identifier."""
    return (
        doc.get("document_number")
        or doc.get("policy_number")
        or doc.get("invoice_number")
        or doc.get("receipt_number")
        or doc.get("quote_number")
        or doc.get("po_number")
        or "N/A"
    )


def get_total_amount(doc: Dict[str, Any]) -> float:
    """Return the document total (premium for policies, total for others)."""
    doc_type = doc.get("document_type", detect_document_type(doc))

    if doc_type == "policy":
        return float(doc.get("total_monthly_premium") or 0)

    return float(
        doc.get("total")
        or doc.get("total_amount")
        or doc.get("subtotal")
        or 0
    )


def get_document_date(doc: Dict[str, Any]) -> Optional[str]:
    """Return the primary date for any document type."""
    if doc.get("document_date"):
        return doc["document_date"]

    eff = doc.get("effective_dates")
    if isinstance(eff, dict):
        return eff.get("print_date") or eff.get("renewal_date")

    return None


def get_document_type_label(doc_type: str) -> str:
    """Return the Hebrew UI label for a document type."""
    return DOCUMENT_TYPE_LABELS_HE.get(doc_type, "מסמך")


def is_policy(doc: Dict[str, Any]) -> bool:
    """Check whether a document is an insurance policy."""
    return doc.get("document_type", detect_document_type(doc)) == "policy"
