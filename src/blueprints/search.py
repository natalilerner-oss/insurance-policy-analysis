import json
import os
import re
from typing import Any, Dict, List, Optional

import azure.functions as func

from src.hebrew_utils import contains_hebrew
from src.blueprints.utils import assign_request_id, error_response, verify_jwt, logger, get_request_id

bp = func.Blueprint()

# External search endpoint (AskNice.FunctionApp integration)
EXTERNAL_SEARCH_URL = os.environ.get("EXTERNAL_SEARCH_URL", "")
EXTERNAL_SEARCH_KEY = os.environ.get("EXTERNAL_SEARCH_FUNCTION_KEY", "")


def _normalize(text: str) -> str:
    """Lowercase and strip diacritics for matching."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text.strip().lower())


def _matches_query(value: Any, query: str) -> bool:
    """Check if a value (string or nested dict/list) contains the query string."""
    if value is None:
        return False
    if isinstance(value, str):
        return query in _normalize(value)
    if isinstance(value, (int, float)):
        return query in str(value)
    if isinstance(value, dict):
        return any(_matches_query(v, query) for v in value.values())
    if isinstance(value, list):
        return any(_matches_query(item, query) for item in value)
    return False


def _match_policy(policy: Dict[str, Any], query: str, filters: Dict[str, str]) -> bool:
    """Check whether a policy matches the search query and filters."""
    nq = _normalize(query)

    # Text query matching – search across key fields
    if nq:
        searchable_fields = [
            policy.get("policy_number"),
            policy.get("carrier", {}).get("name") if isinstance(policy.get("carrier"), dict) else None,
            policy.get("carrier", {}).get("name_en") if isinstance(policy.get("carrier"), dict) else None,
            policy.get("policyholder", {}).get("name") if isinstance(policy.get("policyholder"), dict) else None,
            policy.get("policyholder", {}).get("name_en") if isinstance(policy.get("policyholder"), dict) else None,
            policy.get("_source_file"),
        ]

        # Also search coverages
        for cov in policy.get("coverages", []) or []:
            if isinstance(cov, dict):
                searchable_fields.extend([
                    cov.get("type"),
                    cov.get("type_en"),
                    cov.get("product_name"),
                ])

        # Also search exclusions
        for exc in policy.get("exclusions", []) or []:
            if isinstance(exc, dict):
                searchable_fields.extend(exc.get("conditions", []))
                searchable_fields.extend(exc.get("conditions_en", []))

        found = any(_normalize(str(f)) and nq in _normalize(str(f)) for f in searchable_fields if f)
        if not found:
            return False

    # Filter: carrier
    carrier_filter = _normalize(filters.get("carrier", ""))
    if carrier_filter:
        carrier = policy.get("carrier", {})
        carrier_name = _normalize(carrier.get("name", "")) if isinstance(carrier, dict) else ""
        carrier_name_en = _normalize(carrier.get("name_en", "")) if isinstance(carrier, dict) else ""
        if carrier_filter not in carrier_name and carrier_filter not in carrier_name_en:
            return False

    # Filter: coverage_type
    cov_filter = _normalize(filters.get("coverage_type", ""))
    if cov_filter:
        coverages = policy.get("coverages", []) or []
        cov_match = any(
            cov_filter in _normalize(c.get("type", "") or "") or cov_filter in _normalize(c.get("type_en", "") or "")
            for c in coverages if isinstance(c, dict)
        )
        if not cov_match:
            return False

    # Filter: date range (effective dates or coverage periods)
    date_from = filters.get("date_from", "")
    date_to = filters.get("date_to", "")
    if date_from or date_to:
        # Check against coverage period start dates and effective dates
        policy_dates = []
        eff = policy.get("effective_dates", {})
        if isinstance(eff, dict):
            for dk in ("print_date", "renewal_date"):
                if eff.get(dk):
                    policy_dates.append(str(eff[dk]))
        for cov in policy.get("coverages", []) or []:
            if isinstance(cov, dict):
                period = cov.get("period", {})
                if isinstance(period, dict) and period.get("start"):
                    policy_dates.append(str(period["start"]))

        if policy_dates:
            if date_from and all(d < date_from for d in policy_dates):
                return False
            if date_to and all(d > date_to for d in policy_dates):
                return False

    return True


def _build_result(policy: Dict[str, Any]) -> Dict[str, Any]:
    """Build a search result entry from a policy."""
    carrier = policy.get("carrier", {})
    carrier_name = carrier.get("name", "") if isinstance(carrier, dict) else ""
    holder = policy.get("policyholder", {})
    holder_name = holder.get("name", "") if isinstance(holder, dict) else ""

    coverage_types = []
    for cov in policy.get("coverages", []) or []:
        if isinstance(cov, dict):
            ct = cov.get("type") or cov.get("type_en") or cov.get("product_name")
            if ct and ct not in coverage_types:
                coverage_types.append(ct)

    return {
        "policy_number": policy.get("policy_number", ""),
        "carrier": carrier_name,
        "policyholder": holder_name,
        "total_monthly_premium": policy.get("total_monthly_premium"),
        "coverage_types": coverage_types,
        "source_file": policy.get("_source_file", ""),
    }


@bp.route(route="search", methods=["POST"])
def search_policies_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    """Search across loaded policies with text query and optional filters."""
    assign_request_id(req)
    logger.info("search route triggered")

    ok, detail = verify_jwt(req)
    if not ok:
        return error_response("unauthorized", "Authorization failed", 401, details=detail)

    try:
        body = req.get_json()
    except ValueError:
        return error_response("bad_request", "Invalid JSON payload", 400)

    query = body.get("query", "").strip()
    policies = body.get("policies", [])
    filters = {
        "carrier": body.get("carrier", ""),
        "coverage_type": body.get("coverage_type", ""),
        "date_from": body.get("date_from", ""),
        "date_to": body.get("date_to", ""),
    }

    if not policies:
        return func.HttpResponse(
            json.dumps({"results": [], "total": 0, "request_id": get_request_id()}, ensure_ascii=False),
            status_code=200,
            mimetype="application/json",
            headers={"X-Request-ID": get_request_id()},
        )

    results = []
    for policy in policies:
        if not isinstance(policy, dict):
            continue
        if _match_policy(policy, query, filters):
            results.append(_build_result(policy))

    response_data = {
        "results": results,
        "total": len(results),
        "query": query,
        "filters": {k: v for k, v in filters.items() if v},
        "request_id": get_request_id(),
    }

    return func.HttpResponse(
        json.dumps(response_data, ensure_ascii=False),
        status_code=200,
        mimetype="application/json",
        headers={"X-Request-ID": get_request_id()},
    )


@bp.route(route="Search", methods=["GET"])
def external_search_proxy(req: func.HttpRequest) -> func.HttpResponse:
    """Proxy to external AskNice.FunctionApp UserSearch endpoint.

    Forwards GET requests to the configured EXTERNAL_SEARCH_URL.
    """
    assign_request_id(req)
    logger.info("external Search proxy route triggered")

    if not EXTERNAL_SEARCH_URL:
        return error_response(
            "not_configured",
            "External search endpoint is not configured. Set EXTERNAL_SEARCH_URL.",
            503,
        )

    import requests as http_requests

    query = req.params.get("query", "")
    params = {"query": query}

    headers = {"Content-Type": "application/json"}
    if EXTERNAL_SEARCH_KEY:
        headers["x-functions-key"] = EXTERNAL_SEARCH_KEY

    try:
        resp = http_requests.get(EXTERNAL_SEARCH_URL, params=params, headers=headers, timeout=30)
        return func.HttpResponse(
            body=resp.text,
            status_code=resp.status_code,
            mimetype="application/json",
            headers={"X-Request-ID": get_request_id()},
        )
    except Exception as e:
        logger.error("External search proxy failed: %s", e, exc_info=True)
        return error_response("proxy_error", f"External search failed: {str(e)}", 502)
