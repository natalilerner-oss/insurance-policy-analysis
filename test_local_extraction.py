import os
import json
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env or local.settings.json
load_dotenv()

# If strict local settings are needed, we can parse local.settings.json manually
# but load_dotenv is usually sufficient for scripts.

from src.policy_extractor import extract_policy
from src.azure_clients import get_document_intelligence_client, get_openai_client

def test_extraction(pdf_path: str):
    print(f"Testing extraction for: {pdf_path}")
    
    try:
        doc_client = get_document_intelligence_client()
        openai_client = get_openai_client()
        deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
        
        print(f"Using deployment: {deployment}")
        
        with open(pdf_path, "rb") as f:
            content = f.read()
        
        print("Sending to Azure Document Intelligence and OpenAI...")
        result = extract_policy(
            doc_client=doc_client,
            openai_client=openai_client,
            deployment=deployment,
            content=content,
            source_language="he"  # Defaulting to Hebrew as per project
        )
        
        return result
        
    except Exception as e:
        print(f"Error during extraction: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test policy extraction locally")
    parser.add_argument("pdf_path", help="Path to the PDF file")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.pdf_path):
        print(f"File not found: {args.pdf_path}")
        exit(1)
        
    result = test_extraction(args.pdf_path)
    
    if result:
        print("\n--- Extraction Result ---")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        # Optionally save to file
        output_path = f"{args.pdf_path}.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\nResult saved to: {output_path}")
