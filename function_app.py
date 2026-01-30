import base64
import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from io import BytesIO
from typing import Any, Dict, Optional, Tuple

import azure.functions as func
from azure.storage.blob import ContentSettings, generate_blob_sas, BlobSasPermissions
from requests_toolbelt.multipart.decoder import MultipartDecoder

from src.azure_clients import (
    get_blob_service_client,
    get_document_intelligence_client,
    get_openai_client,
)
from src.hebrew_utils import contains_hebrew
from src.policy_extractor import extract_policy
from src.job_store import load_job, save_job

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)


def _parse_multipart(body: bytes, content_type: str) -> Optional[Tuple[bytes, str]]:
    try:
        import cgi

        decoder = MultipartDecoder(body, content_type)
        file_parts = []
        fields: Dict[str, str] = {}

        for part in decoder.parts:
            headers = {k.decode().lower(): v.decode() for k, v in part.headers.items()}
            disposition = headers.get("content-disposition", "")
            _, params = cgi.parse_header(disposition)
            name = params.get("name")
            filename = params.get("filename")

            if filename:
                file_parts.append((name or "file", filename, part.content))
            elif name:
                fields[name] = part.text

        if "file_base64" in fields:
            filename = fields.get("filename", "document")
            return base64.b64decode(fields["file_base64"]), filename

        if file_parts:
            preferred = [p for p in file_parts if p[0] in {"file", "document", "upload"}]
            chosen = preferred[0] if preferred else file_parts[0]
            return chosen[2], chosen[1] or "upload"
        return None
    except Exception:
        return None


def _parse_request_payload(req: func.HttpRequest) -> Tuple[bytes, str]:
    content_type = req.headers.get("content-type", "").lower()
    body = req.get_body()

    if "multipart/form-data" in content_type:
        parsed = _parse_multipart(body, content_type)
        if parsed:
            return parsed

    try:
        payload = req.get_json()
    except ValueError as exc:
        raise ValueError("Invalid JSON payload") from exc

    file_base64 = payload.get("file_base64") or payload.get("data")
    if not file_base64:
        raise ValueError("file_base64 is required in JSON body")

    filename = payload.get("filename", "document")
    return base64.b64decode(file_base64), filename


def _detect_language(text: str) -> str:
    return "he" if contains_hebrew(text) else "en"


def _upload_result(job_id: str, data: Dict[str, Any]) -> Optional[str]:
    blob_service = get_blob_service_client()
    if not blob_service:
        return None

    container_name = os.environ.get("COMPLETED_JOBS_CONTAINER", "policy-extractions")
    container = blob_service.get_container_client(container_name)
    try:
        container.create_container()
    except Exception:
        pass

    blob_name = f"{job_id}.json"
    blob_client = container.get_blob_client(blob_name)
    blob_client.upload_blob(
        json.dumps(data, ensure_ascii=False),
        overwrite=True,
        content_settings=ContentSettings(content_type="application/json"),
    )

    sas = generate_blob_sas(
        account_name=blob_client.account_name,
        container_name=container_name,
        blob_name=blob_name,
        account_key=blob_service.credential.account_key,
        permission=BlobSasPermissions(read=True),
        expiry=datetime.utcnow() + timedelta(days=1),
    )
    return f"{blob_client.url}?{sas}"


def _run_extraction(job_id: str, content: bytes) -> None:
    try:
        doc_client = get_document_intelligence_client()
        openai_client = get_openai_client()
        deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")

        sample_text, _ = doc_client.begin_analyze_document("prebuilt-document", content).result(), None
        source_language = _detect_language(sample_text.content if sample_text else "")

        result = extract_policy(
            doc_client=doc_client,
            openai_client=openai_client,
            deployment=deployment,
            content=content,
            source_language=source_language,
        )

        download_url = _upload_result(job_id, result)
        save_job(
            job_id,
            {
                "jobId": job_id,
                "status": "completed",
                "result": result,
                "download_url": download_url,
            },
        )
    except Exception as exc:
        save_job(
            job_id,
            {
                "jobId": job_id,
                "status": "failed",
                "error": str(exc),
            },
        )


@app.route(route="extract_policy")
def extract_policy_sync(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Processing extract_policy request")
    try:
        content, _ = _parse_request_payload(req)
        doc_client = get_document_intelligence_client()
        openai_client = get_openai_client()
        deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")

        preview = doc_client.begin_analyze_document("prebuilt-document", content).result()
        source_language = _detect_language(preview.content if preview else "")

        result = extract_policy(
            doc_client=doc_client,
            openai_client=openai_client,
            deployment=deployment,
            content=content,
            source_language=source_language,
        )

        return func.HttpResponse(
            json.dumps(result, ensure_ascii=False),
            mimetype="application/json",
            status_code=200,
        )
    except Exception as exc:
        return func.HttpResponse(str(exc), status_code=400)


@app.route(route="extract_policy_async")
def extract_policy_async(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Processing extract_policy_async request")
    try:
        content, _ = _parse_request_payload(req)
    except Exception as exc:
        return func.HttpResponse(str(exc), status_code=400)

    job_id = str(uuid.uuid4())
    try:
        save_job(
            job_id,
            {
                "jobId": job_id,
                "status": "running",
                "created_at": datetime.utcnow().isoformat(),
            },
        )
    except Exception as exc:
        return func.HttpResponse(str(exc), status_code=500)

    import threading

    thread = threading.Thread(target=_run_extraction, args=(job_id, content), daemon=True)
    thread.start()

    status_url = req.url.replace("/extract_policy_async", f"/extract_policy/status/{job_id}")
    response = {"jobId": job_id, "pollingUrl": status_url}
    return func.HttpResponse(json.dumps(response), mimetype="application/json", status_code=202)


@app.route(route="extract_policy/status/{jobId}")
def extract_policy_status(req: func.HttpRequest) -> func.HttpResponse:
    job_id = req.route_params.get("jobId")
    if not job_id:
        return func.HttpResponse("jobId is required", status_code=400)

    try:
        job = load_job(job_id)
    except Exception as exc:
        return func.HttpResponse(str(exc), status_code=500)

    if not job:
        return func.HttpResponse("Job not found", status_code=404)

    return func.HttpResponse(json.dumps(job, ensure_ascii=False), mimetype="application/json")
