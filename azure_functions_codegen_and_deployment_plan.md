# Azure Functions Code Generation and Deployment Plan

## 1. Architecture Definition

### Overview
This project is an **Insurance Policy Analysis** system built on **Azure Functions (Python v2 model)**. It provides APIs to extract data from insurance policy documents using Azure AI services and generate portfolio reports in Excel format.

### Components
*   **Function App**: Analysis and Reporting API.
    *   **Runtime**: Python 3.10+
    *   **Hosting Model**: Linux (Consumption or Premium).
*   **Triggers**:
    *   `extract_policy_sync` (HTTP POST): Synchronous policy extraction via Azure Document Intelligence & OpenAI.
    *   `generate_insurance_portfolio_endpoint` (HTTP POST): Generates Excel portfolio summaries.
    *   `translate_document` (HTTP POST): (Inferred) Async document translation.
    *   `job_status` (HTTP GET): (Inferred) Check status of async jobs.
*   **Data Stores**:
    *   **Azure Blob Storage**:
        *   Container `excel-reports`: Stores generated portfolio Excel files.
        *   Container `rfp-state` (default): Stores async job states (if configured).

### Key Integrations
*   **Azure Document Intelligence**: For OCR and layout analysis of policy PDF/Images.
*   **Azure OpenAI**: For semantic extraction of policy details using GPT models (e.g., GPT-4o).
*   **Azure Storage**: For persistent file storage and state management.

## 2. Technology Stack

*   **Programming Language**: Python (Recommended: 3.10 or 3.11)
*   **Framework**: Azure Functions Python Worker v2 (`function_app.py` style)
*   **Key Libraries**:
    *   `azure-functions`: Function app framework.
    *   `azure-storage-blob`: Blob storage interaction.
    *   `azure-ai-formrecognizer` / `azure-ai-documentintelligence`: Document analysis.
    *   `openai`: Azure OpenAI SDK.
    *   `pydantic`: Data validation and schema definition.
    *   `openpyxl`: Excel report generation.
    *   `jwt`: Authentication (optional).

## 3. Resource Requirements

### Azure Services
*   **Function App**:
    *   OS: Linux.
    *   Plan: **Consumption** (standard) or **Premium** (if timeouts > 5-10 mins are expected or VNET integration is needed). Given OCR/LLM latency, Premium or Container Apps hosting might be considered for stability, but Consumption is fine for initial setup with extended timeout configuration in `host.json`.
*   **Storage Account**: Standard General Purpose v2 (LRS/ZRS).
*   **Application Insights**: For monitoring and logging (essential for serverless).
*   **Azure AI Services**:
    *   **Azure OpenAI Resource**: Needs `gpt-4o` deployment.
    *   **Document Intelligence Resource**: Standard S0 tier (or free F0 for dev).

### Configuration (App Settings)
*   `AzureWebJobsStorage`: Connection string for the function app's internal storage.
*   `BLOB_CONNECTION_STRING` / `BLOB_ACCOUNT_URL`: For application data (reports/jobs).
*   `AZURE_OPENAI_ENDPOINT`: Endpoint for OpenAI.
*   `AZURE_OPENAI_API_KEY`: Key for OpenAI.
*   `AZURE_OPENAI_DEPLOYMENT`: Deployment name (e.g., "gpt-4o").
*   `DOCUMENT_INTELLIGENCE_ENDPOINT`: Endpoint for Form Recognizer.
*   `DOCUMENT_INTELLIGENCE_KEY`: Key for Form Recognizer.
*   `JWT_SECRET` (Optional): For securing endpoints.

## 4. Validation Strategy

*   **Local Validation**:
    *   Use **Azure Functions Core Tools** (`func start`) to run locally.
    *   Use `.vscode/launch.json` for debugging in VS Code.
    *   Verify all environment variables in `local.settings.json`.
*   **Testing**:
    *   **Unit Tests**: `pytest` for `src/` logic (schemas, Excel generation, utility functions).
    *   **Integration Tests**: Test actual HTTP endpoints against mocked or real AI services.
    *   **End-to-End**: Validate the full flow: Upload PDF -> Extract JSON -> Generate Excel.
*   **Deployment Verification**:
    *   Smoke test endpoints after deployment.
    *   Check Application Insights for errors.

## 5. Next Steps
1.  Verify local environment and dependencies.
2.  Consult Azure Best Practices for Python Code Generation & Deployment.
3.  Refine code or configuration if gaps are found.
4.  Deployment.
