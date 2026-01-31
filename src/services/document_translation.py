from .translator import translate_text, TranslationError
from ..azure_clients import get_blob_service_client
from azure.storage.blob import BlobClient
import uuid
import os

def translate_remote_file(file_url: str, to_lang: str, from_lang: str, correlation_id: str) -> dict:
    """Translate a remote file by downloading, translating content, and uploading translated version."""
    try:
        # Download the file
        bc = BlobClient.from_blob_url(file_url)
        data = bc.download_blob().readall()
        
        # Assume text file for simplicity; decode
        try:
            text = data.decode('utf-8')
        except UnicodeDecodeError:
            raise TranslationError("File is not a valid text file")
        
        # Translate the text
        translated = translate_text(text, to_lang, from_lang)
        
        # Upload translated version to blob
        blob_service = get_blob_service_client()
        if not blob_service:
            raise TranslationError(
                "Blob storage not configured. Set BLOB_CONNECTION_STRING (or AzureWebJobsStorage on Azure Functions) or BLOB_ACCOUNT_URL + BLOB_SAS_TOKEN."
            )
        container_name = os.getenv("TRANSLATED_CONTAINER", "translated")
        translated_blob_name = f"{correlation_id}.txt"
        
        blob_client = blob_service.get_blob_client(container=container_name, blob=translated_blob_name)
        blob_client.upload_blob(translated.encode('utf-8'), overwrite=True, content_type="text/plain")
        
        translated_blob_url = blob_client.url
        
        # For download URL, could add SAS token if needed
        translated_download_url = translated_blob_url  # Placeholder
        
        return {
            "translatedBlobUrl": translated_blob_url,
            "translatedDownloadUrl": translated_download_url,
            "correlationId": correlation_id
        }
    except Exception as e:
        raise TranslationError(f"Document translation failed: {str(e)}")