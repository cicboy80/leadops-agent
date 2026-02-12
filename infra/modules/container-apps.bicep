@description('Name of the Container App')
param name string

@description('Azure region')
param location string

@description('Container Apps Environment resource ID')
param containerAppsEnvironmentId string

@description('Container image')
param containerImage string

@description('Target port for the container')
param targetPort int

@description('Environment name')
param environment string

@description('Minimum number of replicas')
param minReplicas int = 1

@description('Maximum number of replicas')
param maxReplicas int = 3

@description('CPU cores allocated to the container')
param cpu string = '0.5'

@description('Memory allocated to the container')
param memory string = '1Gi'

@description('ACR server')
param acrServer string

@description('Environment variables')
param environmentVariables array = []

@description('Secrets')
param secrets array = []

@description('Health probe path (null for no probe)')
param healthProbePath string?

resource containerApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: name
  location: location
  tags: {
    environment: environment
    project: 'leadops'
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    managedEnvironmentId: containerAppsEnvironmentId
    configuration: {
      ingress: {
        external: true
        targetPort: targetPort
        transport: 'auto'
        allowInsecure: false
      }
      registries: [
        {
          server: acrServer
          identity: 'system'
        }
      ]
      secrets: secrets
    }
    template: {
      containers: [
        {
          name: name
          image: containerImage
          resources: {
            cpu: json(cpu)
            memory: memory
          }
          env: environmentVariables
          probes: healthProbePath != null ? [
            {
              type: 'Liveness'
              httpGet: {
                path: healthProbePath
                port: targetPort
                scheme: 'HTTP'
              }
              initialDelaySeconds: 30
              periodSeconds: 10
              timeoutSeconds: 5
              failureThreshold: 3
            }
            {
              type: 'Readiness'
              httpGet: {
                path: healthProbePath
                port: targetPort
                scheme: 'HTTP'
              }
              initialDelaySeconds: 10
              periodSeconds: 5
              timeoutSeconds: 3
              failureThreshold: 3
            }
          ] : []
        }
      ]
      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas
        rules: [
          {
            name: 'http-scaling'
            http: {
              metadata: {
                concurrentRequests: '100'
              }
            }
          }
        ]
      }
    }
  }
}

output fqdn string = containerApp.properties.configuration.ingress.fqdn
output name string = containerApp.name
output id string = containerApp.id
output principalId string = containerApp.identity.principalId
