import json
import os
import uuid
from datetime import datetime, timezone

import azure.functions as func
from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob import ContentSettings

from src.azure_clients import get_blob_service_client, get_blob_config_status
from src.blueprints.utils import assign_request_id, error_response, verify_jwt, logger, get_request_id

bp = func.Blueprint()

SESSIONS_CONTAINER = "recent-sessions"
MAX_RECENT_SESSIONS = 20


def _get_sessions_container():
    blob_service = get_blob_service_client()
    if not blob_service:
        return None
    container_name = os.environ.get("SESSIONS_CONTAINER", SESSIONS_CONTAINER)
    container = blob_service.get_container_client(container_name)
    try:
        container.create_container()
    except Exception:
        pass
    return container


def _blob_unavailable_response():
    status = get_blob_config_status()
    details = {
        "configured": status.get("configured"),
        "missing": status.get("missing"),
        "required": "BLOB_CONNECTION_STRING (or AzureWebJobsStorage) or BLOB_ACCOUNT_URL + BLOB_SAS_TOKEN",
    }
    return error_response("blob_unavailable", "Blob storage not configured", 503, details=details)


@bp.route(route="sessions", methods=["POST"])
def save_session(req: func.HttpRequest) -> func.HttpResponse:
    """Save a recent extraction session."""
    assign_request_id(req)
    logger.info("save_session route triggered")
    ok, detail = verify_jwt(req)
    if not ok:
        return error_response("unauthorized", "Authorization failed", 401, details=detail)

    if not get_blob_config_status().get("configured"):
        return _blob_unavailable_response()

    try:
        body = req.get_json()
    except ValueError as exc:
        return error_response("bad_request", "Invalid JSON payload: %s" % str(exc), 400)

    policies = body.get("policies")
    if not isinstance(policies, list) or not policies:
        return error_response("bad_request", "Request must include a non-empty policies array", 400)

    family_name = body.get("family_name", "")
    session_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    session_data = {
        "session_id": session_id,
        "family_name": family_name,
        "created_at": now,
        "policy_count": len(policies),
        "policies": policies,
    }

    container = _get_sessions_container()
    if not container:
        return _blob_unavailable_response()

    try:
        blob_client = container.get_blob_client(f"{session_id}.json")
        blob_client.upload_blob(
            json.dumps(session_data, ensure_ascii=False),
            overwrite=True,
            content_settings=ContentSettings(content_type="application/json"),
        )
    except Exception as exc:
        logger.error("Failed to save session: %s", exc)
        return error_response("failed_to_save", "Failed to save session", 500, details=str(exc))

    response = {
        "session_id": session_id,
        "created_at": now,
        "policy_count": len(policies),
        "request_id": get_request_id(),
    }
    return func.HttpResponse(
        json.dumps(response, ensure_ascii=False),
        status_code=201,
        mimetype="application/json",
        headers={"X-Request-ID": get_request_id()},
    )


@bp.route(route="sessions", methods=["GET"])
def list_sessions(req: func.HttpRequest) -> func.HttpResponse:
    """List recent extraction sessions."""
    assign_request_id(req)
    logger.info("list_sessions route triggered")
    ok, detail = verify_jwt(req)
    if not ok:
        return error_response("unauthorized", "Authorization failed", 401, details=detail)

    if not get_blob_config_status().get("configured"):
        return _blob_unavailable_response()

    container = _get_sessions_container()
    if not container:
        return _blob_unavailable_response()

    try:
        blobs = list(container.list_blobs())
    except Exception as exc:
        logger.error("Failed to list sessions: %s", exc)
        return error_response("failed_to_list", "Failed to list sessions", 500, details=str(exc))

    # Sort by last_modified descending and limit
    blobs.sort(key=lambda b: b.last_modified, reverse=True)
    blobs = blobs[:MAX_RECENT_SESSIONS]

    sessions = []
    for blob in blobs:
        try:
            blob_client = container.get_blob_client(blob.name)
            content = blob_client.download_blob().readall()
            data = json.loads(content)
            sessions.append({
                "session_id": data.get("session_id", blob.name.replace(".json", "")),
                "family_name": data.get("family_name", ""),
                "created_at": data.get("created_at", ""),
                "policy_count": data.get("policy_count", 0),
            })
        except Exception as exc:
            logger.warning("Failed to read session blob %s: %s", blob.name, exc)

    response = {
        "sessions": sessions,
        "total": len(sessions),
        "request_id": get_request_id(),
    }
    return func.HttpResponse(
        json.dumps(response, ensure_ascii=False),
        status_code=200,
        mimetype="application/json",
        headers={"X-Request-ID": get_request_id()},
    )


@bp.route(route="sessions/{sessionId}", methods=["GET"])
def get_session(req: func.HttpRequest) -> func.HttpResponse:
    """Get a specific session by ID."""
    assign_request_id(req)
    logger.info("get_session route triggered")
    ok, detail = verify_jwt(req)
    if not ok:
        return error_response("unauthorized", "Authorization failed", 401, details=detail)

    session_id = req.route_params.get("sessionId")
    if not session_id:
        return error_response("bad_request", "sessionId is required", 400)

    if not get_blob_config_status().get("configured"):
        return _blob_unavailable_response()

    container = _get_sessions_container()
    if not container:
        return _blob_unavailable_response()

    try:
        blob_client = container.get_blob_client(f"{session_id}.json")
        content = blob_client.download_blob().readall()
        data = json.loads(content)
    except ResourceNotFoundError:
        return error_response("not_found", "Session not found", 404)
    except Exception as exc:
        logger.error("Failed to get session: %s", exc)
        return error_response("failed_to_get", "Failed to get session", 500, details=str(exc))

    data["request_id"] = get_request_id()
    return func.HttpResponse(
        json.dumps(data, ensure_ascii=False),
        status_code=200,
        mimetype="application/json",
        headers={"X-Request-ID": get_request_id()},
    )
