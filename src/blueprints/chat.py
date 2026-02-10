import json
import os
from typing import Any, Dict, List

import azure.functions as func

from src.azure_clients import get_openai_client
from src.hebrew_utils import contains_hebrew
from src.document_helpers import detect_document_type, get_party_name, get_issuer_name, get_document_number, get_total_amount
from src.blueprints.utils import assign_request_id, error_response, verify_jwt, logger, get_request_id

bp = func.Blueprint()

# Configuration
CHAT_MODEL = os.environ.get("AZURE_OPENAI_CHAT_MODEL", os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1"))
CHAT_MAX_TOKENS = int(os.environ.get("CHAT_MAX_TOKENS", "1000"))
CHAT_TEMPERATURE = float(os.environ.get("CHAT_TEMPERATURE", "0.7"))

SYSTEM_PROMPT = """You are a helpful financial document assistant for PolicyLens, a system that manages Israeli financial documents including insurance policies, invoices, receipts, quotes, and more.
You help users understand their documents in both Hebrew and English.

IMPORTANT RULES:
1. Always mask sensitive information in your responses:
   - Show only last 4 digits of ID numbers (e.g., ****2272)
   - Use first name + initial for last names (e.g., נטלי ק.)
   - Never show full addresses
   - Mask phone numbers showing only last 4 digits
2. Answer based ONLY on the document data provided in the context.
3. If the user asks about something not in the provided data, say you don't have that information.
4. Respond in the same language the user uses (Hebrew or English).
5. Use currency symbol ₪ for Israeli Shekel amounts.
6. Be concise but thorough in your answers.
7. When referring to documents, use the correct type (policy, invoice, receipt, etc.).
"""


def _build_policy_context(policies: List[Dict[str, Any]]) -> str:
    """Build a summarized context string from document data for the LLM."""
    if not policies:
        return "No documents loaded."

    parts = []
    for i, doc in enumerate(policies, 1):
        doc_type = doc.get("document_type", detect_document_type(doc))

        if doc_type == "policy":
            lines = [f"--- Policy {i} ---"]
            lines.append(f"Document Type: Insurance Policy")
            lines.append(f"Policy Number: {doc.get('policy_number', 'N/A')}")

            carrier = doc.get("carrier", {})
            if isinstance(carrier, dict):
                lines.append(f"Carrier: {carrier.get('name', 'N/A')}")

            holder = doc.get("policyholder", {})
            if isinstance(holder, dict):
                lines.append(f"Policyholder: {holder.get('name', 'N/A')}")
                if holder.get("date_of_birth"):
                    lines.append(f"Date of Birth: {holder['date_of_birth']}")

            lines.append(f"Total Monthly Premium: {doc.get('total_monthly_premium', 'N/A')}")

            coverages = doc.get("coverages", [])
            if coverages:
                lines.append("Coverages:")
                for cov in coverages:
                    if not isinstance(cov, dict):
                        continue
                    cov_type = cov.get("type") or cov.get("product_name") or "Unknown"
                    premium = cov.get("premium", {})
                    if isinstance(premium, dict):
                        amount = premium.get("final_monthly") or premium.get("base_monthly") or 0
                    else:
                        amount = premium or 0
                    lines.append(f"  - {cov_type}: ₪{amount}")

            exclusions = doc.get("exclusions", [])
            if exclusions:
                lines.append("Exclusions:")
                for exc in exclusions:
                    if isinstance(exc, dict):
                        conditions = ", ".join(exc.get("conditions", []))
                        lines.append(f"  - {exc.get('coverage', '')}: {conditions}")

        else:
            # Non-policy document (invoice, receipt, quote, etc.)
            type_map = {
                "invoice": "Invoice",
                "receipt": "Receipt",
                "quote": "Quote",
                "purchase_order": "Purchase Order",
                "tax_document": "Tax Document",
            }
            type_label = type_map.get(doc_type, "Document")
            lines = [f"--- {type_label} {i} ---"]
            lines.append(f"Document Type: {type_label}")
            lines.append(f"Document Number: {get_document_number(doc)}")
            lines.append(f"Date: {doc.get('document_date', 'N/A')}")
            lines.append(f"Issuer: {get_issuer_name(doc)}")
            lines.append(f"Recipient: {get_party_name(doc)}")
            lines.append(f"Total: ₪{get_total_amount(doc):,.2f}")

            line_items = doc.get("line_items", [])
            if line_items:
                lines.append("Line Items:")
                for item in line_items:
                    if not isinstance(item, dict):
                        continue
                    desc = item.get("description", "Unknown")
                    qty = item.get("quantity", "")
                    total = item.get("total", 0)
                    lines.append(f"  - {desc} (qty: {qty}) ₪{total}")

            if doc.get("subtotal") is not None:
                lines.append(f"Subtotal: ₪{doc['subtotal']}")
            if doc.get("tax") is not None:
                lines.append(f"Tax/VAT: ₪{doc['tax']}")
            if doc.get("discount") is not None:
                lines.append(f"Discount: ₪{doc['discount']}")
            if doc.get("po_number"):
                lines.append(f"PO Number: {doc['po_number']}")
            if doc.get("payment_terms"):
                lines.append(f"Payment Terms: {doc['payment_terms']}")

        source = doc.get("_source_file")
        if source:
            lines.append(f"Source File: {source}")

        parts.append("\n".join(lines))

    return "\n\n".join(parts)


@bp.route(route="chat", methods=["POST"])
def chat_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """Chat endpoint that answers questions about loaded insurance policies."""
    assign_request_id(req)
    logger.info("chat route triggered")

    ok, detail = verify_jwt(req)
    if not ok:
        return error_response("unauthorized", "Authorization failed", 401, details=detail)

    try:
        body = req.get_json()
    except ValueError:
        return error_response("bad_request", "Invalid JSON payload", 400)

    message = body.get("message", "").strip()
    if not message:
        return error_response("bad_request", "Message is required", 400)

    history = body.get("history", [])
    policies = body.get("policies", [])

    # Build context from policies
    policy_context = _build_policy_context(policies)

    # Build messages for the LLM
    messages = [
        {"role": "system", "content": f"{SYSTEM_PROMPT}\n\nPolicy Data:\n{policy_context}"},
    ]

    # Add conversation history (limit to last 10 exchanges to stay within token limits)
    for msg in history[-20:]:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})

    # Add the current user message
    messages.append({"role": "user", "content": message})

    try:
        client = get_openai_client()
        response = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=messages,
            max_tokens=CHAT_MAX_TOKENS,
            temperature=CHAT_TEMPERATURE,
        )

        assistant_message = response.choices[0].message.content
        is_hebrew = contains_hebrew(assistant_message)

        result = {
            "response": assistant_message,
            "language": "he" if is_hebrew else "en",
            "request_id": get_request_id(),
        }

        return func.HttpResponse(
            json.dumps(result, ensure_ascii=False),
            status_code=200,
            mimetype="application/json",
            headers={"X-Request-ID": get_request_id()},
        )

    except Exception as e:
        logger.error("Chat completion failed: %s", e, exc_info=True)
        return error_response("chat_failed", f"Failed to generate response: {str(e)}", 500)
