# Microsoft 365 Copilot Agent Packaging Instructions

## Prerequisites
- Node.js and npm installed
- Microsoft 365 Developer account
- Azure Functions app deployed

## Steps

1. **Update Manifest**
   - Replace `your-function-app.azurewebsites.net` with your actual Azure Functions domain
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