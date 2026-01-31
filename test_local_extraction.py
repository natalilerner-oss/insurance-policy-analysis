# test_local_extraction.py
import os
import json
from pathlib import Path

# Set test environment
# os.environ["AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"] = "your-endpoint"
# os.environ["AZURE_DOCUMENT_INTELLIGENCE_KEY"] = "your-key"
# os.environ["AZURE_OPENAI_ENDPOINT"] = "your-endpoint"
# os.environ["AZURE_OPENAI_KEY"] = "your-key"
# os.environ["AZURE_OPENAI_DEPLOYMENT"] = "gpt-4o"

from src.policy_extractor import extract_policy
from src.azure_clients import get_document_intelligence_client, get_openai_client

def test_extraction(pdf_path: str):
    doc_client = get_document_intelligence_client()
    openai_client = get_openai_client()
    
    with open(pdf_path, "rb") as f:
        content = f.read()
    
    result = extract_policy(
        doc_client=doc_client,
        openai_client=openai_client,
        deployment=os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o"),
        content=content,
        source_language="he"
    )
    
    return result

if __name__ == "__main__":
    import sys
    # Allow passing file path as argument
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else "path/to/policy.pdf"
    
    if os.path.exists(pdf_path):
        result = test_extraction(pdf_path)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"File not found: {pdf_path}")

