targetScope = 'resourceGroup'

@description('Environment name (dev or prod)')
@allowed([
  'dev'
  'prod'
])
param environment string = 'dev'

@description('Azure region for all resources')
param location string = 'westeurope'

@description('External database connection string (e.g. Neon PostgreSQL)')
@secure()
param databaseUrl string

@description('OpenAI API key')
@secure()
param openaiApiKey string

@description('API key for backend authentication')
@secure()
param apiKey string

@description('ACR name (existing)')
param acrName string = 'hrchatbotregistry'

@description('Backend container image tag')
param backendImageTag string = 'latest'

@description('Frontend container image tag')
param frontendImageTag string = 'latest'

// Variables
var projectName = 'leadops'
var uniqueSuffix = uniqueString(resourceGroup().id)
var logAnalyticsName = '${projectName}-logs-${environment}-${uniqueSuffix}'
var containerAppsEnvName = '${projectName}-env-${environment}-${uniqueSuffix}'
var keyVaultName = '${projectName}-kv-${environment}-${substring(uniqueSuffix, 0, 5)}'
var backendAppName = '${projectName}-backend-${environment}'
var frontendAppName = '${projectName}-frontend-${environment}'

// Reference existing ACR
resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = {
  name: acrName
  scope: resourceGroup()
}

// 1. Log Analytics Workspace
module logAnalytics './modules/log-analytics.bicep' = {
  name: 'logAnalytics-deployment'
  params: {
    name: logAnalyticsName
    location: location
    environment: environment
  }
}

// 2. Container Apps Environment
module containerAppsEnv './modules/container-apps-env.bicep' = {
  name: 'containerAppsEnv-deployment'
  params: {
    name: containerAppsEnvName
    location: location
    logAnalyticsWorkspaceId: logAnalytics.outputs.workspaceId
    logAnalyticsWorkspaceKey: logAnalytics.outputs.workspaceKey
    environment: environment
  }
}

// 3. Key Vault (database hosted externally on Neon free tier)
module keyVault './modules/key-vault.bicep' = {
  name: 'keyVault-deployment'
  params: {
    name: keyVaultName
    location: location
    environment: environment
    secrets: [
      {
        name: 'database-connection-string'
        value: databaseUrl
      }
      {
        name: 'openai-api-key'
        value: openaiApiKey
      }
      {
        name: 'api-key'
        value: apiKey
      }
    ]
  }
}

// 4. Backend Container App
module backendApp './modules/container-apps.bicep' = {
  name: 'backendApp-deployment'
  params: {
    name: backendAppName
    location: location
    containerAppsEnvironmentId: containerAppsEnv.outputs.environmentId
    containerImage: '${acr.properties.loginServer}/leadops-backend:${backendImageTag}'
    targetPort: 8000
    environment: environment
    minReplicas: environment == 'prod' ? 2 : 0
    maxReplicas: environment == 'prod' ? 10 : 3
    acrServer: acr.properties.loginServer
    environmentVariables: [
      {
        name: 'ENVIRONMENT'
        value: environment
      }
      {
        name: 'DATABASE_URL'
        secretRef: 'database-connection-string'
      }
      {
        name: 'OPENAI_API_KEY'
        secretRef: 'openai-api-key'
      }
      {
        name: 'API_KEY'
        secretRef: 'api-key'
      }
      {
        name: 'LLM_PROVIDER'
        value: 'openai'
      }
      {
        name: 'AUTO_SEED_DEMO'
        value: 'true'
      }
      {
        name: 'CORS_ORIGINS'
        value: 'https://${frontendAppName}.${containerAppsEnv.outputs.defaultDomain}'
      }
    ]
    secrets: [
      {
        name: 'database-connection-string'
        value: databaseUrl
      }
      {
        name: 'openai-api-key'
        value: openaiApiKey
      }
      {
        name: 'api-key'
        value: apiKey
      }
    ]
    healthProbePath: '/api/v1/health'
  }
  dependsOn: [
    keyVault
  ]
}

// 5. Frontend Container App
module frontendApp './modules/container-apps.bicep' = {
  name: 'frontendApp-deployment'
  params: {
    name: frontendAppName
    location: location
    containerAppsEnvironmentId: containerAppsEnv.outputs.environmentId
    containerImage: '${acr.properties.loginServer}/leadops-frontend:${frontendImageTag}'
    targetPort: 3000
    environment: environment
    minReplicas: environment == 'prod' ? 2 : 0
    maxReplicas: environment == 'prod' ? 10 : 3
    acrServer: acr.properties.loginServer
    environmentVariables: [
      {
        name: 'NEXT_PUBLIC_API_URL'
        value: 'https://${backendAppName}.${containerAppsEnv.outputs.defaultDomain}'
      }
      {
        name: 'NEXT_PUBLIC_DEMO_MODE'
        value: 'true'
      }
      {
        name: 'NODE_ENV'
        value: 'production'
      }
    ]
    secrets: []
    healthProbePath: null
  }
}

// Outputs
output backendUrl string = 'https://${backendAppName}.${containerAppsEnv.outputs.defaultDomain}'
output frontendUrl string = 'https://${frontendAppName}.${containerAppsEnv.outputs.defaultDomain}'
output keyVaultName string = keyVault.outputs.name
