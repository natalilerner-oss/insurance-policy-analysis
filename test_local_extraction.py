import json
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Mock clients for testing
class MockDocClient:
    def begin_analyze_document(self, model_id, document, locale=None):
        class MockPoller:
            def result(self):
                return MockResult()
        return MockPoller()

class MockResult:
    def __init__(self):
        self.content = "Sample insurance policy content extracted from PDF."
        self.pages = [1]

class MockOpenAIClient:
    def chat_completions_create(self, model, messages, temperature=0, **kwargs):
        class MockResponse:
            choices = [MockChoice()]
        return MockResponse()

class MockChoice:
    def __init__(self):
        self.message = MockMessage()

class MockMessage:
    content = '{"policy_number": "123456789", "insured_name": "John Doe", "coverage_type": "Health Insurance", "premium": 100, "effective_date": "2024-01-01", "metadata": {"source_language": "en", "pages_processed": 1}}'

def get_document_intelligence_client():
    return MockDocClient()

def get_openai_client():
    return MockOpenAIClient()

from src.policy_extractor import extract_policy


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
    pdf_path = os.environ.get("TEST_POLICY_PDF", "sample_policy.txt")
    if not Path(pdf_path).exists():
        raise FileNotFoundError(f"Policy file not found: {pdf_path}")

    result = test_extraction(pdf_path)
    print(json.dumps(result, indent=2, ensure_ascii=False))
