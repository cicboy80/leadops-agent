# Infrastructure and CI/CD Files Created

This document lists all the files created for Azure deployment and CI/CD.

## Infrastructure (Bicep) Files

### Main Template
- **`/infra/main.bicep`** - Main orchestrator that deploys all Azure resources
  - Coordinates deployment of all modules
  - Defines parameters for environment, location, secrets
  - Outputs backend/frontend URLs

### Modules
- **`/infra/modules/log-analytics.bicep`** - Log Analytics workspace
  - 30-day retention
  - PerGB2018 pricing tier

- **`/infra/modules/container-apps-env.bicep`** - Container Apps Environment
  - Links to Log Analytics
  - Zone redundancy for prod

- **`/infra/modules/postgres.bicep`** - PostgreSQL Flexible Server
  - Version 16
  - B1ms SKU for dev, B2s for prod
  - Firewall rule for Azure services

- **`/infra/modules/key-vault.bicep`** - Key Vault
  - Soft delete enabled (7 days)
  - RBAC authorization
  - Purge protection for prod

- **`/infra/modules/container-apps.bicep`** - Reusable Container App module
  - Configurable replicas, CPU, memory
  - Health probes support
  - Managed identity for ACR pull

### Parameter Files
- **`/infra/parameters.dev.json`** - Development environment parameters
  - References Key Vault for secrets
  - Uses dev-latest image tags

- **`/infra/parameters.prod.json`** - Production environment parameters
  - References Key Vault for secrets
  - Uses prod-latest image tags

## Deployment Scripts

- **`/infra/deploy.sh`** - Main deployment script
  - Builds amd64 Docker images
  - Pushes to ACR
  - Deploys Bicep templates
  - Grants ACR permissions
  - Runs database migrations

- **`/infra/validate.sh`** - Validation script
  - Validates Bicep syntax
  - Validates parameter JSON
  - Optional Azure validation
  - Optional what-if preview

## GitHub Actions Workflows

- **`/.github/workflows/ci.yml`** - Continuous Integration
  - Runs on pull requests
  - Backend: ruff lint, pytest with coverage
  - Frontend: ESLint, Next.js build, type-check

- **`/.github/workflows/deploy.yml`** - Continuous Deployment
  - Runs on push to main or manual trigger
  - Builds and pushes Docker images
  - Deploys Bicep infrastructure
  - Grants permissions and runs migrations
  - Creates deployment summary

## Documentation

- **`/infra/README.md`** - Infrastructure documentation
  - Architecture overview
  - Deployment instructions
  - Configuration details
  - Troubleshooting guide
  - Cost optimization tips

- **`/.github/DEPLOYMENT_SETUP.md`** - GitHub Actions setup guide
  - Service principal creation
  - Federated credentials setup
  - GitHub secrets configuration
  - Environment setup
  - Workflow details

- **`/infra/AZURE_COMMANDS.md`** - Azure CLI command reference
  - Common operations for all services
  - Container Apps management
  - PostgreSQL operations
  - Monitoring and diagnostics
  - Troubleshooting commands

- **`/DEPLOYMENT.md`** - Main deployment guide
  - Quick start instructions
  - Architecture diagram
  - Environment configuration
  - Monitoring setup
  - Security best practices

## Supporting Files

- **`/backend/.dockerignore`** - Docker build exclusions for backend
  - Excludes Python cache, tests, local DBs

- **`/frontend/.dockerignore`** - Docker build exclusions for frontend
  - Excludes node_modules, .next, local files

## Updated Files

- **`/Makefile`** - Enhanced with infrastructure targets
  - `make deploy-dev` / `make deploy-prod`
  - `make bicep-validate`
  - `make deploy-preview-dev` / `make deploy-preview-prod`
  - `make docker-build-all`
  - `make logs-backend-dev` / `make logs-frontend-dev`
  - `make migrate-azure-dev` / `make migrate-azure-prod`

## File Structure

```
leadops_agent/
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                      # CI workflow
│   │   └── deploy.yml                  # Deployment workflow
│   └── DEPLOYMENT_SETUP.md             # GitHub Actions setup guide
│
├── infra/
│   ├── modules/
│   │   ├── log-analytics.bicep         # Log Analytics module
│   │   ├── container-apps-env.bicep    # Container Apps Env module
│   │   ├── postgres.bicep              # PostgreSQL module
│   │   ├── key-vault.bicep             # Key Vault module
│   │   └── container-apps.bicep        # Container App module
│   │
│   ├── main.bicep                      # Main orchestrator
│   ├── parameters.dev.json             # Dev parameters
│   ├── parameters.prod.json            # Prod parameters
│   ├── deploy.sh                       # Deployment script
│   ├── validate.sh                     # Validation script
│   ├── README.md                       # Infrastructure docs
│   ├── AZURE_COMMANDS.md               # Azure CLI reference
│   └── FILES_CREATED.md                # This file
│
├── backend/
│   └── .dockerignore                   # Docker exclusions
│
├── frontend/
│   └── .dockerignore                   # Docker exclusions
│
├── DEPLOYMENT.md                       # Main deployment guide
└── Makefile                            # Updated with infra targets
```

## Quick Reference

### Deploy to Azure

```bash
# Development
./infra/deploy.sh dev
# or
make deploy-dev

# Production
./infra/deploy.sh prod
# or
make deploy-prod
```

### Validate Templates

```bash
./infra/validate.sh
# or
make bicep-validate
```

### Preview Changes

```bash
make deploy-preview-dev
make deploy-preview-prod
```

### View Logs

```bash
make logs-backend-dev
make logs-frontend-dev
```

### Run Migrations

```bash
make migrate-azure-dev
make migrate-azure-prod
```

## Important Notes

1. **Make Scripts Executable**: After cloning, run:
   ```bash
   chmod +x infra/deploy.sh
   chmod +x infra/validate.sh
   ```

2. **Set Up Secrets**: Before first deployment, create Key Vault with secrets:
   - `postgres-admin-password`
   - `openai-api-key`
   - `api-key`

3. **GitHub Actions**: Follow `.github/DEPLOYMENT_SETUP.md` to configure:
   - Azure Service Principal
   - Federated Credentials
   - GitHub Secrets
   - GitHub Environments

4. **ACR Permissions**: The deployment script automatically grants ACR pull permissions to container apps using managed identities.

5. **Database Migrations**: Migrations are run automatically during deployment. If they fail, run manually using `make migrate-azure-dev`.

## Architecture Decisions

1. **Bicep over ARM Templates**: Cleaner syntax, better validation
2. **Modules**: Reusable, testable, maintainable
3. **Managed Identity**: No credential management for ACR access
4. **Key Vault**: Secure secret storage with RBAC
5. **Federated Credentials**: Passwordless GitHub Actions
6. **Zone Redundancy**: High availability for production
7. **Auto-scaling**: HTTP-based scaling rules
8. **Health Probes**: Backend liveness and readiness checks

## Cost Breakdown

### Development (~$50-70/month)
- Container Apps: ~$30-50
- PostgreSQL B1ms: ~$15
- Log Analytics: ~$5
- Key Vault: Free tier

### Production (~$140-250/month)
- Container Apps: ~$100-200 (with auto-scaling)
- PostgreSQL B2s: ~$30
- Log Analytics: ~$10-20
- Key Vault: Free tier

## Next Steps

1. Review all created files
2. Customize parameters for your environment
3. Set up Azure Key Vault with secrets
4. Run validation: `./infra/validate.sh`
5. Deploy to dev: `./infra/deploy.sh dev`
6. Set up GitHub Actions (see `.github/DEPLOYMENT_SETUP.md`)
7. Configure monitoring and alerts
8. Set up custom domains (optional)
9. Configure Application Insights (optional)

## Support Resources

- **Azure Container Apps**: https://learn.microsoft.com/azure/container-apps/
- **Bicep**: https://learn.microsoft.com/azure/azure-resource-manager/bicep/
- **GitHub Actions**: https://docs.github.com/actions
- **PostgreSQL**: https://learn.microsoft.com/azure/postgresql/
