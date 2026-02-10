import json
import os
from datetime import datetime, timedelta
import threading

import azure.functions as func
from azure.storage.blob import ContentSettings, generate_blob_sas, BlobSasPermissions

from src.azure_clients import get_blob_service_client
from src.insurance_portfolio_schema import InsurancePortfolioRequest
from src.insurance_portfolio_generator import generate_insurance_portfolio
from src.blueprints.utils import assign_request_id, error_response, verify_jwt, logger, get_request_id
from src.email_service import send_portfolio_email

bp = func.Blueprint()

@bp.route(route="generate_insurance_portfolio", methods=["POST"])
def generate_insurance_portfolio_endpoint(req: func.HttpRequest) -> func.HttpResponse:
    assign_request_id(req)
    logger.info("generate_insurance_portfolio route triggered")
    ok, detail = verify_jwt(req)
    if not ok:
        return error_response("unauthorized", "Authorization failed", 401, details=detail)

    try:
        body = req.get_json()
        data = InsurancePortfolioRequest(**body)
    except ValueError as e:
        return error_response("bad_request", f"Invalid request data: {str(e)}", 400)

    try:
        excel_bytes = generate_insurance_portfolio(data)

        # Calculate totals for summary (needed for both paths)
        total_premium = sum(
            sum(c.premium for c in p.coverages) if p.coverages else (p.premium or 0)
            for p in data.insurance_products
        )
        summary = {
            "family_name": data.family_name,
            "report_date": str(data.report_date),
            "products_count": len(data.insurance_products),
            "total_monthly_premium": float(total_premium),
            "family_members_count": len(data.family_members)
        }

        # Upload to blob storage
        filename = f"תיק_ביטוח_משפחת_{data.family_name}_{data.report_date}.xlsx"
        blob_service = get_blob_service_client()
        download_url = None

        if blob_service:
            try:
                container_name = os.environ.get("EXCEL_REPORTS_CONTAINER", "excel-reports")
                container = blob_service.get_container_client(container_name)
                try:
                    container.create_container()
                except Exception:
                    pass

                blob_name = f"{data.family_name}_{data.report_date}.xlsx"
                blob_client = container.get_blob_client(blob_name)
                blob_client.upload_blob(
                    excel_bytes.getvalue(),
                    overwrite=True,
                    content_settings=ContentSettings(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                )

                # Generate SAS URL
                sas = generate_blob_sas(
                    account_name=blob_client.account_name,
                    container_name=container_name,
                    blob_name=blob_name,
                    account_key=blob_service.credential.account_key,
                    permission=BlobSasPermissions(read=True),
                    expiry=datetime.utcnow() + timedelta(days=7),  # Longer expiry for reports
                )
                download_url = f"{blob_client.url}?{sas}"
            except Exception as e:
                logger.error("Failed to upload report to blob storage: %s", e)
                # Continue to direct download fallback

        if download_url:
            # Send email asynchronously if recipient_email is provided
            # Note: Using daemon thread for simplicity. For production with high reliability
            # requirements, consider using a proper message queue (e.g., Azure Storage Queue)
            # to ensure emails are not lost if the application shuts down.
            if data.recipient_email:
                def send_email_async():
                    try:
                        result = send_portfolio_email(
                            recipient_email=data.recipient_email,
                            family_name=data.family_name,
                            download_link=download_url,
                            total_premium=float(total_premium),
                            products_count=len(data.insurance_products),
                            report_date=str(data.report_date)
                        )
                        if result.get("success"):
                            logger.info(f"Email sent successfully to {data.recipient_email}")
                        else:
                            logger.warning(
                                f"Failed to send email to {data.recipient_email}: {result.get('error', 'Unknown error')}"
                            )
                    except Exception as e:
                        logger.error(f"Error in async email sending: {str(e)}", exc_info=True)
                
                # Start email sending in background thread
                email_thread = threading.Thread(target=send_email_async, daemon=True)
                email_thread.start()
            
            response_data = {
                "success": True,
                "filename": filename,
                "downloadUrl": download_url,
                "summary": summary,
                "request_id": get_request_id()
            }

            return func.HttpResponse(
                json.dumps(response_data, ensure_ascii=False),
                status_code=200,
                mimetype="application/json",
                headers={"X-Request-ID": get_request_id()}
            )
        else:
            # Fallback: Return file directly
            return func.HttpResponse(
                excel_bytes.getvalue(),
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                status_code=200,
                headers={
                    "Content-Disposition": f"attachment; filename={filename}",
                    "X-Request-ID": get_request_id()
                }
            )

    except Exception as e:
        logger.error("Failed to generate insurance portfolio: %s", e, exc_info=True)
        return error_response("failed_to_generate", f"Excel generation failed: {str(e)}", 500)

from typing import Dict, Any

@bp.route(route="compare_policies", methods=["POST"])
def compare_policies(req: func.HttpRequest) -> func.HttpResponse:
    assign_request_id(req)
    logger.info("compare_policies route triggered")
    ok, detail = verify_jwt(req)
    if not ok:
        return error_response("unauthorized", "Authorization failed", 401, details=detail)

    try:
        body = req.get_json()
    except ValueError as exc:
        return error_response("bad_request", f"Invalid JSON payload: {str(exc)}", 400)

    policies = body.get("policies") if isinstance(body, dict) else body
    if not isinstance(policies, list) or not policies:
        return error_response("bad_request", "Request must include a non-empty policies array", 400)

    def policy_label(policy: Dict[str, Any], index: int) -> str:
        policy_number = policy.get("policy_number") or f"policy_{index + 1}"
        carrier_obj = policy.get("carrier", {})
        carrier = carrier_obj.get("name") if isinstance(carrier_obj, dict) else None
        return f"{policy_number} ({carrier})" if carrier else policy_number

    def coverage_premium(coverage: Dict[str, Any]) -> float:
        premium = coverage.get("premium")
        if isinstance(premium, dict):
            return float(premium.get("final_monthly") or premium.get("base_monthly") or 0)
        if premium is None:
            return 0.0
        return float(premium)

    policy_labels = []
    summary = []
    coverage_index: Dict[str, Dict[str, float]] = {}

    for idx, policy in enumerate(policies):
        if not isinstance(policy, dict):
            continue
        label = policy_label(policy, idx)
        # Deduplicate labels by appending a counter suffix
        base_label = label
        counter = 2
        while label in policy_labels:
            label = f"{base_label} #{counter}"
            counter += 1
        policy_labels.append(label)
        total_premium = policy.get("total_monthly_premium") or 0
        # If total_monthly_premium not set, calculate from coverages
        if not total_premium and policy.get("coverages"):
            total_premium = sum(coverage_premium(c) for c in policy["coverages"] if isinstance(c, dict))
        carrier_obj = policy.get("carrier", {})
        summary.append(
            {
                "policy": label,
                "policy_number": policy.get("policy_number"),
                "carrier": carrier_obj.get("name") if isinstance(carrier_obj, dict) else None,
                "total_monthly_premium": float(total_premium or 0),
            }
        )

        for coverage in policy.get("coverages", []) or []:
            if not isinstance(coverage, dict):
                continue
            coverage_name = coverage.get("type") or coverage.get("product_name") or "Coverage"
            coverage_index.setdefault(coverage_name, {})[label] = coverage_premium(coverage)

    comparison_rows = []
    for coverage_name, by_policy in coverage_index.items():
        row = {"coverage": coverage_name}
        for label in policy_labels:
            row[label] = by_policy.get(label, 0)
        comparison_rows.append(row)

    response = {
        "policies": summary,
        "columns": ["coverage"] + policy_labels,
        "rows": comparison_rows,
        "request_id": get_request_id(),
    }
    return func.HttpResponse(
        json.dumps(response, ensure_ascii=False),
        status_code=200,
        mimetype="application/json",
        headers={"X-Request-ID": get_request_id()},
    )
