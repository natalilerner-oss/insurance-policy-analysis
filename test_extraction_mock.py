import json
import os
from pathlib import Path

# Mock the clients
class MockDocClient:
    def begin_analyze_document(self, model_id, document, locale=None):
        class MockPoller:
            def result(self):
                return MockResult()
        return MockPoller()

class MockResult:
    def __init__(self):
        self.content = "Sample insurance policy content extracted from PDF."
        self.pages = [1]  # Mock pages

class MockOpenAIClient:
    def chat_completions_create(self, model, messages, **kwargs):
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

# Import the actual extract_policy but with mocks
import sys
sys.path.insert(0, 'src')

from policy_extractor import extract_policy

def test_extraction_mock(pdf_path: str):
    doc_client = get_document_intelligence_client()
    openai_client = get_openai_client()
    deployment = "gpt-4o"

    with open(pdf_path, "rb") as f:
        content = f.read()

    result = extract_policy(
        doc_client=doc_client,
        openai_client=openai_client,
        deployment=deployment,
        content=content,
        source_language="en",
    )

    return result

if __name__ == "__main__":
    # Create a simple text file as "PDF" for testing
    pdf_path = "sample_policy.txt"
    with open(pdf_path, "w") as f:
        f.write("Sample Insurance Policy\nPolicy Number: 123456789\nInsured: John Doe\n")

    result = test_extraction_mock(pdf_path)
    print(json.dumps(result, indent=2, ensure_ascii=False))