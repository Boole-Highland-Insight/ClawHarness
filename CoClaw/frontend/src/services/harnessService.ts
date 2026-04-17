import type { Container } from '../types';

// Service boundary for backend/harness integration.
// UI only consumes typed data from this service.
export async function getDashboardData(): Promise<Container[]> {
  return [
    {
      id: 'ctr-001',
      name: 'openclaw-gateway',
      image: 'openclaw/gateway:latest',
      status: 'running',
      instances: [
        {
          id: 'inst-001',
          containerId: 'ctr-001',
          name: 'gateway-main',
          status: 'running',
          endpoint: 'http://localhost:8080'
        },
        {
          id: 'inst-002',
          containerId: 'ctr-001',
          name: 'gateway-shadow',
          status: 'stopped',
          endpoint: 'http://localhost:8081'
        }
      ]
    },
    {
      id: 'ctr-002',
      name: 'openclaw-worker',
      image: 'openclaw/worker:latest',
      status: 'error',
      instances: [
        {
          id: 'inst-003',
          containerId: 'ctr-002',
          name: 'worker-recovering',
          status: 'error'
        }
      ]
    }
  ];
}
