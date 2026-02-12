@description('PostgreSQL server name')
param serverName string

@description('Azure region')
param location string

@description('Administrator username')
param administratorLogin string = 'leadopsadmin'

@description('Administrator password')
@secure()
param administratorPassword string

@description('Environment name')
param environment string

@description('PostgreSQL version')
param postgresVersion string = '16'

@description('Database name')
param databaseName string = 'leadops'

var skuName = environment == 'prod' ? 'Standard_B2s' : 'Standard_B1ms'
var tier = 'Burstable'
var storageSizeGB = environment == 'prod' ? 128 : 32
var backupRetentionDays = environment == 'prod' ? 7 : 7

resource postgresServer 'Microsoft.DBforPostgreSQL/flexibleServers@2023-03-01-preview' = {
  name: serverName
  location: location
  tags: {
    environment: environment
    project: 'leadops'
  }
  sku: {
    name: skuName
    tier: tier
  }
  properties: {
    administratorLogin: administratorLogin
    administratorLoginPassword: administratorPassword
    version: postgresVersion
    storage: {
      storageSizeGB: storageSizeGB
    }
    backup: {
      backupRetentionDays: backupRetentionDays
      geoRedundantBackup: 'Disabled'
    }
    highAvailability: {
      mode: 'Disabled'
    }
    availabilityZone: ''
  }
}

// Firewall rule to allow Azure services
resource firewallRule 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2023-03-01-preview' = {
  name: 'AllowAllAzureServicesAndResourcesWithinAzureIps'
  parent: postgresServer
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

// Create database
resource database 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2023-03-01-preview' = {
  name: databaseName
  parent: postgresServer
  properties: {
    charset: 'UTF8'
    collation: 'en_US.utf8'
  }
}

output fqdn string = postgresServer.properties.fullyQualifiedDomainName
output serverName string = postgresServer.name
output databaseName string = database.name
