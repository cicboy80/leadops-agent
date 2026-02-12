# LeadOps Agent - Azure Infrastructure

This directory contains Azure Bicep templates and deployment scripts for the LeadOps Agent application.

## Architecture Overview

The infrastructure deploys the following Azure resources:

- **Container Apps Environment** - Hosts both frontend and backend containers
- **Azure Container Apps** - Separate apps for backend (FastAPI) and frontend (Next.js)
- **PostgreSQL Flexible Server** - Database (version 16)
- **Log Analytics Workspace** - Centralized logging and monitoring
- **Key Vault** - Secure storage for secrets (optional, parameters can use direct secrets)
- **Azure Container Registry** - Pre-existing registry (hrchatbotregistry.azurecr.io)

## Prerequisites

1. **Azure CLI** - Install from https://docs.microsoft.com/en-us/cli/azure/install-azure-cli
2. **Docker** with buildx support for multi-platform builds
3. **Azure permissions** - Contributor role on the resource group
4. **Secrets** - Store secrets in a Key Vault named `leadops-secrets` with:
   - `postgres-admin-password`
   - `openai-api-key`
   - `api-key`

## File Structure

```
infra/
├── main.bicep                      # Main orchestrator template
├── modules/
│   ├── log-analytics.bicep         # Log Analytics workspace
│   ├── container-apps-env.bicep    # Container Apps environment
│   ├── postgres.bicep              # PostgreSQL Flexible Server
│   ├── key-vault.bicep             # Key Vault for secrets
│   └── container-apps.bicep        # Reusable Container App module
├── parameters.dev.json             # Development parameters
├── parameters.prod.json            # Production parameters
├── deploy.sh                       # Deployment script
└── README.md                       # This file
```

## Deployment

### Option 1: Using deploy.sh (Recommended)

The deployment script automates the entire process:

```bash
# Make script executable (if needed)
chmod +x deploy.sh

# Deploy to dev environment
./deploy.sh dev

# Deploy to production environment
./deploy.sh prod
```

The script will:
1. Build amd64 Docker images for backend and frontend
2. Push images to ACR with environment-specific tags
3. Deploy Bicep infrastructure
4. Grant ACR pull permissions to container apps
5. Run Alembic database migrations

### Option 2: Manual Deployment

```bash
# Set Azure subscription
az account set --subscription 5684e867-a54a-43a3-b185-55f48ba6ee24

# Login to ACR
az acr login --name hrchatbotregistry

# Build and push images
cd ../backend
docker buildx build --platform linux/amd64 \
  -t hrchatbotregistry.azurecr.io/leadops-backend:dev-latest \
  --push .

cd ../frontend
docker buildx build --platform linux/amd64 \
  -t hrchatbotregistry.azurecr.io/leadops-frontend:dev-latest \
  --push .

# Deploy infrastructure
cd ../infra
az deployment group create \
  --name leadops-dev-$(date +%Y%m%d-%H%M%S) \
  --resource-group hr-chatbot-rg \
  --template-file main.bicep \
  --parameters parameters.dev.json

# Grant ACR pull permissions (see deploy.sh for full commands)

# Run migrations
az containerapp exec \
  --name leadops-backend-dev \
  --resource-group hr-chatbot-rg \
  --command "/bin/bash" \
  --args "-c 'cd /app && alembic upgrade head'"
```

## Configuration

### Environment-Specific Settings

**Development (dev)**:
- PostgreSQL SKU: Standard_B1ms (Burstable, 1 vCore, 2 GiB RAM)
- Container replicas: 1 min, 3 max
- Zone redundancy: Disabled
- Storage: 32 GB

**Production (prod)**:
- PostgreSQL SKU: Standard_B2s (Burstable, 2 vCores, 4 GiB RAM)
- Container replicas: 2 min, 10 max
- Zone redundancy: Enabled
- Storage: 128 GB
- Purge protection: Enabled on Key Vault

### Container App Settings

Both backend and frontend use:
- CPU: 0.5 cores
- Memory: 1 GiB
- Auto-scaling based on HTTP concurrency (100 requests)

Backend includes:
- Liveness probe: /api/v1/health (30s initial delay)
- Readiness probe: /api/v1/health (10s initial delay)

### Managed Identity

Container Apps use system-assigned managed identities to pull images from ACR. The deployment script automatically grants the `AcrPull` role.

## GitHub Actions CI/CD

### CI Pipeline (.github/workflows/ci.yml)

Runs on pull requests to main/develop:
- Backend: Lint with ruff, run pytest with coverage
- Frontend: Lint with ESLint, build with Next.js, type-check

### Deploy Pipeline (.github/workflows/deploy.yml)

Runs on push to main or manual trigger:
- Build and push amd64 images to ACR
- Deploy Bicep infrastructure
- Grant ACR permissions
- Run database migrations

**Required GitHub Secrets**:
- `AZURE_CLIENT_ID` - Service principal client ID
- `AZURE_TENANT_ID` - Azure AD tenant ID

The service principal needs:
- Contributor role on resource group
- AcrPush role on ACR

### Setting Up GitHub Environments

Create GitHub environments for `dev` and `prod` with environment-specific protection rules:
- Production: Require manual approval
- Development: Auto-deploy on main branch

## Monitoring

View logs and metrics:

```bash
# View container logs
az containerapp logs show \
  --name leadops-backend-dev \
  --resource-group hr-chatbot-rg \
  --follow

# View metrics in Log Analytics
az monitor log-analytics query \
  --workspace <workspace-id> \
  --analytics-query "ContainerAppConsoleLogs_CL | where TimeGenerated > ago(1h)"
```

## Troubleshooting

### Container app not pulling images

Verify managed identity has ACR access:

```bash
# Check role assignments
az role assignment list \
  --assignee <principal-id> \
  --scope /subscriptions/.../resourceGroups/.../providers/Microsoft.ContainerRegistry/registries/hrchatbotregistry
```

### Database connection issues

Verify firewall rules allow Azure services:

```bash
az postgres flexible-server firewall-rule list \
  --resource-group hr-chatbot-rg \
  --name leadops-db-dev-<suffix>
```

### Migration failures

Run migrations manually:

```bash
az containerapp exec \
  --name leadops-backend-dev \
  --resource-group hr-chatbot-rg \
  --command "/bin/bash" \
  --args "-c 'cd /app && alembic upgrade head'"
```

## Cost Optimization

**Development environment estimated monthly costs** (West Europe):
- Container Apps: ~$30-50 (based on actual usage)
- PostgreSQL B1ms: ~$15
- Log Analytics: ~$5 (first 5GB free)
- **Total: ~$50-70/month**

**Production environment estimated monthly costs**:
- Container Apps: ~$100-200 (with auto-scaling)
- PostgreSQL B2s: ~$30
- Log Analytics: ~$10-20
- **Total: ~$140-250/month**

## Clean Up

To delete all resources:

```bash
# Delete specific deployment
az deployment group delete \
  --name <deployment-name> \
  --resource-group hr-chatbot-rg

# Or use Azure Portal to delete individual resources
# Keep ACR as it's shared across projects
```

## Security Notes

1. **Key Vault**: Secrets are stored in Key Vault with soft-delete enabled (7 days retention)
2. **Managed Identity**: Container apps use managed identities instead of service principal credentials
3. **Network**: PostgreSQL allows Azure services only (0.0.0.0/0 rule for Azure internal traffic)
4. **CORS**: Backend CORS is configured to only allow the frontend domain
5. **HTTPS**: All external traffic uses HTTPS (Container Apps ingress)

## Next Steps

1. Set up custom domains for container apps
2. Configure Application Insights for APM
3. Set up Azure Front Door for global distribution (production)
4. Configure backup retention policies
5. Set up alerts for critical metrics
