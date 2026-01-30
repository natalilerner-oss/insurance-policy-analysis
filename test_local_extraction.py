import json
import os
from pathlib import Path

from src.policy_extractor import extract_policy
from src.azure_clients import get_document_intelligence_client, get_openai_client


def test_extraction(pdf_path: str):
    doc_client = get_document_intelligence_client()
    openai_client = get_openai_client()
    deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")

    with open(pdf_path, "rb") as f:
        content = f.read()

    result = extract_policy(
        doc_client=doc_client,
        openai_client=openai_client,
        deployment=deployment,
        content=content,
        source_language="he",
    )

    return result


if __name__ == "__main__":
    pdf_path = os.environ.get("TEST_POLICY_PDF", "path/to/policy.pdf")
    if not Path(pdf_path).exists():
        raise FileNotFoundError(f"Policy PDF not found: {pdf_path}")

    result = test_extraction(pdf_path)
    print(json.dumps(result, indent=2, ensure_ascii=False))
