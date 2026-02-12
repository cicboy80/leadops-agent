@description('Name of the Container Apps Environment')
param name string

@description('Azure region')
param location string

@description('Log Analytics workspace resource ID')
param logAnalyticsWorkspaceId string

@description('Log Analytics workspace key')
@secure()
param logAnalyticsWorkspaceKey string

@description('Environment name')
param environment string

resource containerAppsEnvironment 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: name
  location: location
  tags: {
    environment: environment
    project: 'leadops'
  }
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: reference(logAnalyticsWorkspaceId, '2022-10-01').customerId
        sharedKey: logAnalyticsWorkspaceKey
      }
    }
    zoneRedundant: environment == 'prod' ? true : false
  }
}

output environmentId string = containerAppsEnvironment.id
output defaultDomain string = containerAppsEnvironment.properties.defaultDomain
