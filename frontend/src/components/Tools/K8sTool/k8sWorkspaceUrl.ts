export const K8S_RESOURCE_TYPES = ['pods', 'workloads', 'nodes', 'events'] as const;

export type K8sResourceType = (typeof K8S_RESOURCE_TYPES)[number];

export interface K8sWorkspaceRouteState {
  connectionId: string | null;
  resourceType: K8sResourceType;
  namespaces: string[];
}

const DEFAULT_RESOURCE_TYPE: K8sResourceType = 'pods';

function normalizeNamespaces(value: string | null): string[] {
  if (!value) return [];

  return [...new Set(
    value
      .split(',')
      .map((namespace) => namespace.trim())
      .filter(Boolean)
  )];
}

function isResourceType(value: string | null): value is K8sResourceType {
  return !!value && K8S_RESOURCE_TYPES.includes(value as K8sResourceType);
}

export function parseK8sWorkspaceSearch(search: string): K8sWorkspaceRouteState {
  const params = new URLSearchParams(search);
  const connectionId = params.get('cluster')?.trim() || null;
  const resource = params.get('resource');

  return {
    connectionId,
    resourceType: isResourceType(resource) ? resource : DEFAULT_RESOURCE_TYPE,
    namespaces: normalizeNamespaces(params.get('namespaces')),
  };
}

export function serializeK8sWorkspaceSearch(
  state: K8sWorkspaceRouteState,
  currentSearch = '',
): string {
  const params = new URLSearchParams(currentSearch);
  params.delete('cluster');
  params.delete('resource');
  params.delete('namespaces');

  if (state.connectionId) params.set('cluster', state.connectionId);
  params.set('resource', state.resourceType);
  if (state.namespaces.length > 0) params.set('namespaces', state.namespaces.join(','));

  const value = params.toString();
  return value ? `?${value}` : '';
}
