# LeadOps Agent - Deployment Guide

Complete guide for deploying the LeadOps Agent to Azure Container Apps.

## Overview

This project uses Azure Bicep for Infrastructure as Code (IaC) and GitHub Actions for CI/CD. The infrastructure is deployed to Azure Container Apps with PostgreSQL as the database.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Azure Container Apps                     │
│                                                              │
│  ┌──────────────────┐              ┌──────────────────┐    │
│  │   Frontend       │              │    Backend       │    │
│  │   (Next.js)      │─────────────▶│    (FastAPI)     │    │
│  │   Port: 3000     │              │    Port: 8000    │    │
│  └──────────────────┘              └──────────────────┘    │
│                                              │               │
└──────────────────────────────────────────────┼──────────────┘
                                               │
                                               ▼
                                    ┌──────────────────┐
                                    │   PostgreSQL     │
                                    │   Flexible Server│
                                    │   (Version 16)   │
                                    └──────────────────┘
```

## Infrastructure Components

### Core Services

1. **Container Apps Environment** - Managed environment for running containers
2. **Backend Container App** - FastAPI application
3. **Frontend Container App** - Next.js application
4. **PostgreSQL Flexible Server** - Database (B1ms for dev, B2s for prod)
5. **Log Analytics Workspace** - Centralized logging
6. **Key Vault** - Secret management

### Existing Resources

- **Azure Container Registry** - `hrchatbotregistry.azurecr.io` (already exists)
- **Resource Group** - `hr-chatbot-rg` (already exists)
- **Subscription** - `5684e867-a54a-43a3-b185-55f48ba6ee24`

## Quick Start

### Prerequisites

1. Azure CLI installed and configured
2. Docker Desktop with buildx support
3. Access to Azure subscription (Contributor role)
4. Git repository with GitHub Actions enabled

### Local Setup

```bash
# Clone repository
git clone <repository-url>
cd leadops_agent

# Set up backend
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Set up frontend
cd ../frontend
npm install

# Run locally
make dev
```

### First Deployment to Azure

1. **Set up Azure secrets**

```bash
# Create Key Vault for secrets
az keyvault create \
  --name leadops-secrets \
  --resource-group hr-chatbot-rg \
  --location westeurope

# Add secrets
az keyvault secret set --vault-name leadops-secrets \
  --name postgres-admin-password --value "<secure-password>"

az keyvault secret set --vault-name leadops-secrets \
  --name openai-api-key --value "<your-openai-key>"

az keyvault secret set --vault-name leadops-secrets \
  --name api-key --value "<your-api-key>"
```

2. **Make deploy script executable**

```bash
chmod +x infra/deploy.sh
```

3. **Deploy to dev environment**

```bash
# From project root
./infra/deploy.sh dev
```

4. **Access your applications**

The deployment script will output the URLs:
- Backend: `https://leadops-backend-dev.<region>.azurecontainerapps.io`
- Frontend: `https://leadops-frontend-dev.<region>.azurecontainerapps.io`

## GitHub Actions CI/CD

### Setup

Follow the detailed guide in `.github/DEPLOYMENT_SETUP.md` to:

1. Create Azure Service Principal with federated credentials
2. Add GitHub secrets (AZURE_CLIENT_ID, AZURE_TENANT_ID)
3. Configure GitHub environments (dev, prod)
4. Set up Key Vault references in parameter files

### Workflows

#### CI Workflow (Pull Requests)

Triggered on PR to main/develop:
- Backend: Lint with ruff, test with pytest
- Frontend: Lint with ESLint, build with Next.js

#### Deploy Workflow (Push to Main)

Triggered on push to main or manual dispatch:
- Build amd64 Docker images
- Push to Azure Container Registry
- Deploy Bicep infrastructure
- Grant ACR permissions
- Run database migrations

### Manual Deployment Triggers

```bash
# Via GitHub CLI
gh workflow run deploy.yml -f environment=dev
gh workflow run deploy.yml -f environment=prod

# Via GitHub UI
# Go to Actions → Deploy to Azure → Run workflow
```

## Deployment Commands

### Using Makefile

```bash
# Deploy to dev
make deploy-dev

# Deploy to prod
make deploy-prod

# Preview changes (what-if)
make deploy-preview-dev
make deploy-preview-prod

# Validate Bicep templates
make bicep-validate

# Build Docker images locally
make docker-build-all

# View logs
make logs-backend-dev
make logs-frontend-dev

# Run migrations on Azure
make migrate-azure-dev
make migrate-azure-prod
```

### Manual Deployment

```bash
# Login and set subscription
az login
az account set --subscription 5684e867-a54a-43a3-b185-55f48ba6ee24

# Run deployment script
cd infra
./deploy.sh dev  # or ./deploy.sh prod
```

## Environment Configuration

### Development (dev)

- **Purpose**: Testing and development
- **PostgreSQL**: Standard_B1ms (1 vCore, 2 GiB RAM)
- **Replicas**: 1 min, 3 max
- **Zone Redundancy**: Disabled
- **Cost**: ~$50-70/month

### Production (prod)

- **Purpose**: Live production workload
- **PostgreSQL**: Standard_B2s (2 vCores, 4 GiB RAM)
- **Replicas**: 2 min, 10 max
- **Zone Redundancy**: Enabled
- **Cost**: ~$140-250/month

## Database Migrations

### Local Development

```bash
# Create new migration
make migrate-new msg="add new table"

# Apply migrations
make migrate
```

### Azure Environment

```bash
# Dev environment
make migrate-azure-dev

# Production environment
make migrate-azure-prod

# Manual execution
az containerapp exec \
  --name leadops-backend-prod \
  --resource-group hr-chatbot-rg \
  --command "/bin/bash" \
  --args "-c 'cd /app && alembic upgrade head'"
```

## Monitoring

### View Logs

```bash
# Backend logs (dev)
az containerapp logs show \
  --name leadops-backend-dev \
  --resource-group hr-chatbot-rg \
  --follow

# Frontend logs (dev)
az containerapp logs show \
  --name leadops-frontend-dev \
  --resource-group hr-chatbot-rg \
  --follow
```

### Check Application Health

```bash
# Check backend health endpoint
curl https://leadops-backend-dev.<region>.azurecontainerapps.io/api/v1/health

# Check container app status
az containerapp show \
  --name leadops-backend-dev \
  --resource-group hr-chatbot-rg \
  --query properties.runningStatus
```

### Metrics & Analytics

- **Azure Portal**: Navigate to Container Apps → Metrics
- **Log Analytics**: Query logs using KQL
- **Application Insights**: (Optional) Set up for detailed APM

## Scaling

### Manual Scaling

```bash
# Scale backend
az containerapp update \
  --name leadops-backend-dev \
  --resource-group hr-chatbot-rg \
  --min-replicas 2 \
  --max-replicas 10
```

### Auto-scaling

Auto-scaling is configured based on:
- HTTP concurrency (100 concurrent requests)
- CPU utilization (future enhancement)
- Memory utilization (future enhancement)

## Troubleshooting

### Common Issues

#### 1. Image Pull Failures

```bash
# Check managed identity
az containerapp show \
  --name leadops-backend-dev \
  --resource-group hr-chatbot-rg \
  --query identity.principalId

# Grant ACR pull permission
ACR_ID=$(az acr show --name hrchatbotregistry --query id --output tsv)
az role assignment create \
  --assignee <principal-id> \
  --role AcrPull \
  --scope $ACR_ID
```

#### 2. Database Connection Issues

```bash
# Check firewall rules
az postgres flexible-server firewall-rule list \
  --resource-group hr-chatbot-rg \
  --name leadops-db-dev-<suffix>

# Test connection
az postgres flexible-server connect \
  --name leadops-db-dev-<suffix> \
  --admin-user leadopsadmin \
  --database-name leadops
```

#### 3. Migration Failures

```bash
# Connect to container
az containerapp exec \
  --name leadops-backend-dev \
  --resource-group hr-chatbot-rg \
  --command "/bin/bash"

# Inside container
cd /app
alembic current
alembic upgrade head
```

#### 4. Application Crashes

```bash
# View recent logs
az containerapp logs show \
  --name leadops-backend-dev \
  --resource-group hr-chatbot-rg \
  --tail 200

# Check revision status
az containerapp revision list \
  --name leadops-backend-dev \
  --resource-group hr-chatbot-rg \
  --output table
```

## Security Best Practices

1. **Secrets Management**
   - Store all secrets in Key Vault
   - Use managed identities for Azure resources
   - Rotate secrets regularly

2. **Network Security**
   - Container Apps use HTTPS by default
   - PostgreSQL allows Azure services only
   - Configure CORS for frontend domain only

3. **Access Control**
   - Use RBAC for resource access
   - Require MFA for Azure Portal access
   - Implement least privilege principle

4. **Monitoring**
   - Enable diagnostic settings
   - Set up alerts for failures
   - Review logs regularly

## Rollback Procedure

### Rollback to Previous Image

```bash
# Deploy with previous image tag
az deployment group create \
  --name leadops-rollback-$(date +%Y%m%d-%H%M%S) \
  --resource-group hr-chatbot-rg \
  --template-file infra/main.bicep \
  --parameters infra/parameters.dev.json \
  --parameters backendImageTag=dev-<previous-commit-sha>
```

### Rollback Database Migrations

```bash
# Connect to container
az containerapp exec \
  --name leadops-backend-dev \
  --resource-group hr-chatbot-rg \
  --command "/bin/bash"

# Downgrade migration
alembic downgrade -1
```

## Cost Optimization

### Development Tips

1. **Stop non-essential resources**: Scale to 0 replicas when not in use
2. **Use smaller SKUs**: B1ms for PostgreSQL is sufficient for dev
3. **Delete old images**: Clean up ACR regularly
4. **Review logs retention**: Adjust Log Analytics retention

### Production Optimization

1. **Right-size replicas**: Monitor usage and adjust min/max
2. **Enable autoscaling**: Let Azure scale based on demand
3. **Reserved capacity**: Consider reserved instances for predictable workloads
4. **Spot instances**: Use for non-critical workloads

## Maintenance

### Regular Tasks

- **Weekly**: Review logs and metrics
- **Monthly**: Check for security updates
- **Quarterly**: Review and optimize costs
- **Annually**: Rotate secrets and credentials

### Updates

```bash
# Update backend image
cd backend
docker buildx build --platform linux/amd64 \
  -t hrchatbotregistry.azurecr.io/leadops-backend:dev-latest \
  --push .

# Trigger new revision
az containerapp update \
  --name leadops-backend-dev \
  --resource-group hr-chatbot-rg \
  --image hrchatbotregistry.azurecr.io/leadops-backend:dev-latest
```

## Additional Resources

- **Infrastructure Details**: See `/infra/README.md`
- **GitHub Actions Setup**: See `/.github/DEPLOYMENT_SETUP.md`
- **Azure CLI Commands**: See `/infra/AZURE_COMMANDS.md`
- **Project Documentation**: See `/CLAUDE.md`

## Support

For issues or questions:

1. Check the troubleshooting section above
2. Review Azure Container Apps documentation
3. Check GitHub Actions workflow logs
4. Review deployment logs in Azure Portal

## Next Steps

After successful deployment:

1. Configure custom domains
2. Set up Application Insights
3. Configure backup policies
4. Set up monitoring alerts
5. Document runbook procedures
