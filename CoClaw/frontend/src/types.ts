export type InstanceStatus = 'running' | 'stopped' | 'error';

export interface OpenClawInstance {
  id: string;
  containerId: string;
  name: string;
  status: InstanceStatus;
  endpoint?: string;
}

export interface Container {
  id: string;
  name: string;
  image: string;
  status: InstanceStatus;
  instances: OpenClawInstance[];
}
