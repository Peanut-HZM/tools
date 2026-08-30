/**
 * Agent 市场 API 客户端
 *
 * P2-④ Agent 市场 / 分享
 * 对应后端 /api/v1/marketplace 系列接口。
 */

import { getAuthHeaders } from './authApi';
import { API_BASE_URL } from '../config/api';
import { authedFetch } from './http';

const MARKETPLACE_API_BASE_URL = `${API_BASE_URL}/marketplace`;

/** 市场目录条目（对应后端 list_marketplace_agents 返回） */
export interface MarketAgent {
  id: string;
  name: string;
  description: string;
  icon: string;
  icon_color: string;
  category: string;
  updated_at: string | null;
}

/** fork 返回（对应后端 fork_agent 返回） */
export interface ForkResult {
  id: string;
  name: string;
  visibility: string;
  owner_id: string;
}

/** 浏览 public Agent 目录 */
export async function listMarketAgents(
  skip = 0,
  limit = 50,
): Promise<{ records: MarketAgent[]; count: number }> {
  const response = await authedFetch(
    `${MARKETPLACE_API_BASE_URL}/agents?skip=${skip}&limit=${limit}`,
    { headers: getAuthHeaders() },
  );
  if (!response.ok) throw new Error('加载市场目录失败');
  return response.json();
}

/** fork public agent 到当前用户名下（private 副本） */
export async function forkAgent(agentId: string): Promise<ForkResult> {
  const response = await authedFetch(
    `${MARKETPLACE_API_BASE_URL}/agents/${encodeURIComponent(agentId)}/fork`,
    { method: 'POST', headers: getAuthHeaders() },
  );
  if (!response.ok) {
    const detail = await response
      .json()
      .catch(() => ({ detail: 'fork 失败' }))
      .then((b) => (b as { detail?: string }).detail)
      .catch(() => 'fork 失败');
    throw new Error(detail || 'fork 失败');
  }
  return response.json();
}

export const marketplaceApi = {
  list: listMarketAgents,
  fork: forkAgent,
};
