# Microsoft 365 Copilot Agent Packaging Instructions

## Features

This Microsoft 365 Copilot agent provides comprehensive insurance policy management capabilities:

### Core Features
- **Policy Data Extraction**: Extract structured data from PDF/image insurance documents
- **Async Processing**: Handle large documents with job status tracking
- **Insurance Portfolio Excel Generation**: Create Hebrew RTL Excel reports for family insurance portfolios
- **Office Document Text Extraction**: Extract text from .pptx, .docx, .xlsx, .pdf files
- **Translation Services**: Translate text and documents between languages

### New: Insurance Portfolio Excel Reports
- Generate professional Excel reports with Hebrew RTL layout
- Coverage breakdowns for health insurance policies
- Automatic premium calculations and subtotals
- Secure download links with SAS tokens

## Prerequisites
- Node.js and npm installed
- Microsoft 365 Developer account
- Azure Functions app deployed

## Steps

1. **Update Manifest**
   - Replace `policy-extractor.azurewebsites.net` with your actual Azure Functions domain (if different)
   - Update developer info, privacy URL, etc.

2. **Create Icons**
   - Replace `color.png` (32x32) and `outline.png` (20x20) with actual PNG files
   - Use PNG format with transparent background

3. **Package the App**
   ```bash
   # Install Teams Toolkit CLI
   npm install -g @microsoft/teamsfx-cli

   # Package the app
   teamsfx package --manifest m365-agent/manifest.json --output app.zip
   ```

4. **Upload to Microsoft 365**
   - Go to Microsoft Teams Admin Center
   - Upload the app.zip file
   - Publish to your tenant

## Environment Variables
Set in your Azure Functions app:
- `AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT`
- `AZURE_DOCUMENT_INTELLIGENCE_KEY`
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_KEY`
- `AZURE_OPENAI_DEPLOYMENT=gpt-4.1`
- `BLOB_CONNECTION_STRING`
- `JOBS_CONTAINER=policy-jobs`
- `COMPLETED_JOBS_CONTAINER=policy-extractions`
- `EXCEL_REPORTS_CONTAINER=excel-reports` (for portfolio Excel files)
- `JWT_SECRET` (optional, for JWT authentication)
- `LOG_LEVEL=INFO`