# Azure Deployment Guide

## Prerequisites

- Azure CLI installed and authenticated
- Docker with buildx support
- Access to the `hr-chatbot-rg` resource group
- ACR: `hrchatbotregistry.azurecr.io`

## Architecture

```
┌─────────────────────────────────────────────┐
│          Azure Container Apps Environment    │
│                                              │
│  ┌──────────────┐    ┌──────────────┐       │
│  │   Frontend    │    │   Backend    │       │
│  │  (Next.js)   │───→│  (FastAPI)   │       │
│  │  Port 3000   │    │  Port 8000   │       │
│  └──────────────┘    └──────┬───────┘       │
│                              │               │
└──────────────────────────────┼───────────────┘
                               │
                    ┌──────────▼───────────┐
                    │  PostgreSQL Flexible  │
                    │       Server          │
                    └──────────────────────┘
```

## Step 1: Build Container Images

Images must be built for `linux/amd64` (Azure runs x86_64, local MacBooks are ARM64):

```bash
# Login to ACR
az acr login --name hrchatbotregistry

# Build and push backend
docker buildx build --platform linux/amd64 \
  -t hrchatbotregistry.azurecr.io/leadops-backend:latest \
  -f Dockerfile.backend --push .

# Build and push frontend
docker buildx build --platform linux/amd64 \
  -t hrchatbotregistry.azurecr.io/leadops-frontend:latest \
  -f Dockerfile.frontend --push .
```

## Step 2: Deploy Infrastructure

```bash
cd infra

# Dev environment
az deployment group create \
  --resource-group hr-chatbot-rg \
  --template-file main.bicep \
  --parameters @parameters.dev.json \
  --parameters postgresAdminPassword='<secure-password>' \
  --parameters openaiApiKey='<your-key>' \
  --parameters apiKey='<your-api-key>'

# Or prod environment
az deployment group create \
  --resource-group hr-chatbot-rg \
  --template-file main.bicep \
  --parameters @parameters.prod.json \
  --parameters postgresAdminPassword='<secure-password>' \
  --parameters openaiApiKey='<your-key>' \
  --parameters apiKey='<your-api-key>'
```

## Step 3: Run Database Migrations

```bash
# Get backend container app name
BACKEND_APP=$(az containerapp list -g hr-chatbot-rg --query "[?contains(name,'backend')].name" -o tsv)

# Run migrations via exec
az containerapp exec -n $BACKEND_APP -g hr-chatbot-rg --command "alembic upgrade head"
```

## Step 4: Seed Demo Data (Optional)

```bash
az containerapp exec -n $BACKEND_APP -g hr-chatbot-rg \
  --command "python -m scripts.seed_demo_data"
```

## Step 5: Verify

```bash
# Get frontend URL
az containerapp show -n leadops-frontend-dev -g hr-chatbot-rg \
  --query "properties.configuration.ingress.fqdn" -o tsv

# Get backend URL
az containerapp show -n leadops-backend-dev -g hr-chatbot-rg \
  --query "properties.configuration.ingress.fqdn" -o tsv

# Test health endpoint
curl https://<backend-fqdn>/api/v1/health
```

## Environment Variables

| Variable | Description | Where Set |
|----------|-------------|-----------|
| DATABASE_URL | PostgreSQL connection string | Key Vault → Container App env |
| OPENAI_API_KEY | OpenAI API key | Key Vault → Container App env |
| API_KEY | API authentication key | Key Vault → Container App env |
| CORS_ORIGINS | Frontend URL | Container App env |
| LLM_PROVIDER | openai or azure_openai | Container App env |
| EMAIL_MODE | mock (default) | Container App env |
| ENVIRONMENT | dev or production | Container App env |

## Automated Deployment

Push to `main` triggers `.github/workflows/deploy.yml`:
1. Builds amd64 Docker images
2. Pushes to ACR
3. Deploys Bicep infrastructure
4. Container Apps auto-pull new images

## Scaling

Container Apps configured with:
- **Dev**: 0-1 replicas (scale to zero when idle)
- **Prod**: 1-3 replicas with HTTP scaling rules

## Monitoring

- **Logs**: Azure Log Analytics workspace
- **Metrics**: Container Apps built-in metrics
- **Traces**: Structured logs with correlation IDs (X-Request-ID)

## Troubleshooting

```bash
# View backend logs
az containerapp logs show -n leadops-backend-dev -g hr-chatbot-rg --follow

# Check container app status
az containerapp show -n leadops-backend-dev -g hr-chatbot-rg --query "properties.runningStatus"

# Restart container
az containerapp revision restart -n leadops-backend-dev -g hr-chatbot-rg --revision <revision-name>
```
