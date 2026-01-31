import json
import logging
import os
import sys
import threading
import uuid
from typing import Any, Tuple

import azure.functions as func
import jwt
from jwt import InvalidTokenError
import psutil

# Config
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
JWT_SECRET = os.environ.get("JWT_SECRET")
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")

_request_ctx = threading.local()

class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = getattr(_request_ctx, "request_id", "N/A")
        return True

def setup_logger():
    logging.basicConfig(
        stream=sys.stdout,
        level=LOG_LEVEL,
        format="%(asctime)s [%(levelname)s] [insurance-func] [request_id=%(request_id)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger = logging.getLogger("insurance-func")
    logger.addFilter(RequestIdFilter())
    return logger

logger = setup_logger()

def assign_request_id(req: func.HttpRequest) -> None:
    _request_ctx.request_id = req.headers.get("X-Request-ID") or str(uuid.uuid4())

def get_request_id() -> str:
    return getattr(_request_ctx, "request_id", "N/A")

def verify_jwt(req: func.HttpRequest) -> Tuple[bool, Any]:
    if not JWT_SECRET:
        return True, "jwt_not_configured"
    auth_header = req.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return False, "missing_bearer_token"
    token = auth_header.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        logger.info("JWT validated for sub: %s", payload.get("sub"))
        return True, payload
    except InvalidTokenError as e:
        logger.warning("Invalid JWT: %s", str(e))
        return False, f"invalid_token: {e}"

def error_response(key: str, message: str, status: int = 400, *, details: Any = None) -> func.HttpResponse:
    payload = {"error": key, "message": message, "request_id": get_request_id()}
    if details is not None:
        payload["details"] = details
    return func.HttpResponse(
        body=json.dumps(payload, separators=(",", ":")),
        status_code=status,
        headers={"Content-Type": "application/json", "X-Request-ID": get_request_id()},
    )

try:
    import resource
except ImportError:
    resource = None

def get_memory_info():
    """Get current process memory usage in MB"""
    try:
        process = psutil.Process()
        mem_info = process.memory_info()
        return {
            "rss_mb": round(mem_info.rss / (1024 * 1024), 2),
            "vms_mb": round(mem_info.vms / (1024 * 1024), 2),
        }
    except (ImportError, AttributeError):
        if resource:
            try:
                usage = resource.getrusage(resource.RUSAGE_SELF)
                maxrss_mb = round(usage.ru_maxrss / 1024, 2) if sys.platform == 'darwin' else round(usage.ru_maxrss / 1024, 2)
                return {"maxrss_mb": maxrss_mb}
            except Exception:
                return {"error": "memory tracking unavailable"}
        return {"error": "psutil not found and resource module not available"}
    except Exception as e:
        return {"error": str(e)}
