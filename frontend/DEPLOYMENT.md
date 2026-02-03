# Frontend Deployment Guide

This guide explains how to deploy the PolicyLens Streamlit frontend to Azure App Service.

## Prerequisites

- Azure account with an active subscription
- GitHub repository with appropriate permissions
- Azure CLI installed (for local testing)

## Azure App Service Setup

### 1. Create Azure App Service

1. **Navigate to Azure Portal** (https://portal.azure.com)

2. **Create a new Web App:**
   - Click "Create a resource" → "Web App"
   - Fill in the required details:
     - **Subscription**: Select your Azure subscription
     - **Resource Group**: Create new or select existing
     - **Name**: `policy-lens-frontend` (or your preferred name)
     - **Publish**: Code
     - **Runtime stack**: Python 3.11
     - **Operating System**: Linux
     - **Region**: Select your preferred region
     - **Pricing Plan**: Select appropriate plan (at least B1 Basic for production)

3. **Click "Review + Create"** and then "Create"

### 2. Configure Startup Command

After the Web App is created:

1. Navigate to your Web App in Azure Portal
2. Go to **Configuration** → **General settings**
3. Set the **Startup Command**:
   ```bash
   streamlit run app.py --server.port 8000 --server.address 0.0.0.0
   ```
4. Click **Save**

> **Note**: Azure App Service expects the application to listen on port 8000 by default. Streamlit's default port is 8501, so we override it.

### 3. Configure Environment Variables

In the Azure Portal, navigate to **Configuration** → **Application settings** and add:

| Name | Value | Description |
|------|-------|-------------|
| `BACKEND_URL` | `https://<your-backend-name>.azurewebsites.net/api` | URL to your Azure Function backend (replace with your actual backend URL) |
| `SCM_DO_BUILD_DURING_DEPLOYMENT` | `true` | Enable build during deployment |
| `WEBSITES_PORT` | `8000` | Port that Streamlit will listen on |

**Optional environment variables:**
- `STREAMLIT_SERVER_HEADLESS` = `true` (recommended for production)
- `STREAMLIT_SERVER_ENABLE_CORS` = `false`

Click **Save** after adding all variables.

### 4. Download Publish Profile

1. In your Azure Web App, click **Download publish profile** (top menu)
2. This downloads an XML file containing deployment credentials
3. Keep this file secure - it contains sensitive credentials

### 5. Add Publish Profile to GitHub Secrets

1. Open your GitHub repository
2. Go to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Name: `AZURE_WEBAPP_PUBLISH_PROFILE_FRONTEND`
5. Value: Open the downloaded publish profile XML file and paste its entire contents
6. Click **Add secret**

## GitHub Actions Workflow

The deployment workflow (`.github/workflows/deploy-frontend.yml`) will:

1. **Trigger** automatically when:
   - Changes are pushed to the `main` branch in the `frontend/` directory
   - Manually dispatched via GitHub Actions UI

2. **Build** the frontend:
   - Checkout code
   - Set up Python 3.11
   - Install dependencies from `frontend/requirements.txt`
   - Create a deployment package (ZIP)

3. **Deploy** to Azure:
   - Download the build artifact
   - Deploy to Azure App Service using the publish profile

## Manual Deployment

If you need to deploy manually without GitHub Actions:

### Option 1: Using Azure CLI

```bash
# Login to Azure
az login

# Navigate to frontend directory
cd frontend

# Create a deployment ZIP
zip -r ../frontend-deploy.zip . -x "*.pyc" -x "__pycache__/*" -x ".env"

# Deploy to Azure Web App
az webapp deployment source config-zip \
  --resource-group <your-resource-group> \
  --name policy-lens-frontend \
  --src ../frontend-deploy.zip
```

### Option 2: Using Azure Portal

1. Navigate to your Web App in Azure Portal
2. Go to **Deployment Center**
3. Choose **ZIP Deploy** or **FTP** and follow the instructions

### Option 3: Using VS Code

1. Install the "Azure App Service" extension
2. Right-click on the `frontend` folder
3. Select "Deploy to Web App"
4. Follow the prompts

## Verifying Deployment

After deployment:

1. **Check deployment logs** in Azure Portal:
   - Go to your Web App → **Deployment Center** → **Logs**

2. **Check application logs**:
   - Go to **Log stream** to see real-time logs
   - Or go to **Monitoring** → **App Service logs** to enable logging

3. **Access the application**:
   - Your app will be available at: `https://policy-lens-frontend.azurewebsites.net`
   - Wait 1-2 minutes for the app to fully start

4. **Test functionality**:
   - Verify the UI loads correctly
   - Test backend API connection
   - Upload a sample policy document
   - Generate an insurance portfolio Excel file
   - Verify the download functionality works

## Troubleshooting

### App doesn't start

1. **Check the startup command** is set correctly:
   ```bash
   streamlit run app.py --server.port 8000 --server.address 0.0.0.0
   ```

2. **Check application logs** in Azure Portal → Log stream

3. **Common issues:**
   - Port mismatch: Ensure `--server.port 8000` matches `WEBSITES_PORT`
   - Missing dependencies: Verify `requirements.txt` is complete
   - File not found: Ensure `app.py` exists in the root of deployment

### Backend connection fails

1. **Verify `BACKEND_URL`** environment variable is set correctly
2. **Check CORS settings** on the backend Azure Function
3. **Test the backend** directly using curl or Postman

### Deployment fails

1. **Check GitHub Actions logs** for build/deployment errors
2. **Verify the publish profile secret** is set correctly
3. **Check Azure service health** for any outages

### File download doesn't work

1. Verify the backend returns the correct `downloadUrl` key (not `download_url`)
2. Check that the backend URL is accessible from the frontend
3. Verify CORS is configured on the backend

## Local Development

To run the frontend locally:

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
pip install -r requirements.txt

# Create .env file with backend URL
echo "BACKEND_URL=http://localhost:7071/api" > .env

# Run Streamlit
streamlit run app.py
```

The app will be available at `http://localhost:8501`

## Production Best Practices

1. **Enable Always On**: In Azure Portal → Configuration → General settings
   - Prevents the app from being unloaded during idle periods

2. **Enable HTTPS Only**: In Azure Portal → TLS/SSL settings
   - Force HTTPS for security

3. **Configure scaling**: In Azure Portal → Scale up/Scale out
   - Set up autoscaling based on traffic

4. **Monitor performance**: In Azure Portal → Application Insights
   - Track errors, performance, and usage

5. **Set up custom domain**: In Azure Portal → Custom domains
   - Add your own domain name

## Security Considerations

1. **Never commit** the publish profile or `.env` files to Git
2. **Rotate credentials** periodically by downloading a new publish profile
3. **Use managed identities** when possible for Azure service connections
4. **Enable Application Insights** for security monitoring
5. **Set up rate limiting** if needed to prevent abuse

## Support

For issues or questions:
- Check Azure App Service documentation: https://learn.microsoft.com/azure/app-service/
- Check Streamlit documentation: https://docs.streamlit.io/
- Review GitHub Actions logs for deployment issues
- Contact the development team

## Updating the App

To deploy updates:

1. Make changes to files in the `frontend/` directory
2. Commit and push to the `main` branch
3. GitHub Actions will automatically deploy the changes
4. Monitor the deployment in the GitHub Actions tab

Manual trigger:
- Go to GitHub Actions → "Deploy Streamlit Frontend" → "Run workflow"
This document explains how to deploy the Streamlit frontend application.

## Prerequisites

1. Azure subscription
2. Azure CLI installed
3. GitHub repository with proper secrets configured

## Azure App Service Setup

### 1. Create Resource Group (if not exists)
```bash
az group create --name policy-lens-rg --location "East US"
```

### 2. Create App Service Plan
```bash
az appservice plan create \
  --name policy-lens-plan \
  --resource-group policy-lens-rg \
  --sku B1 \
  --is-linux
```

### 3. Create Web App
```bash
az webapp create \
  --resource-group policy-lens-rg \
  --plan policy-lens-plan \
  --name policy-lens-frontend \
  --runtime "PYTHON:3.11" \
  --deployment-local-git
```

### 4. Configure Startup Command
```bash
az webapp config set \
  --resource-group policy-lens-rg \
  --name policy-lens-frontend \
  --startup-file "streamlit run app.py --server.port 8000 --server.address 0.0.0.0"
```

### 5. Set Environment Variables
```bash
az webapp config appsettings set \
  --resource-group policy-lens-rg \
  --name policy-lens-frontend \
  --settings \
    BACKEND_URL="https://policy-extractor-30058.azurewebsites.net/api"
```

## GitHub Actions Setup

### Required Secrets

Add the following secrets to your GitHub repository:

1. `AZURE_WEBAPP_PUBLISH_PROFILE_FRONTEND`
   - Get this from Azure Portal > App Service > policy-lens-frontend > Get publish profile
   - Copy the entire XML content

### Workflow Triggers

The deployment workflow runs automatically on:
- Push to `main` branch when files in `frontend/` directory change
- Manual trigger via GitHub Actions

## Manual Deployment

If you need to deploy manually:

```bash
# Install Azure CLI and login
az login

# Deploy to Azure App Service
az webapp up \
  --name policy-lens-frontend \
  --resource-group policy-lens-rg \
  --runtime PYTHON:3.11 \
  --sku B1
```

## Troubleshooting

### Common Issues

1. **Port Configuration**: Ensure the startup command uses port 8000
2. **Environment Variables**: Verify BACKEND_URL is set correctly
3. **Dependencies**: Check that all packages in requirements.txt are compatible with Python 3.11

### Logs

View application logs:
```bash
az webapp log tail \
  --name policy-lens-frontend \
  --resource-group policy-lens-rg
```

### Health Check

After deployment, verify the app is running by visiting:
`https://policy-lens-frontend.azurewebsites.net`
