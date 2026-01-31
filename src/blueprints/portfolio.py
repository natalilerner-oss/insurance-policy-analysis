import json
import os
from datetime import datetime, timedelta

import azure.functions as func
from azure.storage.blob import ContentSettings, generate_blob_sas, BlobSasPermissions

from src.azure_clients import get_blob_service_client
from src.insurance_portfolio_schema import InsurancePortfolioRequest
from src.insurance_portfolio_generator import generate_insurance_portfolio
from src.blueprints.utils import assign_request_id, error_response, verify_jwt, logger, get_request_id

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
