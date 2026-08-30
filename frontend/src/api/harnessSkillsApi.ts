/**
 * Agent 技能（程序性记忆）API 客户端
 *
 * P2-② Memory procedural
 * 对应后端 /api/v1/harness/agents/{agent_id}/skills 系列接口。
 */

import { getAuthHeaders } from './authApi';
import { API_BASE_URL } from '../config/api';
import { authedFetch } from './http';

const HARNESS_API_BASE_URL = `${API_BASE_URL}/harness`;

/** 单条技能记录（对应后端 _serialize 返回） */
export interface SkillEntry {
  name: string;
  trigger: string;
  content: string;
  importance: number;
  use_count: number;
  is_enabled: boolean;
  updated_at: string | null;
}

/** 列出当前用户对指定 Agent 的全部技能 */
export async function listSkills(
  agentId: string,
): Promise<{ records: SkillEntry[]; count: number }> {
  const response = await authedFetch(
    `${HARNESS_API_BASE_URL}/agents/${encodeURIComponent(agentId)}/skills`,
    { headers: getAuthHeaders() },
  );
  if (!response.ok) throw new Error('加载技能失败');
  return response.json();
}

/** 创建/更新技能（按 name UPSERT） */
export async function createSkill(
  agentId: string,
  data: { name: string; trigger: string; content: string },
): Promise<SkillEntry> {
  const response = await authedFetch(
    `${HARNESS_API_BASE_URL}/agents/${encodeURIComponent(agentId)}/skills`,
    {
      method: 'POST',
      headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    },
  );
  if (!response.ok) throw new Error('保存技能失败');
  return response.json();
}

/** 删除指定技能（后端返回 204 No Content） */
export async function deleteSkill(agentId: string, name: string): Promise<void> {
  const response = await authedFetch(
    `${HARNESS_API_BASE_URL}/agents/${encodeURIComponent(agentId)}/skills/${encodeURIComponent(name)}`,
    { method: 'DELETE', headers: getAuthHeaders() },
  );
  if (!response.ok && response.status !== 204) throw new Error('删除技能失败');
}

/** 命名空间对象，与 harnessMemoriesApi 风格一致 */
export const harnessSkillsApi = {
  list: listSkills,
  create: createSkill,
  remove: deleteSkill,
};
