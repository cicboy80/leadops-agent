#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SUBSCRIPTION_ID="5684e867-a54a-43a3-b185-55f48ba6ee24"
RESOURCE_GROUP="leadops-agent-rg"
ACR_NAME="hrchatbotregistry"
ACR_LOGIN_SERVER="${ACR_NAME}.azurecr.io"

# Check required parameters
if [ -z "$1" ]; then
  echo -e "${RED}Error: Environment parameter required (dev or prod)${NC}"
  echo "Usage: ./deploy.sh <environment>"
  exit 1
fi

ENVIRONMENT=$1

if [ "$ENVIRONMENT" != "dev" ] && [ "$ENVIRONMENT" != "prod" ]; then
  echo -e "${RED}Error: Environment must be 'dev' or 'prod'${NC}"
  exit 1
fi

echo -e "${GREEN}Starting deployment for environment: ${ENVIRONMENT}${NC}"

# Set Azure subscription
echo -e "${YELLOW}Setting Azure subscription...${NC}"
az account set --subscription "$SUBSCRIPTION_ID"

# Login to ACR
echo -e "${YELLOW}Logging into Azure Container Registry...${NC}"
az acr login --name "$ACR_NAME"

# Get project root directory (parent of infra)
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
echo -e "${YELLOW}Project root: ${PROJECT_ROOT}${NC}"

# Build and push backend image (context is project root for access to data/ directory)
echo -e "${YELLOW}Building backend Docker image for amd64...${NC}"
cd "$PROJECT_ROOT"
docker buildx build --platform linux/amd64 \
  -f Dockerfile.backend \
  -t "${ACR_LOGIN_SERVER}/leadops-backend:${ENVIRONMENT}-latest" \
  -t "${ACR_LOGIN_SERVER}/leadops-backend:${ENVIRONMENT}-$(git rev-parse --short HEAD 2>/dev/null || echo 'local')" \
  --push .

# Build and push frontend image (context is project root)
echo -e "${YELLOW}Building frontend Docker image for amd64...${NC}"
cd "$PROJECT_ROOT"
docker buildx build --platform linux/amd64 \
  -f Dockerfile.frontend \
  -t "${ACR_LOGIN_SERVER}/leadops-frontend:${ENVIRONMENT}-latest" \
  -t "${ACR_LOGIN_SERVER}/leadops-frontend:${ENVIRONMENT}-$(git rev-parse --short HEAD 2>/dev/null || echo 'local')" \
  --push .

# Get ACR admin credentials for container app image pulls
echo -e "${YELLOW}Fetching ACR admin credentials...${NC}"
ACR_USERNAME=$(az acr credential show --name "$ACR_NAME" --query username -o tsv)
ACR_PASSWORD=$(az acr credential show --name "$ACR_NAME" --query "passwords[0].value" -o tsv)

# Deploy Bicep infrastructure
echo -e "${YELLOW}Deploying Azure infrastructure with Bicep...${NC}"
cd "$PROJECT_ROOT/infra"

DEPLOYMENT_NAME="leadops-${ENVIRONMENT}-$(date +%Y%m%d-%H%M%S)"

az deployment group create \
  --name "$DEPLOYMENT_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --template-file main.bicep \
  --parameters "parameters.${ENVIRONMENT}.json" \
  --parameters acrUsername="$ACR_USERNAME" acrPassword="$ACR_PASSWORD" \
  --query 'properties.outputs' \
  --output json > deployment-outputs.json

echo -e "${GREEN}Infrastructure deployment completed!${NC}"
cat deployment-outputs.json

# Extract backend app name from outputs
BACKEND_APP_NAME=$(jq -r '.backendUrl.value' deployment-outputs.json | sed 's|https://||' | sed 's|\..*||')
BACKEND_URL=$(jq -r '.backendUrl.value' deployment-outputs.json)
FRONTEND_URL=$(jq -r '.frontendUrl.value' deployment-outputs.json)

echo -e "${YELLOW}Backend App Name: ${BACKEND_APP_NAME}${NC}"

# Note: Migrations already applied to Neon DB locally.
# For fresh deployments, run manually:
#   az containerapp exec --name $BACKEND_APP_NAME --resource-group $RESOURCE_GROUP \
#     --command "/bin/bash" --args "-c 'cd /app && alembic upgrade head'"
echo -e "${YELLOW}Skipping migrations (already applied to Neon). Run manually if needed.${NC}"

echo -e "${GREEN}===============================================${NC}"
echo -e "${GREEN}Deployment completed successfully!${NC}"
echo -e "${GREEN}===============================================${NC}"
echo -e "Backend URL:  ${BACKEND_URL}"
echo -e "Frontend URL: ${FRONTEND_URL}"
echo -e "${GREEN}===============================================${NC}"
