@description('Name of the Log Analytics workspace')
param name string

@description('Azure region')
param location string

@description('Environment name')
param environment string

@description('Data retention in days')
param retentionInDays int = 30

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: name
  location: location
  tags: {
    environment: environment
    project: 'leadops'
  }
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: retentionInDays
    features: {
      enableLogAccessUsingOnlyResourcePermissions: true
    }
  }
}

output workspaceId string = logAnalytics.id
output workspaceKey string = logAnalytics.listKeys().primarySharedKey
output workspaceCustomerId string = logAnalytics.properties.customerId
