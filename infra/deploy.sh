#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SUBSCRIPTION_ID="5684e867-a54a-43a3-b185-55f48ba6ee24"
RESOURCE_GROUP="hr-chatbot-rg"
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

# Build and push backend image
echo -e "${YELLOW}Building backend Docker image for amd64...${NC}"
cd "$PROJECT_ROOT/backend"
docker buildx build --platform linux/amd64 \
  -t "${ACR_LOGIN_SERVER}/leadops-backend:${ENVIRONMENT}-latest" \
  -t "${ACR_LOGIN_SERVER}/leadops-backend:${ENVIRONMENT}-$(git rev-parse --short HEAD 2>/dev/null || echo 'local')" \
  --push .

# Build and push frontend image
echo -e "${YELLOW}Building frontend Docker image for amd64...${NC}"
cd "$PROJECT_ROOT/frontend"
docker buildx build --platform linux/amd64 \
  -t "${ACR_LOGIN_SERVER}/leadops-frontend:${ENVIRONMENT}-latest" \
  -t "${ACR_LOGIN_SERVER}/leadops-frontend:${ENVIRONMENT}-$(git rev-parse --short HEAD 2>/dev/null || echo 'local')" \
  --push .

# Deploy Bicep infrastructure
echo -e "${YELLOW}Deploying Azure infrastructure with Bicep...${NC}"
cd "$PROJECT_ROOT/infra"

DEPLOYMENT_NAME="leadops-${ENVIRONMENT}-$(date +%Y%m%d-%H%M%S)"

az deployment group create \
  --name "$DEPLOYMENT_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --template-file main.bicep \
  --parameters "parameters.${ENVIRONMENT}.json" \
  --query 'properties.outputs' \
  --output json > deployment-outputs.json

echo -e "${GREEN}Infrastructure deployment completed!${NC}"
cat deployment-outputs.json

# Extract backend app name from outputs
BACKEND_APP_NAME=$(jq -r '.backendUrl.value' deployment-outputs.json | sed 's|https://||' | sed 's|\..*||')
BACKEND_URL=$(jq -r '.backendUrl.value' deployment-outputs.json)
FRONTEND_URL=$(jq -r '.frontendUrl.value' deployment-outputs.json)

echo -e "${YELLOW}Backend App Name: ${BACKEND_APP_NAME}${NC}"

# Grant ACR pull permissions to container apps
echo -e "${YELLOW}Granting ACR pull permissions to container apps...${NC}"

# Get backend app principal ID
BACKEND_PRINCIPAL_ID=$(az containerapp show \
  --name "$BACKEND_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query 'identity.principalId' \
  --output tsv)

# Get frontend app principal ID
FRONTEND_APP_NAME="leadops-frontend-${ENVIRONMENT}"
FRONTEND_PRINCIPAL_ID=$(az containerapp show \
  --name "$FRONTEND_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query 'identity.principalId' \
  --output tsv)

# Get ACR resource ID
ACR_ID=$(az acr show --name "$ACR_NAME" --query id --output tsv)

# Assign AcrPull role to backend
az role assignment create \
  --assignee "$BACKEND_PRINCIPAL_ID" \
  --role "AcrPull" \
  --scope "$ACR_ID" || echo "Backend role assignment may already exist"

# Assign AcrPull role to frontend
az role assignment create \
  --assignee "$FRONTEND_PRINCIPAL_ID" \
  --role "AcrPull" \
  --scope "$ACR_ID" || echo "Frontend role assignment may already exist"

# Run database migrations
echo -e "${YELLOW}Running Alembic database migrations...${NC}"

# Build migration command
MIGRATION_COMMAND="cd /app && alembic upgrade head"

# Execute migration in backend container
az containerapp exec \
  --name "$BACKEND_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --command "/bin/bash" \
  --args "-c \"$MIGRATION_COMMAND\"" || {
    echo -e "${YELLOW}Warning: Migration command failed or container exec not available${NC}"
    echo -e "${YELLOW}You may need to run migrations manually:${NC}"
    echo "  az containerapp exec --name $BACKEND_APP_NAME --resource-group $RESOURCE_GROUP --command \"/bin/bash\" --args \"-c 'cd /app && alembic upgrade head'\""
  }

echo -e "${GREEN}===============================================${NC}"
echo -e "${GREEN}Deployment completed successfully!${NC}"
echo -e "${GREEN}===============================================${NC}"
echo -e "Backend URL:  ${BACKEND_URL}"
echo -e "Frontend URL: ${FRONTEND_URL}"
echo -e "${GREEN}===============================================${NC}"
