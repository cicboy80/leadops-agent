# Deployment Checklist

Use this checklist to ensure a smooth deployment to Azure.

## Pre-Deployment Checklist

### Local Environment Setup

- [ ] Azure CLI installed (`az --version`)
- [ ] Docker Desktop installed with buildx support
- [ ] Git configured with repository access
- [ ] Make utility available (or use direct scripts)
- [ ] Logged into Azure (`az login`)
- [ ] Correct subscription set (`az account show`)

### Azure Prerequisites

- [ ] Access to subscription `5684e867-a54a-43a3-b185-55f48ba6ee24`
- [ ] Contributor role on resource group `hr-chatbot-rg`
- [ ] Access to ACR `hrchatbotregistry.azurecr.io`
- [ ] AcrPush role on the container registry (for manual deployments)

### Secrets Setup

- [ ] Key Vault created or accessible (`leadops-secrets`)
- [ ] PostgreSQL admin password stored in Key Vault
  ```bash
  az keyvault secret set --vault-name leadops-secrets \
    --name postgres-admin-password --value "<secure-password>"
  ```
- [ ] OpenAI API key stored in Key Vault
  ```bash
  az keyvault secret set --vault-name leadops-secrets \
    --name openai-api-key --value "<your-key>"
  ```
- [ ] Backend API key stored in Key Vault
  ```bash
  az keyvault secret set --vault-name leadops-secrets \
    --name api-key --value "<your-key>"
  ```

### Code Preparation

- [ ] All changes committed to Git
- [ ] Backend tests passing (`cd backend && pytest`)
- [ ] Frontend builds successfully (`cd frontend && npm run build`)
- [ ] Linting passes (`make lint`)
- [ ] Alembic migrations up to date
- [ ] Docker builds succeed locally

### Infrastructure Files

- [ ] Review `/infra/main.bicep`
- [ ] Review parameter files (`parameters.dev.json`, `parameters.prod.json`)
- [ ] Update Key Vault references if needed
- [ ] Review module files in `/infra/modules/`
- [ ] Scripts are executable:
  ```bash
  chmod +x infra/deploy.sh
  chmod +x infra/validate.sh
  ```

## First-Time Deployment

### Validation

- [ ] Validate Bicep templates
  ```bash
  ./infra/validate.sh
  # or
  make bicep-validate
  ```
- [ ] Review validation output for errors
- [ ] Preview deployment changes
  ```bash
  make deploy-preview-dev
  ```

### Development Environment Deployment

- [ ] Deploy infrastructure
  ```bash
  ./infra/deploy.sh dev
  # or
  make deploy-dev
  ```
- [ ] Note deployment outputs (URLs)
- [ ] Verify backend URL is accessible
- [ ] Verify frontend URL is accessible
- [ ] Check health endpoint: `https://<backend-url>/api/v1/health`
- [ ] Review container logs
  ```bash
  make logs-backend-dev
  ```
- [ ] Verify database migrations ran successfully
- [ ] Test basic functionality (upload CSV, create lead)

### Troubleshooting (if needed)

- [ ] Check deployment logs in Azure Portal
- [ ] Verify ACR pull permissions granted
- [ ] Check PostgreSQL firewall rules
- [ ] Review container app logs for errors
- [ ] Test database connection
- [ ] Manually run migrations if failed:
  ```bash
  make migrate-azure-dev
  ```

## GitHub Actions Setup

### Service Principal

- [ ] Create service principal
  ```bash
  az ad sp create-for-rbac --name leadops-github-actions \
    --role contributor \
    --scopes /subscriptions/5684e867-a54a-43a3-b185-55f48ba6ee24/resourceGroups/hr-chatbot-rg
  ```
- [ ] Save client ID and tenant ID
- [ ] Create federated credential for main branch
- [ ] Create federated credential for pull requests
- [ ] Grant AcrPush role on container registry
- [ ] Grant Key Vault Secrets User role

### GitHub Configuration

- [ ] Add `AZURE_CLIENT_ID` to repository secrets
- [ ] Add `AZURE_TENANT_ID` to repository secrets
- [ ] Create `dev` environment in GitHub
- [ ] Create `prod` environment in GitHub
- [ ] Configure prod environment protection rules
- [ ] Add required reviewers for prod deployments

### Test Workflows

- [ ] Create a test branch
- [ ] Make a small change
- [ ] Open pull request
- [ ] Verify CI workflow runs successfully
- [ ] Merge to main
- [ ] Verify deploy workflow runs
- [ ] Check deployment succeeded in Azure
- [ ] Test deployed application

## Production Deployment

### Pre-Production Checklist

- [ ] Development environment fully tested
- [ ] All tests passing in CI
- [ ] Database migration strategy confirmed
- [ ] Backup strategy in place
- [ ] Monitoring configured
- [ ] Rollback plan documented

### Production Deployment Steps

- [ ] Review production parameters (`parameters.prod.json`)
- [ ] Preview production changes
  ```bash
  make deploy-preview-prod
  ```
- [ ] Deploy to production
  ```bash
  ./infra/deploy.sh prod
  # or via GitHub Actions with manual trigger
  ```
- [ ] Verify deployment outputs
- [ ] Test health endpoint
- [ ] Run smoke tests
- [ ] Monitor logs for first 15 minutes
- [ ] Verify auto-scaling works
- [ ] Test all critical functionality

### Post-Deployment

- [ ] Document deployment in change log
- [ ] Update team on new URLs
- [ ] Configure DNS (if using custom domains)
- [ ] Set up SSL certificates (if needed)
- [ ] Configure monitoring alerts
- [ ] Schedule first backup
- [ ] Document rollback procedure

## Monitoring Setup

### Azure Portal

- [ ] Add backend app to dashboard
- [ ] Add frontend app to dashboard
- [ ] Add PostgreSQL to dashboard
- [ ] Set up availability alerts
- [ ] Set up performance alerts
- [ ] Set up error rate alerts

### Log Analytics

- [ ] Create saved queries for common searches
- [ ] Set up log retention policy
- [ ] Configure diagnostic settings
- [ ] Test log queries

### Optional: Application Insights

- [ ] Create Application Insights resource
- [ ] Configure backend to send telemetry
- [ ] Set up availability tests
- [ ] Configure smart detection
- [ ] Create custom dashboards

## Security Hardening

### Access Control

- [ ] Review RBAC assignments
- [ ] Enable MFA for all users
- [ ] Configure conditional access policies
- [ ] Review Key Vault access policies
- [ ] Audit service principal permissions

### Network Security

- [ ] Review PostgreSQL firewall rules
- [ ] Configure CORS correctly
- [ ] Enable HTTPS only
- [ ] Review Container Apps ingress settings
- [ ] Consider private endpoints (advanced)

### Secrets Management

- [ ] Rotate all secrets post-deployment
- [ ] Set up secret rotation schedule
- [ ] Enable Key Vault audit logging
- [ ] Review who has Key Vault access
- [ ] Document secret rotation procedure

## Maintenance

### Regular Tasks

- [ ] Weekly: Review logs and metrics
- [ ] Weekly: Check for security updates
- [ ] Monthly: Review costs and optimize
- [ ] Monthly: Test backup restoration
- [ ] Quarterly: Rotate secrets
- [ ] Quarterly: Review and update documentation

### Updates

- [ ] Document update procedure
- [ ] Test updates in dev first
- [ ] Schedule maintenance windows
- [ ] Notify users of downtime
- [ ] Keep rollback images available

## Troubleshooting Reference

### Container App Issues

```bash
# Check status
az containerapp show --name <app-name> --resource-group hr-chatbot-rg

# View logs
az containerapp logs show --name <app-name> --resource-group hr-chatbot-rg --follow

# List revisions
az containerapp revision list --name <app-name> --resource-group hr-chatbot-rg

# Execute commands
az containerapp exec --name <app-name> --resource-group hr-chatbot-rg --command "/bin/bash"
```

### Database Issues

```bash
# Test connection
az postgres flexible-server connect --name <server-name> --admin-user leadopsadmin

# Show firewall rules
az postgres flexible-server firewall-rule list --name <server-name> --resource-group hr-chatbot-rg

# Run query
az postgres flexible-server execute --name <server-name> --database-name leadops \
  --admin-user leadopsadmin --querytext "SELECT COUNT(*) FROM leads;"
```

### Deployment Issues

```bash
# Show deployment
az deployment group show --name <deployment-name> --resource-group hr-chatbot-rg

# List deployments
az deployment group list --resource-group hr-chatbot-rg --output table

# What-if preview
az deployment group what-if --resource-group hr-chatbot-rg \
  --template-file infra/main.bicep --parameters infra/parameters.dev.json
```

## Common Issues and Solutions

### Issue: Image pull failed
**Solution**: Grant ACR pull permission to container app managed identity
```bash
ACR_ID=$(az acr show --name hrchatbotregistry --query id --output tsv)
PRINCIPAL_ID=$(az containerapp show --name <app-name> --resource-group hr-chatbot-rg --query identity.principalId -o tsv)
az role assignment create --assignee $PRINCIPAL_ID --role AcrPull --scope $ACR_ID
```

### Issue: Database connection failed
**Solution**: Check PostgreSQL firewall rules allow Azure services
```bash
az postgres flexible-server firewall-rule create \
  --resource-group hr-chatbot-rg \
  --name <server-name> \
  --rule-name AllowAllAzureServicesAndResourcesWithinAzureIps \
  --start-ip-address 0.0.0.0 --end-ip-address 0.0.0.0
```

### Issue: Migration failed
**Solution**: Run migrations manually
```bash
make migrate-azure-dev
# or
az containerapp exec --name leadops-backend-dev --resource-group hr-chatbot-rg \
  --command "/bin/bash" --args "-c 'cd /app && alembic upgrade head'"
```

### Issue: GitHub Actions failing
**Solution**: Check service principal permissions and secrets
```bash
# Verify service principal exists
az ad sp list --display-name leadops-github-actions

# Verify role assignments
az role assignment list --assignee <client-id>
```

## Success Criteria

### Development Environment
- [ ] Backend accessible and healthy
- [ ] Frontend loads without errors
- [ ] Can upload and process CSV
- [ ] Database queries work
- [ ] Logs are being collected
- [ ] Auto-scaling triggers correctly

### Production Environment
- [ ] All dev success criteria met
- [ ] High availability configured
- [ ] Monitoring and alerts active
- [ ] Backups scheduled
- [ ] Team has access
- [ ] Documentation complete

## Sign-Off

Deployment completed by: ________________

Date: ________________

Environment: [ ] Dev  [ ] Prod

Issues encountered: ________________

Notes: ________________
