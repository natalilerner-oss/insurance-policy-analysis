import os
from typing import Any, Dict, Optional

from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from azure.storage.blob import BlobServiceClient
from openai import AzureOpenAI


def get_document_intelligence_client() -> DocumentAnalysisClient:
    endpoint = os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
    key = os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_KEY")
    if not endpoint or not key:
        raise ValueError("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT and AZURE_DOCUMENT_INTELLIGENCE_KEY are required")
    return DocumentAnalysisClient(endpoint=endpoint, credential=AzureKeyCredential(key))


def get_openai_client() -> AzureOpenAI:
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    key = os.environ.get("AZURE_OPENAI_KEY")
    api_version = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-10-21")
    if not endpoint or not key:
        raise ValueError("AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_KEY are required")
    
    # Configure retry behavior:
    # - max_retries=2: Reduce from default to fail faster on rate limits
    # - timeout=60.0: Set a reasonable timeout for individual requests
    # This helps avoid exceeding the frontend timeout (120s) when OpenAI returns 429 errors
    return AzureOpenAI(
        api_key=key,
        api_version=api_version,
        azure_endpoint=endpoint,
        max_retries=2,
        timeout=60.0,
    )


def get_blob_service_client() -> Optional[BlobServiceClient]:
    """
    Returns a BlobServiceClient if configured, otherwise None.
    Checks for BLOB_CONNECTION_STRING, AzureWebJobsStorage, or BLOB_ACCOUNT_URL + BLOB_SAS_TOKEN.
    """
    # Prefer an explicit app setting, but fall back to Azure Functions' built-in
    # storage connection string when available.
    connection = os.environ.get("BLOB_CONNECTION_STRING") or os.environ.get("AzureWebJobsStorage")
    if connection:
        try:
            return BlobServiceClient.from_connection_string(connection)
        except Exception as e:
            # If the connection string is invalid, log and return None or let it bubble?
            # User wants improved error handling.
            import logging
            logging.error(f"Failed to create BlobServiceClient from connection string: {e}")
            return None

    account_url = os.environ.get("BLOB_ACCOUNT_URL")
    sas_token = os.environ.get("BLOB_SAS_TOKEN")
    if account_url and sas_token:
        try:
            # Append SAS token if not already in URL
            if "?" not in account_url and not account_url.endswith("?") and "?" in sas_token:
                # This logic assumes the SAS token needs to be appended, but BlobServiceClient
                # takes named arguments. However, if the user provided just the base URL, it works.
                return BlobServiceClient(account_url=account_url, credential=sas_token)
            # If user passed full SAS URL in account_url (unlikely based on valid configuration)
            return BlobServiceClient(account_url=account_url, credential=sas_token)
        except Exception as e:
            import logging
            logging.error(f"Failed to create BlobServiceClient from SAS: {e}")
            return None

    import logging
    logging.warning("Blob storage is not configured (missing connection string or account URL + SAS).")
    return None


def validate_app_configuration() -> Dict[str, Any]:
    """
    Checks for required environment variables and returns status.
    """
    import logging
    
    missing = []
    
    # Check Document Intelligence
    if not os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"):
        missing.append("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
    if not os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_KEY"):
        missing.append("AZURE_DOCUMENT_INTELLIGENCE_KEY")

    # Check Azure OpenAI
    if not os.environ.get("AZURE_OPENAI_ENDPOINT"):
        missing.append("AZURE_OPENAI_ENDPOINT")
    if not os.environ.get("AZURE_OPENAI_KEY"):
        missing.append("AZURE_OPENAI_KEY")

    # Check Blob Storage
    blob_status = get_blob_config_status()
    if not blob_status["configured"]:
        missing.extend(blob_status["missing"])

    if missing:
        logging.warning(f"Configuration Warning: Missing environment variables: {', '.join(missing)}")
    else:
        logging.info("App configuration is valid.")

    return {"valid": len(missing) == 0, "missing": missing, "blob_status": blob_status}


def get_blob_config_status() -> Dict[str, Any]:
    connection = os.environ.get("BLOB_CONNECTION_STRING")
    func_storage = os.environ.get("AzureWebJobsStorage")
    account_url = os.environ.get("BLOB_ACCOUNT_URL")
    sas_token = os.environ.get("BLOB_SAS_TOKEN")
    if connection:
        return {"configured": True, "mode": "connection_string", "missing": []}
    if func_storage:
        return {"configured": True, "mode": "azure_webjobs_storage", "missing": []}
    if account_url and sas_token:
        return {"configured": True, "mode": "account_url", "missing": []}

    missing = []
    if not connection and not func_storage:
        missing.append("BLOB_CONNECTION_STRING (or AzureWebJobsStorage)")
    if not account_url:
        missing.append("BLOB_ACCOUNT_URL")
    if not sas_token:
        missing.append("BLOB_SAS_TOKEN")
    return {"configured": False, "mode": None, "missing": missing}
