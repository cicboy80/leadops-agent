@description('Name of the Key Vault')
param name string

@description('Azure region')
param location string

@description('Environment name')
param environment string

@description('Array of secrets to create')
param secrets array = []

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: name
  location: location
  tags: {
    environment: environment
    project: 'leadops'
  }
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    enabledForDeployment: false
    enabledForDiskEncryption: false
    enabledForTemplateDeployment: true
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
    enablePurgeProtection: environment == 'prod' ? true : null
    networkAcls: {
      defaultAction: 'Allow'
      bypass: 'AzureServices'
    }
  }
}

resource keyVaultSecrets 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = [for secret in secrets: {
  name: secret.name
  parent: keyVault
  properties: {
    value: secret.value
  }
}]

output name string = keyVault.name
output id string = keyVault.id
output vaultUri string = keyVault.properties.vaultUri
