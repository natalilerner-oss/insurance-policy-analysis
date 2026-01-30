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
    return AzureOpenAI(
        api_key=key,
        api_version=api_version,
        azure_endpoint=endpoint,
    )


def get_blob_service_client() -> Optional[BlobServiceClient]:
    connection = os.environ.get("BLOB_CONNECTION_STRING")
    if connection:
        return BlobServiceClient.from_connection_string(connection)

    account_url = os.environ.get("BLOB_ACCOUNT_URL")
    sas_token = os.environ.get("BLOB_SAS_TOKEN")
    if account_url and sas_token:
        return BlobServiceClient(account_url=account_url, credential=sas_token)

    return None


def get_blob_config_status() -> Dict[str, Any]:
    connection = os.environ.get("BLOB_CONNECTION_STRING")
    account_url = os.environ.get("BLOB_ACCOUNT_URL")
    sas_token = os.environ.get("BLOB_SAS_TOKEN")
    if connection:
        return {"configured": True, "mode": "connection_string", "missing": []}
    if account_url and sas_token:
        return {"configured": True, "mode": "account_url", "missing": []}

    missing = []
    if not connection:
        missing.append("BLOB_CONNECTION_STRING")
    if not account_url:
        missing.append("BLOB_ACCOUNT_URL")
    if not sas_token:
        missing.append("BLOB_SAS_TOKEN")
    return {"configured": False, "mode": None, "missing": missing}
