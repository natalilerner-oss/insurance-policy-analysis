from __future__ import annotations

import json
from typing import Optional

from openai import AzureOpenAI

from src.hebrew_utils import contains_hebrew, normalize_hebrew

TRANSLATION_SYSTEM_PROMPT = (
    "You are a professional Hebrew-English translator for insurance documents. "
    "Translate faithfully, preserving names, numbers, and policy terminology. "
    "Return only the translated text."
)


def detect_language(text: str) -> str:
    if contains_hebrew(text):
        return "he"
    return "en"


def translate_text(client: AzureOpenAI, deployment: str, text: str) -> str:
    if not text:
        return text
    cleaned = normalize_hebrew(text)
    if not contains_hebrew(cleaned):
        return cleaned
    response = client.chat.completions.create(
        model=deployment,
        temperature=0,
        messages=[
            {"role": "system", "content": TRANSLATION_SYSTEM_PROMPT},
            {"role": "user", "content": cleaned},
        ],
    )
    return response.choices[0].message.content.strip()


def translate_json_blob(client: AzureOpenAI, deployment: str, json_text: str) -> str:
    prompt = (
        "Translate all Hebrew values in the following JSON to English. "
        "Preserve keys and structure. Return valid JSON only."
    )
    response = client.chat.completions.create(
        model=deployment,
        temperature=0,
        messages=[
            {"role": "system", "content": TRANSLATION_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
            {"role": "user", "content": json_text},
        ],
    )
    return response.choices[0].message.content.strip()
