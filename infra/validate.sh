#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Validating Bicep templates...${NC}"
echo ""

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo -e "${RED}Error: Azure CLI is not installed${NC}"
    echo "Install from: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
fi

# Check if bicep is available
if ! az bicep version &> /dev/null; then
    echo -e "${YELLOW}Installing Bicep CLI...${NC}"
    az bicep install
fi

echo -e "${GREEN}✓ Azure CLI and Bicep are installed${NC}"
echo ""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Validate individual modules
echo -e "${YELLOW}Validating module files...${NC}"

modules=(
    "modules/log-analytics.bicep"
    "modules/container-apps-env.bicep"
    "modules/postgres.bicep"
    "modules/key-vault.bicep"
    "modules/container-apps.bicep"
)

for module in "${modules[@]}"; do
    echo -n "Validating $module... "
    if az bicep build --file "$SCRIPT_DIR/$module" --stdout > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
        echo -e "${RED}Error in $module:${NC}"
        az bicep build --file "$SCRIPT_DIR/$module" --stdout 2>&1 || true
        exit 1
    fi
done

echo ""

# Validate main template
echo -e "${YELLOW}Validating main template...${NC}"
echo -n "Validating main.bicep... "
if az bicep build --file "$SCRIPT_DIR/main.bicep" --stdout > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    echo -e "${RED}Error in main.bicep:${NC}"
    az bicep build --file "$SCRIPT_DIR/main.bicep" --stdout 2>&1 || true
    exit 1
fi

echo ""

# Validate parameter files
echo -e "${YELLOW}Validating parameter files...${NC}"

param_files=(
    "parameters.dev.json"
    "parameters.prod.json"
)

for param_file in "${param_files[@]}"; do
    echo -n "Validating $param_file... "
    if jq empty "$SCRIPT_DIR/$param_file" 2>/dev/null; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
        echo -e "${RED}Invalid JSON in $param_file${NC}"
        exit 1
    fi
done

echo ""

# Optional: Validate against Azure (requires authentication)
read -p "Do you want to validate against Azure subscription? (requires login) [y/N]: " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Validating against Azure...${NC}"

    SUBSCRIPTION_ID="5684e867-a54a-43a3-b185-55f48ba6ee24"
    RESOURCE_GROUP="hr-chatbot-rg"

    # Check if logged in
    if ! az account show &> /dev/null; then
        echo -e "${YELLOW}Not logged in to Azure. Please login...${NC}"
        az login
    fi

    # Set subscription
    az account set --subscription "$SUBSCRIPTION_ID"

    # Validate dev deployment
    echo -e "${YELLOW}Validating dev deployment...${NC}"
    if az deployment group validate \
        --resource-group "$RESOURCE_GROUP" \
        --template-file "$SCRIPT_DIR/main.bicep" \
        --parameters "$SCRIPT_DIR/parameters.dev.json" \
        --output none 2>&1; then
        echo -e "${GREEN}✓ Dev deployment validation passed${NC}"
    else
        echo -e "${RED}✗ Dev deployment validation failed${NC}"
        az deployment group validate \
            --resource-group "$RESOURCE_GROUP" \
            --template-file "$SCRIPT_DIR/main.bicep" \
            --parameters "$SCRIPT_DIR/parameters.dev.json" 2>&1 || true
        exit 1
    fi

    # Validate prod deployment
    echo -e "${YELLOW}Validating prod deployment...${NC}"
    if az deployment group validate \
        --resource-group "$RESOURCE_GROUP" \
        --template-file "$SCRIPT_DIR/main.bicep" \
        --parameters "$SCRIPT_DIR/parameters.prod.json" \
        --output none 2>&1; then
        echo -e "${GREEN}✓ Prod deployment validation passed${NC}"
    else
        echo -e "${RED}✗ Prod deployment validation failed${NC}"
        az deployment group validate \
            --resource-group "$RESOURCE_GROUP" \
            --template-file "$SCRIPT_DIR/main.bicep" \
            --parameters "$SCRIPT_DIR/parameters.prod.json" 2>&1 || true
        exit 1
    fi

    # Optional: Preview changes with what-if
    echo ""
    read -p "Do you want to preview deployment changes (what-if)? [y/N]: " -n 1 -r
    echo ""

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Running what-if analysis for dev environment...${NC}"
        az deployment group what-if \
            --resource-group "$RESOURCE_GROUP" \
            --template-file "$SCRIPT_DIR/main.bicep" \
            --parameters "$SCRIPT_DIR/parameters.dev.json"
    fi
fi

echo ""
echo -e "${GREEN}===============================================${NC}"
echo -e "${GREEN}All validations passed successfully!${NC}"
echo -e "${GREEN}===============================================${NC}"
echo ""
echo "Next steps:"
echo "  1. Review the templates in the infra/ directory"
echo "  2. Update parameter files with your secrets (Key Vault references)"
echo "  3. Run deployment: ./infra/deploy.sh dev"
echo ""
