# Frontend Deployment Guide

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