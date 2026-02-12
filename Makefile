.PHONY: dev test lint migrate seed deploy build

# Local development
dev:
	docker-compose up postgres -d
	cd backend && uvicorn app.main:app --reload --port 8000 &
	cd frontend && npm run dev

# Run all tests
test:
	cd backend && pytest tests/ -v --cov=app

# Lint backend + frontend
lint:
	cd backend && ruff check . && ruff format --check .
	cd frontend && npm run lint

# Format code
format:
	cd backend && ruff check --fix . && ruff format .

# Database migrations
migrate:
	cd backend && alembic upgrade head

migrate-new:
	cd backend && alembic revision --autogenerate -m "$(msg)"

# Seed demo data
seed:
	cd backend && python -m scripts.seed_demo_data

# Docker
build:
	docker-compose build

up:
	docker-compose up

down:
	docker-compose down

# Deploy to Azure
deploy-dev:
	cd infra && bash deploy.sh dev

deploy-prod:
	cd infra && bash deploy.sh prod

# Validate Bicep templates
bicep-validate:
	az bicep build --file infra/main.bicep
	@echo "Bicep validation successful"

# Preview infrastructure changes (what-if)
deploy-preview-dev:
	az deployment group what-if \
		--resource-group hr-chatbot-rg \
		--template-file infra/main.bicep \
		--parameters infra/parameters.dev.json

deploy-preview-prod:
	az deployment group what-if \
		--resource-group hr-chatbot-rg \
		--template-file infra/main.bicep \
		--parameters infra/parameters.prod.json

# Build Docker images locally
docker-build-backend:
	cd backend && docker buildx build --platform linux/amd64 -t hrchatbotregistry.azurecr.io/leadops-backend:dev-latest .

docker-build-frontend:
	cd frontend && docker buildx build --platform linux/amd64 -t hrchatbotregistry.azurecr.io/leadops-frontend:dev-latest .

docker-build-all: docker-build-backend docker-build-frontend

# Azure Container Apps management
logs-backend-dev:
	az containerapp logs show --name leadops-backend-dev --resource-group hr-chatbot-rg --follow

logs-frontend-dev:
	az containerapp logs show --name leadops-frontend-dev --resource-group hr-chatbot-rg --follow

logs-backend-prod:
	az containerapp logs show --name leadops-backend-prod --resource-group hr-chatbot-rg --follow

logs-frontend-prod:
	az containerapp logs show --name leadops-frontend-prod --resource-group hr-chatbot-rg --follow

# Database migrations on Azure
migrate-azure-dev:
	az containerapp exec \
		--name leadops-backend-dev \
		--resource-group hr-chatbot-rg \
		--command "/bin/bash" \
		--args "-c 'cd /app && alembic upgrade head'"

migrate-azure-prod:
	az containerapp exec \
		--name leadops-backend-prod \
		--resource-group hr-chatbot-rg \
		--command "/bin/bash" \
		--args "-c 'cd /app && alembic upgrade head'"
