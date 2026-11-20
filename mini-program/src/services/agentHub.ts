import { request } from './request';

/**
 * Agent Hub（Agent 订阅与供应商中心）API — 与 Web 端共用同一后端 /api/agent-hub。
 * 设计文档: docs/plans/2026-11-19-mini-program-agent-hub-design.md
 */

export interface AgentHubSubscription {
  id: string;
  provider_id: string;
  name: string;
  kind: string;
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
  last_query: {
    success: boolean;
    plan_name?: string;
    tiers?: { name: string; used: number; total: number; unit: string; resets_at?: string }[];
    balance?: { value: number; unit: string };
    error?: string;
    queried_at?: string;
  } | null;
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
  category: string;
  enabled: boolean;
  notes: string;
}

export interface AgentHubPreset {
  kind: string;
  name: string;
  app: string;
  category: string;
  needs_api_key: boolean;
  credential_source?: string;
  usage_api_key_hint?: string;
  notes?: string;
  base_url?: string;
  website_url?: string;
}

export interface AgentHubAgent {
  agent: string;
  configured: boolean;
  current_provider_id: string;
  current_provider_name: string;
  switched_at: string;
}

const BASE = '/agent-hub';

export const agentHubApi = {
  listSubscriptions: () =>
    request<{ subscriptions: AgentHubSubscription[] }>(`${BASE}/subscriptions`),

  listProviders: () =>
    request<{ providers: AgentHubProvider[] }>(`${BASE}/providers`),

  listPresets: () =>
    request<{ presets: AgentHubPreset[] }>(`${BASE}/presets`),

  createProvider: (payload: Record<string, unknown>) =>
    request<{ provider: AgentHubProvider }>(`${BASE}/providers`, {
      method: 'POST', data: payload,
    }),

  deleteProvider: (id: string) =>
    request<{ ok: boolean }>(`${BASE}/providers/${id}`, { method: 'DELETE' }),

  createSubscription: (payload: Record<string, unknown>) =>
    request<{ subscription: AgentHubSubscription }>(`${BASE}/subscriptions`, {
      method: 'POST', data: payload,
    }),

  deleteSubscription: (id: string) =>
    request<{ ok: boolean }>(`${BASE}/subscriptions/${id}`, { method: 'DELETE' }),

  adjustQuota: (id: string, payload: Record<string, unknown>) =>
    request<{ subscription: AgentHubSubscription }>(`${BASE}/subscriptions/${id}/quota`, {
      method: 'PUT', data: payload,
    }),

  queryUsage: (id: string) =>
    request<Record<string, unknown>>(`${BASE}/subscriptions/${id}/usage`, { method: 'POST' }),

  queryAllUsage: () =>
    request<{ results: (Record<string, unknown> & { id: string })[] }>(`${BASE}/subscriptions/usage/all`),

  listAgents: () =>
    request<{ agents: AgentHubAgent[] }>(`${BASE}/agents`),

  switchAgent: (agent: string, providerId: string) =>
    request<{ ok: boolean }>(`${BASE}/agents/${agent}/switch`, {
      method: 'POST', data: { provider_id: providerId },
    }),
};
