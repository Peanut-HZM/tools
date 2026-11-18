import { API_BASE_URL } from '../config/api';
import { authedFetch } from './http';
import { getAuthHeaders } from './authApi';

const BASE_URL = `${API_BASE_URL}/agent-hub`;

// ---------------------------------------------------------------------------
// 类型（与后端 app/routes/agent_hub.py 对齐）
// ---------------------------------------------------------------------------

export interface AgentHubPreset {
  kind: string;
  name: string;
  app: string;
  category: string;
  needs_api_key: boolean;
  credential_source?: string;
  website_url?: string;
  base_url?: string;
  usage_api_key_hint?: string;
  notes?: string;
}

export interface AgentHubProvider {
  id: string;
  name: string;
  kind: string;
  app: string;
  base_url: string;
  api_key_masked: string;
  has_api_key: boolean;
  usage_api_key_masked: string;
  has_usage_api_key: boolean;
  usage_base_url: string;
  category: string;
  website_url: string;
  notes: string;
  enabled: boolean;
}

export interface QuotaTier {
  name: string;
  used: number;
  total: number;
  unit: string;
  utilization?: number;
  resets_at?: string;
}

export interface UsageResult {
  success: boolean;
  plan_name?: string;
  tiers?: QuotaTier[];
  balance?: { value: number; unit: string };
  error?: string;
  not_configured?: boolean;
  credential_expired?: boolean;
  queried_at?: string;
}

export interface AgentHubSubscription {
  id: string;
  provider_id: string;
  name: string;
  kind: string;
  credential_masked: string;
  has_credential: boolean;
  credential_source: string;
  agent_app: string;
  base_url: string;
  total_quota: number;
  used_quota: number;
  quota_unit: string;
  window_type: string;
  window_reset_at: string;
  enabled: boolean;
  last_queried_at: string;
  displayable: boolean;
  last_query: UsageResult | null;
}

export interface AgentHubAgent {
  agent: string;
  files: { path: string; exists: boolean }[];
  configured: boolean;
  current_provider_id: string;
  current_provider_name: string;
  switched_at: string;
}

export interface SwitchPreview {
  agent: string;
  files: { path: string; exists: boolean; backed_up: boolean }[];
  floor: Record<string, string>;
}

// ---------------------------------------------------------------------------
// API
// ---------------------------------------------------------------------------

async function handle<T>(resp: Response): Promise<T> {
  if (!resp.ok) {
    let detail = `HTTP ${resp.status}`;
    try {
      const body = await resp.json();
      detail = body.detail || body.error || detail;
    } catch { /* 保留 HTTP 状态码 */ }
    throw new Error(detail);
  }
  return resp.json() as Promise<T>;
}

const jsonInit = (method: string, body?: unknown) => ({
  method,
  headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
  body: body === undefined ? undefined : JSON.stringify(body),
});

export const agentHubApi = {
  listPresets: () =>
    authedFetch(`${BASE_URL}/presets`, { headers: getAuthHeaders() }).then(handle<{ presets: AgentHubPreset[]; agents: string[] }>),
  listProviders: () =>
    authedFetch(`${BASE_URL}/providers`, { headers: getAuthHeaders() }).then(handle<{ providers: AgentHubProvider[] }>),
  createProvider: (payload: Record<string, unknown>) =>
    authedFetch(`${BASE_URL}/providers`, jsonInit('POST', payload)).then(handle<{ provider: AgentHubProvider }>),
  updateProvider: (id: string, payload: Record<string, unknown>) =>
    authedFetch(`${BASE_URL}/providers/${id}`, jsonInit('PUT', payload)).then(handle<{ provider: AgentHubProvider }>),
  deleteProvider: (id: string) =>
    authedFetch(`${BASE_URL}/providers/${id}`, { method: 'DELETE', headers: getAuthHeaders() }).then(handle<{ ok: boolean }>),

  listSubscriptions: () =>
    authedFetch(`${BASE_URL}/subscriptions`, { headers: getAuthHeaders() }).then(handle<{ subscriptions: AgentHubSubscription[] }>),
  createSubscription: (payload: Record<string, unknown>) =>
    authedFetch(`${BASE_URL}/subscriptions`, jsonInit('POST', payload)).then(handle<{ subscription: AgentHubSubscription }>),
  updateSubscription: (id: string, payload: Record<string, unknown>) =>
    authedFetch(`${BASE_URL}/subscriptions/${id}`, jsonInit('PUT', payload)).then(handle<{ subscription: AgentHubSubscription }>),
  deleteSubscription: (id: string) =>
    authedFetch(`${BASE_URL}/subscriptions/${id}`, { method: 'DELETE', headers: getAuthHeaders() }).then(handle<{ ok: boolean }>),
  adjustQuota: (id: string, payload: Record<string, unknown>) =>
    authedFetch(`${BASE_URL}/subscriptions/${id}/quota`, jsonInit('PUT', payload)).then(handle<{ subscription: AgentHubSubscription }>),
  queryUsage: (id: string) =>
    authedFetch(`${BASE_URL}/subscriptions/${id}/usage`, { method: 'POST', headers: getAuthHeaders() }).then(handle<UsageResult>),
  queryAllUsage: () =>
    authedFetch(`${BASE_URL}/subscriptions/usage/all`, { headers: getAuthHeaders() }).then(handle<{ results: (UsageResult & { id: string; name: string })[] }>),

  listAgents: () =>
    authedFetch(`${BASE_URL}/agents`, { headers: getAuthHeaders() }).then(handle<{ agents: AgentHubAgent[]; supported: string[] }>),
  previewSwitch: (agent: string, providerId: string) =>
    authedFetch(`${BASE_URL}/agents/${agent}/config-preview?provider_id=${providerId}`,
      { headers: getAuthHeaders() })
      .then(handle<SwitchPreview>),
  switchAgent: (agent: string, providerId: string) =>
    authedFetch(`${BASE_URL}/agents/${agent}/switch`, jsonInit('POST', { provider_id: providerId }))
      .then(handle<{ ok: boolean; switch: { provider_name: string; written: string[] } }>),
  restoreAgent: (agent: string) =>
    authedFetch(`${BASE_URL}/agents/${agent}/restore`, { method: 'POST', headers: getAuthHeaders() })
      .then(handle<{ ok: boolean; restored: string[] }>),
};
