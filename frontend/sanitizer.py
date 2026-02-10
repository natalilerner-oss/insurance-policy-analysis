"""
PII sanitization utilities for PolicyLens frontend.

Masks sensitive personal information (ID numbers, names, addresses,
phone numbers, emails) for safe display in the UI.
"""

import copy
import re
from typing import Any, Dict, List


# ---------------------------------------------------------------------------
# Masking helpers
# ---------------------------------------------------------------------------

def mask_id_number(value: str) -> str:
    """Mask ID number, showing only last 4 digits.  '303682272' -> '****2272'"""
    if not value:
        return value
    clean = re.sub(r"\D", "", str(value))
    if len(clean) <= 4:
        return "****"
    return "****" + clean[-4:]


def mask_name(full_name: str) -> str:
    """Keep first name, abbreviate the rest.  'נטלי קויפמן' -> 'נטלי ק.'"""
    if not full_name:
        return full_name
    parts = full_name.strip().split()
    if len(parts) <= 1:
        return full_name
    first = parts[0]
    rest = " ".join(p[0] + "." for p in parts[1:] if p)
    return f"{first} {rest}"


def mask_address(address: str) -> str:
    """Replace full address with a masked placeholder."""
    if not address:
        return address
    return "כתובת מוסתרת"


def mask_phone(phone: str) -> str:
    """Mask phone number, showing only last 4 digits."""
    if not phone:
        return phone
    digits = re.sub(r"\D", "", str(phone))
    if len(digits) <= 4:
        return "****"
    return "****-" + digits[-4:]


def mask_email(email: str) -> str:
    """Mask email address, preserving domain.  'user@example.com' -> '***@example.com'"""
    if not email or "@" not in str(email):
        return "***"
    _, domain = str(email).rsplit("@", 1)
    return f"***@{domain}"


# ---------------------------------------------------------------------------
# Key-based classification
# ---------------------------------------------------------------------------

_ID_KEYS = frozenset({"id_number", "identity_number"})
_PERSON_PARENTS = frozenset({
    "policyholder", "agent", "insured", "insured_person",
    "from_party", "to_party",
})
_NAME_KEYS = frozenset({"name", "full_name", "name_en"})
_MEMBER_NAME_KEYS = frozenset({"member_name"})
_ADDRESS_KEYS = frozenset({"address", "full_address"})
_PHONE_KEYS = frozenset({"phone", "phone_number", "mobile", "fax"})
_EMAIL_KEYS = frozenset({"email"})


def _mask_value(key: str, value: str, parent_key: str) -> str:
    """Apply the appropriate mask to a value based on its key and parent context."""
    k = key.lower()
    if k in _ID_KEYS:
        return mask_id_number(value)
    if k in _MEMBER_NAME_KEYS:
        return mask_name(value)
    if k in _NAME_KEYS and parent_key.lower() in _PERSON_PARENTS:
        return mask_name(value)
    if k in _ADDRESS_KEYS:
        return mask_address(value)
    if k in _PHONE_KEYS:
        return mask_phone(value)
    if k in _EMAIL_KEYS:
        return mask_email(value)
    return value


# ---------------------------------------------------------------------------
# Deep sanitization
# ---------------------------------------------------------------------------

def _sanitize_dict(data: Dict[str, Any], parent_key: str = "") -> Dict[str, Any]:
    result = {}
    for key, value in data.items():
        if isinstance(value, dict):
            result[key] = _sanitize_dict(value, parent_key=key)
        elif isinstance(value, list):
            result[key] = _sanitize_list(value, parent_key=key)
        elif isinstance(value, str):
            result[key] = _mask_value(key, value, parent_key)
        else:
            result[key] = value
    return result


def _sanitize_list(data: list, parent_key: str = "") -> list:
    return [
        _sanitize_dict(item, parent_key) if isinstance(item, dict)
        else _sanitize_list(item, parent_key) if isinstance(item, list)
        else item
        for item in data
    ]


def sanitize_policy(policy: Dict[str, Any]) -> Dict[str, Any]:
    """Return a deep copy of *policy* (or any document) with all PII fields masked."""
    return _sanitize_dict(copy.deepcopy(policy))


# Alias for use with any document type (invoices, receipts, etc.)
sanitize_document = sanitize_policy


def sanitize_policies(policies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sanitize every policy/document in a list."""
    return [sanitize_policy(p) for p in policies]
