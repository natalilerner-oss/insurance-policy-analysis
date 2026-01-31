# test_local_extraction.py
import os
import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Load environment variables from local.settings.json
def load_local_settings():
    settings_path = Path("local.settings.json")
    if settings_path.exists():
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                settings = json.load(f)
                values = settings.get("Values", {})
                for k, v in values.items():
                    if k not in os.environ:
                        os.environ[k] = str(v)
            print(f"Loaded {len(values)} settings from local.settings.json")
        except Exception as e:
            print(f"Failed to load local.settings.json: {e}")

load_local_settings()

from src.policy_extractor import extract_policy
from src.azure_clients import get_document_intelligence_client, get_openai_client

def test_extraction(pdf_path: str):
    print(f"Testing extraction for: {pdf_path}")
    
    try:
        doc_client = get_document_intelligence_client()
        openai_client = get_openai_client()
        deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
        
        print(f"Using deployment: {deployment}")
        
        if not os.path.exists(pdf_path):
            print(f"Error: File not found: {pdf_path}")
            return None

        with open(pdf_path, "rb") as f:
            content = f.read()
            
        print(f"File read, size: {len(content)} bytes. Starting extraction...")

        result = extract_policy(
            doc_client=doc_client,
            openai_client=openai_client,
            deployment=deployment,
            content=content,
            source_language="he"
        )

        return result
    except Exception as e:
        print(f"Extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    if len(sys.argv) > 1:
        sample_pdf = sys.argv[1]
    else:
        # Default to a file if exists, or warn
        sample_pdf = "sample_policy.pdf"
    
    if not os.path.exists(sample_pdf):
        print(f"Please provide a path to a PDF file.\nUsage: python test_local_extraction.py <path_to_pdf>")
        if os.path.exists("sample_policy.txt"):
             print("\nNote: sample_policy.txt exists, but this tool expects a PDF file for full Document Intelligence testing.")
    else:
        print("Starting test...")
        result = test_extraction(sample_pdf)
        if result:
            print("Extraction successful!")
            output_file = f"{Path(sample_pdf).stem}_result.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"Result saved to {output_file}")
            print("\nPreview:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
