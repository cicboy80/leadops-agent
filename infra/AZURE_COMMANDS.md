# Azure CLI Quick Reference

Common commands for managing the LeadOps Agent infrastructure.

## Setup & Login

```bash
# Login to Azure
az login

# Set subscription
az account set --subscription 5684e867-a54a-43a3-b185-55f48ba6ee24

# Verify current subscription
az account show
```

## Container Registry (ACR)

```bash
# Login to ACR
az acr login --name hrchatbotregistry

# List images
az acr repository list --name hrchatbotregistry --output table

# Show tags for an image
az acr repository show-tags \
  --name hrchatbotregistry \
  --repository leadops-backend \
  --output table

# Delete old images (cleanup)
az acr repository delete \
  --name hrchatbotregistry \
  --image leadops-backend:old-tag \
  --yes
```

## Container Apps

```bash
# List all container apps
az containerapp list \
  --resource-group hr-chatbot-rg \
  --output table

# Show container app details
az containerapp show \
  --name leadops-backend-dev \
  --resource-group hr-chatbot-rg

# Get container app URL
az containerapp show \
  --name leadops-backend-dev \
  --resource-group hr-chatbot-rg \
  --query properties.configuration.ingress.fqdn \
  --output tsv

# View container app logs (stream)
az containerapp logs show \
  --name leadops-backend-dev \
  --resource-group hr-chatbot-rg \
  --follow

# View recent logs (last 100 lines)
az containerapp logs show \
  --name leadops-backend-dev \
  --resource-group hr-chatbot-rg \
  --tail 100

# Execute command in container
az containerapp exec \
  --name leadops-backend-dev \
  --resource-group hr-chatbot-rg \
  --command "/bin/bash"

# Update environment variable
az containerapp update \
  --name leadops-backend-dev \
  --resource-group hr-chatbot-rg \
  --set-env-vars "NEW_VAR=value"

# Scale container app
az containerapp update \
  --name leadops-backend-dev \
  --resource-group hr-chatbot-rg \
  --min-replicas 2 \
  --max-replicas 5

# Restart container app (force new revision)
az containerapp revision restart \
  --name leadops-backend-dev \
  --resource-group hr-chatbot-rg
```

## PostgreSQL

```bash
# Show server details
az postgres flexible-server show \
  --resource-group hr-chatbot-rg \
  --name leadops-db-dev-<suffix>

# List databases
az postgres flexible-server db list \
  --resource-group hr-chatbot-rg \
  --server-name leadops-db-dev-<suffix> \
  --output table

# Connect to PostgreSQL
az postgres flexible-server connect \
  --name leadops-db-dev-<suffix> \
  --admin-user leadopsadmin \
  --database-name leadops

# Execute SQL command
az postgres flexible-server execute \
  --name leadops-db-dev-<suffix> \
  --database-name leadops \
  --admin-user leadopsadmin \
  --querytext "SELECT * FROM leads LIMIT 10;"

# Show firewall rules
az postgres flexible-server firewall-rule list \
  --resource-group hr-chatbot-rg \
  --name leadops-db-dev-<suffix> \
  --output table

# Add firewall rule (for local development)
az postgres flexible-server firewall-rule create \
  --resource-group hr-chatbot-rg \
  --name leadops-db-dev-<suffix> \
  --rule-name AllowMyIP \
  --start-ip-address <your-ip> \
  --end-ip-address <your-ip>

# Show metrics
az monitor metrics list \
  --resource /subscriptions/.../providers/Microsoft.DBforPostgreSQL/flexibleServers/leadops-db-dev-<suffix> \
  --metric "cpu_percent" \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-01T23:59:59Z
```

## Key Vault

```bash
# List secrets
az keyvault secret list \
  --vault-name leadops-secrets \
  --output table

# Get secret value
az keyvault secret show \
  --vault-name leadops-secrets \
  --name postgres-admin-password \
  --query value \
  --output tsv

# Set/update secret
az keyvault secret set \
  --vault-name leadops-secrets \
  --name new-secret \
  --value "secret-value"

# Delete secret (soft delete)
az keyvault secret delete \
  --vault-name leadops-secrets \
  --name old-secret

# Recover deleted secret
az keyvault secret recover \
  --vault-name leadops-secrets \
  --name old-secret
```

## Deployments

```bash
# List deployments
az deployment group list \
  --resource-group hr-chatbot-rg \
  --query "[?contains(name,'leadops')].{Name:name,State:properties.provisioningState,Timestamp:properties.timestamp}" \
  --output table

# Show deployment details
az deployment group show \
  --name leadops-dev-20240101-120000 \
  --resource-group hr-chatbot-rg

# Show deployment outputs
az deployment group show \
  --name leadops-dev-20240101-120000 \
  --resource-group hr-chatbot-rg \
  --query properties.outputs

# Validate template (dry-run)
az deployment group validate \
  --resource-group hr-chatbot-rg \
  --template-file infra/main.bicep \
  --parameters infra/parameters.dev.json

# What-if deployment (preview changes)
az deployment group what-if \
  --resource-group hr-chatbot-rg \
  --template-file infra/main.bicep \
  --parameters infra/parameters.dev.json

# Create deployment
az deployment group create \
  --name leadops-dev-$(date +%Y%m%d-%H%M%S) \
  --resource-group hr-chatbot-rg \
  --template-file infra/main.bicep \
  --parameters infra/parameters.dev.json

# Cancel running deployment
az deployment group cancel \
  --name leadops-dev-20240101-120000 \
  --resource-group hr-chatbot-rg

# Delete deployment (doesn't delete resources)
az deployment group delete \
  --name leadops-dev-20240101-120000 \
  --resource-group hr-chatbot-rg
```

## Log Analytics

```bash
# Query logs
az monitor log-analytics query \
  --workspace <workspace-id> \
  --analytics-query "ContainerAppConsoleLogs_CL | where TimeGenerated > ago(1h) | limit 100"

# Query container app logs
az monitor log-analytics query \
  --workspace <workspace-id> \
  --analytics-query "ContainerAppConsoleLogs_CL | where ContainerAppName_s == 'leadops-backend-dev' | project TimeGenerated, Log_s | order by TimeGenerated desc | limit 50"

# Get workspace ID
az monitor log-analytics workspace show \
  --resource-group hr-chatbot-rg \
  --workspace-name leadops-logs-dev-<suffix> \
  --query customerId \
  --output tsv
```

## Resource Management

```bash
# List all resources in resource group
az resource list \
  --resource-group hr-chatbot-rg \
  --output table

# Show resource group details
az group show \
  --name hr-chatbot-rg

# List resource providers
az provider list --query "[?namespace=='Microsoft.App']" --output table

# Check resource limits
az vm list-usage \
  --location westeurope \
  --output table
```

## Role Assignments

```bash
# List role assignments for a resource
az role assignment list \
  --scope /subscriptions/.../resourceGroups/hr-chatbot-rg \
  --output table

# Grant ACR pull to container app
az role assignment create \
  --assignee <principal-id> \
  --role AcrPull \
  --scope /subscriptions/.../resourceGroups/hr-chatbot-rg/providers/Microsoft.ContainerRegistry/registries/hrchatbotregistry

# List all role definitions
az role definition list \
  --custom-role-only false \
  --query "[?contains(roleName,'Container')].{Name:roleName,Description:description}" \
  --output table
```

## Monitoring & Diagnostics

```bash
# Get container app metrics
az monitor metrics list \
  --resource /subscriptions/.../providers/Microsoft.App/containerApps/leadops-backend-dev \
  --metric "Requests" \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-01T23:59:59Z

# Enable diagnostic settings
az monitor diagnostic-settings create \
  --name containerapp-diagnostics \
  --resource /subscriptions/.../providers/Microsoft.App/containerApps/leadops-backend-dev \
  --workspace /subscriptions/.../resourceGroups/hr-chatbot-rg/providers/Microsoft.OperationalInsights/workspaces/leadops-logs-dev-<suffix> \
  --logs '[{"category": "ContainerAppConsoleLogs", "enabled": true}]' \
  --metrics '[{"category": "AllMetrics", "enabled": true}]'

# List diagnostic settings
az monitor diagnostic-settings list \
  --resource /subscriptions/.../providers/Microsoft.App/containerApps/leadops-backend-dev
```

## Troubleshooting

```bash
# Check container app health
az containerapp show \
  --name leadops-backend-dev \
  --resource-group hr-chatbot-rg \
  --query properties.runningStatus

# Get revision history
az containerapp revision list \
  --name leadops-backend-dev \
  --resource-group hr-chatbot-rg \
  --output table

# Describe a specific revision
az containerapp revision show \
  --name leadops-backend-dev--<revision> \
  --resource-group hr-chatbot-rg \
  --app leadops-backend-dev

# Check deployment errors
az deployment group show \
  --name leadops-dev-20240101-120000 \
  --resource-group hr-chatbot-rg \
  --query properties.error

# Test database connection from local machine
psql "host=leadops-db-dev-<suffix>.postgres.database.azure.com port=5432 dbname=leadops user=leadopsadmin sslmode=require"
```

## Cost Management

```bash
# Show cost analysis
az consumption usage list \
  --start-date 2024-01-01 \
  --end-date 2024-01-31 \
  --query "[?contains(instanceName,'leadops')]" \
  --output table

# Get cost forecast
az consumption forecast list \
  --start-date 2024-01-01 \
  --end-date 2024-01-31
```

## Cleanup

```bash
# Delete a specific container app
az containerapp delete \
  --name leadops-backend-dev \
  --resource-group hr-chatbot-rg \
  --yes

# Delete PostgreSQL server
az postgres flexible-server delete \
  --resource-group hr-chatbot-rg \
  --name leadops-db-dev-<suffix> \
  --yes

# Delete all leadops resources (be careful!)
az resource list \
  --resource-group hr-chatbot-rg \
  --query "[?contains(name,'leadops-dev')].id" \
  --output tsv | xargs -I {} az resource delete --ids {}
```

## Useful Aliases

Add these to your `~/.bashrc` or `~/.zshrc`:

```bash
alias az-login='az login && az account set --subscription 5684e867-a54a-43a3-b185-55f48ba6ee24'
alias az-acr-login='az acr login --name hrchatbotregistry'
alias logs-backend-dev='az containerapp logs show --name leadops-backend-dev --resource-group hr-chatbot-rg --follow'
alias logs-frontend-dev='az containerapp logs show --name leadops-frontend-dev --resource-group hr-chatbot-rg --follow'
alias deploy-dev='cd infra && bash deploy.sh dev'
alias deploy-prod='cd infra && bash deploy.sh prod'
```

## Environment Variables

Useful environment variables for scripts:

```bash
export AZURE_SUBSCRIPTION_ID="5684e867-a54a-43a3-b185-55f48ba6ee24"
export AZURE_RESOURCE_GROUP="hr-chatbot-rg"
export AZURE_ACR_NAME="hrchatbotregistry"
export AZURE_LOCATION="westeurope"
```
