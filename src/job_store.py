import json
import os
from datetime import datetime
from typing import Any, Dict, Optional

from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob import ContentSettings

from src.azure_clients import get_blob_service_client


def _get_container():
    blob_service = get_blob_service_client()
    if not blob_service:
        raise ValueError("BLOB_CONNECTION_STRING is required for async job persistence")

    container_name = os.environ.get("JOBS_CONTAINER", "policy-jobs")
    container = blob_service.get_container_client(container_name)
    try:
        container.create_container()
    except Exception:
        pass
    return container


def save_job(job_id: str, data: Dict[str, Any]) -> None:
    container = _get_container()
    blob_client = container.get_blob_client(f"{job_id}.json")
    data.setdefault("updated_at", datetime.utcnow().isoformat())
    blob_client.upload_blob(
        json.dumps(data, ensure_ascii=False),
        overwrite=True,
        content_settings=ContentSettings(content_type="application/json"),
    )


def load_job(job_id: str) -> Optional[Dict[str, Any]]:
    container = _get_container()
    blob_client = container.get_blob_client(f"{job_id}.json")
    try:
        content = blob_client.download_blob().readall()
    except ResourceNotFoundError:
        return None
    return json.loads(content)
