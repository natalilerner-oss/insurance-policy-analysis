from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional, Tuple

from openai import AzureOpenAI

from src.policy_schema import PolicyDocument

EXTRACTION_SYSTEM_PROMPT = """
You are an expert Israeli insurance document analyst. Extract ALL data from the policy into structured JSON.

Key extraction rules:
1. Dates: Convert to ISO format (YYYY-MM-DD). Handle formats like DD/MM/YYYY and MM/YYYY.
2. Premiums: Extract both base price (לפני הנחה) and final price (אחרי הנחה).
3. Exclusions (החרגות): Map each exclusion to specific coverage/appendix.
4. Premium projections: Extract full age-based premium tables (תחזית השתנות פרמיה), including age and monthly premium.
5. Hebrew terms: Provide English translations for all Hebrew fields.
6. Coverage periods: Note if coverage is "מתחדשת" (renewable) vs fixed term.
7. Agent details: Capture agent name, phone, license, and address when available.
8. Preserve numeric precision for premiums.

Insurance companies mapping:
- פניקס / fnx = Phoenix (Fenix)
- הראל = Harel
- מגדל = Migdal
- כלל = Clal
- מנורה = Menora

Coverage types mapping:
- מחלות קשות = Critical Illness
- ניתוחים = Surgeries
- תרופות = Medications
- השתלות = Transplants
- אמבולטורי = Ambulatory Services
"""


def _extract_json_from_text(text: str) -> Dict[str, Any]:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in model output")
    return json.loads(match.group(0))


def analyze_document_text(doc_client, content: bytes) -> Tuple[str, int]:
    prebuilt = doc_client.begin_analyze_document("prebuilt-document", content).result()
    layout = doc_client.begin_analyze_document("prebuilt-layout", content).result()

    content_parts = []
    if prebuilt.content:
        content_parts.append(prebuilt.content)
    if layout.content:
        content_parts.append(layout.content)

    pages_processed = max(len(prebuilt.pages or []), len(layout.pages or []))
    return "\n\n".join(content_parts).strip(), pages_processed


def run_gpt_extraction(
    client: AzureOpenAI,
    deployment: str,
    document_text: str,
    source_language: str,
) -> Dict[str, Any]:
    schema_hint = PolicyDocument.model_json_schema()
    user_prompt = (
        "Extract the policy into this JSON schema. Use ISO dates. "
        "Return only valid JSON.\n\n"
        f"Schema: {json.dumps(schema_hint, ensure_ascii=False)}\n\n"
        f"Source language: {source_language}\n\n"
        "Document text:\n"
        f"{document_text}"
    )

    response = client.chat.completions.create(
        model=deployment,
        temperature=0,
        messages=[
            {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )
    raw = response.choices[0].message.content
    return _extract_json_from_text(raw)


def extract_policy(
    *,
    doc_client,
    openai_client: AzureOpenAI,
    deployment: str,
    content: bytes,
    source_language: str,
) -> Dict[str, Any]:
    document_text, pages_processed = analyze_document_text(doc_client, content)
    if not document_text:
        raise ValueError("No text extracted from document")

    extracted = run_gpt_extraction(
        client=openai_client,
        deployment=deployment,
        document_text=document_text,
        source_language=source_language,
    )

    extracted.setdefault("metadata", {})
    extracted["metadata"]["source_language"] = source_language
    extracted["metadata"]["pages_processed"] = pages_processed

    model = PolicyDocument.model_validate(extracted)
    return model.model_dump(mode="json")
