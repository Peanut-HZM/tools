/**
 * Harness Agent 记忆管理 API 客户端
 *
 * Phase 3-Plan-1B / Task 7
 * 参考 spec §6: docs/superpowers/specs/2026-08-29-agent-harness-phase3-plan1b-memory-vector-design.md
 *
 * 提供记忆列表 / 删除 / 搜索能力，对接后端
 * /api/v1/harness/agents/{agent_id}/memories 系列接口。
 */

import { getAuthHeaders } from './authApi';
import { API_BASE_URL } from '../config/api';
import { authedFetch } from './http';

const HARNESS_API_BASE_URL = `${API_BASE_URL}/harness`;

/** 单条记忆记录（对应后端 list_memories 返回的 records 元素） */
export interface MemoryEntry {
  key: string;
  value: unknown;
  importance: number;
  access_count: number;
  summary?: string | null;
  has_embedding: boolean;
}

/** 向量检索结果（对应后端 search_memories 返回的 records 元素） */
export interface MemorySearchResult {
  key: string;
  value: unknown;
  score: number;
  summary?: string | null;
}

/** 列出记忆返回结构 */
export interface MemoryListResponse {
  records: MemoryEntry[];
  count: number;
}

/** 向量检索返回结构 */
export interface MemorySearchResponse {
  records: MemorySearchResult[];
  count: number;
}

async function parseError(response: Response, fallback: string): Promise<never> {
  let detail = fallback;
  try {
    const body = await response.json();
    if (body && typeof body === 'object' && typeof body.detail === 'string') {
      detail = body.detail;
    }
  } catch {
    // 非 JSON 响应，使用 fallback
  }
  throw new Error(detail);
}

/** 列出当前用户对指定 Agent 的所有记忆 */
async function listMemories(agentId: string): Promise<MemoryListResponse> {
  const response = await authedFetch(
    `${HARNESS_API_BASE_URL}/agents/${encodeURIComponent(agentId)}/memories`,
    {
      method: 'GET',
      headers: getAuthHeaders(),
    },
  );
  if (!response.ok) await parseError(response, '加载记忆失败');
  return response.json();
}

/** 删除指定记忆条目（按 key） */
async function deleteMemory(agentId: string, key: string): Promise<void> {
  const response = await authedFetch(
    `${HARNESS_API_BASE_URL}/agents/${encodeURIComponent(agentId)}/memories/${encodeURIComponent(key)}`,
    {
      method: 'DELETE',
      headers: getAuthHeaders(),
    },
  );
  if (!response.ok && response.status !== 204) {
    await parseError(response, '删除记忆失败');
  }
}

/** 向量检索记忆（调试 / 预览） */
async function searchMemories(
  agentId: string,
  query: string,
  topK = 5,
): Promise<MemorySearchResponse> {
  const response = await authedFetch(
    `${HARNESS_API_BASE_URL}/agents/${encodeURIComponent(agentId)}/memories/search`,
    {
      method: 'POST',
      headers: {
        ...getAuthHeaders(),
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ query, top_k: topK }),
    },
  );
  if (!response.ok) await parseError(response, '记忆搜索失败');
  return response.json();
}

/**
 * 命名空间对象
 * 兼容以下用法：harnessMemoriesApi.list() / .delete() / .search()
 */
export const harnessMemoriesApi = {
  list: listMemories,
  delete: deleteMemory,
  search: searchMemories,
};
