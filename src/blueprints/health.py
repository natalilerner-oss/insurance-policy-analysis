import json
import os
import azure.functions as func
from src.blueprints.utils import assign_request_id, get_memory_info, get_request_id

VERSION = "3.1"
bp = func.Blueprint()

@bp.route(route="health", methods=["GET"])
def health(req: func.HttpRequest) -> func.HttpResponse:
    assign_request_id(req)
    JWT_SECRET = os.environ.get("JWT_SECRET")
    BLOB_CONNECTION_STRING = os.getenv("BLOB_CONNECTION_STRING")
    AZURE_WEBJOBS_STORAGE = os.getenv("AzureWebJobsStorage")
    BLOB_ACCOUNT_URL = os.getenv("BLOB_ACCOUNT_URL")
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", str(50 * 1024 * 1024)))
    MAX_BLOB_FETCH_MB = int(os.getenv("MAX_BLOB_FETCH_MB", str(200)))

    body = {
        "status": "ok",
        "version": VERSION,
        "jwtEnabled": bool(JWT_SECRET),
        "blobMode": bool(BLOB_CONNECTION_STRING or AZURE_WEBJOBS_STORAGE or BLOB_ACCOUNT_URL),
        "maxUploadMB": round(MAX_CONTENT_LENGTH / (1024 * 1024), 2),
        "maxBlobFetchMB": MAX_BLOB_FETCH_MB,
        "supportedFormats": ["pptx", "docx", "xlsx", "pdf"],
        "capabilities": [
            "insurance_policy_extraction",
            "office_document_text_extraction",
            "text_translation",
            "file_translation",
            "insurance_portfolio_excel_generation",
            "policy_comparison"
        ],
        "memory": get_memory_info(),
        "request_id": get_request_id(),
    }
    return func.HttpResponse(json.dumps(body), status_code=200, mimetype="application/json", headers={"X-Request-ID": get_request_id()})
