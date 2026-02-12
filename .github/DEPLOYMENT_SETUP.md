# GitHub Actions Deployment Setup Guide

This guide walks you through setting up GitHub Actions for CI/CD with Azure.

## Prerequisites

- Azure subscription access
- GitHub repository admin access
- Azure CLI installed locally

## Step 1: Create Azure Service Principal

Create a service principal with federated credentials for GitHub Actions:

```bash
# Set variables
SUBSCRIPTION_ID="5684e867-a54a-43a3-b185-55f48ba6ee24"
RESOURCE_GROUP="hr-chatbot-rg"
APP_NAME="leadops-github-actions"
GITHUB_ORG="<your-github-org>"
GITHUB_REPO="<your-repo-name>"

# Create service principal
az ad sp create-for-rbac \
  --name "$APP_NAME" \
  --role contributor \
  --scopes /subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP \
  --sdk-auth

# Save the output - you'll need the clientId and tenantId
```

## Step 2: Configure Federated Credentials

Add federated credentials for GitHub Actions (recommended over secrets):

```bash
# Get the app ID
APP_ID=$(az ad sp list --display-name "$APP_NAME" --query "[0].appId" -o tsv)

# Add federated credential for main branch
az ad app federated-credential create \
  --id $APP_ID \
  --parameters '{
    "name": "leadops-main-branch",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:'"$GITHUB_ORG/$GITHUB_REPO"':ref:refs/heads/main",
    "audiences": ["api://AzureADTokenExchange"]
  }'

# Add federated credential for pull requests
az ad app federated-credential create \
  --id $APP_ID \
  --parameters '{
    "name": "leadops-pull-requests",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:'"$GITHUB_ORG/$GITHUB_REPO"':pull_request",
    "audiences": ["api://AzureADTokenExchange"]
  }'
```

## Step 3: Grant ACR Permissions

Grant the service principal permission to push to ACR:

```bash
ACR_NAME="hrchatbotregistry"
ACR_ID=$(az acr show --name $ACR_NAME --query id --output tsv)

az role assignment create \
  --assignee $APP_ID \
  --role AcrPush \
  --scope $ACR_ID
```

## Step 4: Create Key Vault for Secrets

Create a Key Vault to store deployment secrets:

```bash
# Create Key Vault (if not exists)
az keyvault create \
  --name leadops-secrets \
  --resource-group $RESOURCE_GROUP \
  --location westeurope \
  --enable-rbac-authorization true

# Grant service principal access to read secrets
VAULT_ID=$(az keyvault show --name leadops-secrets --query id --output tsv)

az role assignment create \
  --assignee $APP_ID \
  --role "Key Vault Secrets User" \
  --scope $VAULT_ID

# Add secrets
az keyvault secret set \
  --vault-name leadops-secrets \
  --name postgres-admin-password \
  --value "<secure-password>"

az keyvault secret set \
  --vault-name leadops-secrets \
  --name openai-api-key \
  --value "<your-openai-key>"

az keyvault secret set \
  --vault-name leadops-secrets \
  --name api-key \
  --value "<your-api-key>"
```

## Step 5: Configure GitHub Secrets

Add the following secrets to your GitHub repository:

1. Go to your repository → Settings → Secrets and variables → Actions
2. Click "New repository secret" and add:

**Required Secrets:**

- `AZURE_CLIENT_ID`: The client ID from step 1
- `AZURE_TENANT_ID`: The tenant ID from step 1

**Optional Secrets (if not using Key Vault references):**

- `POSTGRES_ADMIN_PASSWORD`: PostgreSQL admin password
- `OPENAI_API_KEY`: OpenAI API key
- `API_KEY`: Backend API key

```bash
# Get the values
az ad sp list --display-name "$APP_NAME" --query "[0].{clientId:appId,tenantId:appOwnerOrganizationId}"
```

## Step 6: Create GitHub Environments

1. Go to your repository → Settings → Environments
2. Create two environments:

### Development Environment (`dev`)

- No protection rules needed
- Auto-deploys on push to main

### Production Environment (`prod`)

- Add protection rules:
  - ✓ Required reviewers (add yourself or team)
  - ✓ Wait timer: 5 minutes (optional)
- Only deploys via manual workflow dispatch

## Step 7: Verify Parameter Files

Update the parameter files to reference your Key Vault:

**infra/parameters.dev.json** and **infra/parameters.prod.json** should reference:

```json
{
  "postgresAdminPassword": {
    "reference": {
      "keyVault": {
        "id": "/subscriptions/5684e867-a54a-43a3-b185-55f48ba6ee24/resourceGroups/hr-chatbot-rg/providers/Microsoft.KeyVault/vaults/leadops-secrets"
      },
      "secretName": "postgres-admin-password"
    }
  }
}
```

## Step 8: Test the Workflows

### Test CI Workflow

1. Create a new branch
2. Make a small change
3. Open a pull request
4. Verify CI workflow runs successfully

### Test Deploy Workflow

1. Merge PR to main
2. Workflow should automatically deploy to dev
3. Check Actions tab for deployment status
4. Verify deployment outputs

### Test Manual Production Deployment

1. Go to Actions → Deploy to Azure
2. Click "Run workflow"
3. Select environment: `prod`
4. Click "Run workflow"
5. Approve the deployment when prompted

## Workflow Details

### CI Workflow (ci.yml)

Triggers on: Pull requests to main/develop

**Backend Steps:**
- Checkout code
- Set up Python 3.11
- Install dependencies
- Lint with ruff
- Run pytest with coverage
- Upload coverage to Codecov (optional)

**Frontend Steps:**
- Checkout code
- Set up Node.js 20
- Install dependencies
- Lint with ESLint
- Build with Next.js
- Type-check with TypeScript

### Deploy Workflow (deploy.yml)

Triggers on:
- Push to main (deploys to dev)
- Manual workflow dispatch (choose environment)

**Steps:**
1. Determine target environment
2. Build and push Docker images (amd64)
3. Deploy Bicep infrastructure
4. Grant ACR pull permissions
5. Run database migrations
6. Create deployment summary

## Monitoring Deployments

### View Deployment Logs

```bash
# Azure CLI
az deployment group list \
  --resource-group hr-chatbot-rg \
  --query "[?contains(name,'leadops')].{Name:name,State:properties.provisioningState,Timestamp:properties.timestamp}" \
  --output table

# Check specific deployment
az deployment group show \
  --name <deployment-name> \
  --resource-group hr-chatbot-rg
```

### View Container App Logs

```bash
# Backend logs
az containerapp logs show \
  --name leadops-backend-dev \
  --resource-group hr-chatbot-rg \
  --follow

# Frontend logs
az containerapp logs show \
  --name leadops-frontend-dev \
  --resource-group hr-chatbot-rg \
  --follow
```

## Troubleshooting

### "AADSTS700016: Application not found in the directory"

- Verify the service principal exists
- Check AZURE_CLIENT_ID is correct
- Ensure federated credentials are set up for the correct repository

### "Authorization failed"

- Verify service principal has Contributor role on resource group
- Check service principal has AcrPush role on ACR
- Ensure Key Vault access policies are configured

### "Image pull failed"

- Verify images were pushed to ACR
- Check container app managed identity has AcrPull role
- Verify image tags match deployment parameters

### "Database migration failed"

- Check PostgreSQL firewall rules allow Azure services
- Verify database connection string is correct
- Try running migrations manually via az containerapp exec

## Security Best Practices

1. **Use Federated Credentials**: Avoid storing long-lived secrets in GitHub
2. **Environment Protection**: Require approvals for production deployments
3. **Least Privilege**: Grant minimum required permissions to service principal
4. **Rotate Secrets**: Regularly rotate database passwords and API keys
5. **Review Logs**: Monitor deployment logs for suspicious activity

## Next Steps

After successful deployment:

1. Set up Application Insights for monitoring
2. Configure alerts for container app failures
3. Set up Azure Monitor dashboards
4. Configure log retention policies
5. Set up automated backup verification

## Rollback Procedure

If a deployment fails or causes issues:

```bash
# List recent deployments
az deployment group list \
  --resource-group hr-chatbot-rg \
  --query "[?contains(name,'leadops')].{Name:name,State:properties.provisioningState}" \
  --output table

# Redeploy a previous version
az deployment group create \
  --name leadops-rollback-$(date +%Y%m%d-%H%M%S) \
  --resource-group hr-chatbot-rg \
  --template-file infra/main.bicep \
  --parameters infra/parameters.dev.json \
  --parameters backendImageTag=dev-<previous-commit-sha> \
  --parameters frontendImageTag=dev-<previous-commit-sha>
```

## Support

For issues with:
- **GitHub Actions**: Check repository Actions tab and workflow logs
- **Azure Resources**: Use Azure Portal → Resource Group → Deployments
- **Container Apps**: Check Container Apps → Logs and Metrics
- **Database**: Check PostgreSQL → Monitoring → Metrics
