/**
 * 图像生成管理 API 层
 * Task 12.1 — 后端 admin API 封装
 *
 * 15 个端点：
 * - 4 配额管理：list / grant / revoke / reset
 * - 3 Dify 配置：get / put / test
 * - 3 降级管理：get / put / reset
 * - 3 保留策略：get / put / trigger
 * - 1 统计：get
 */

import { API_BASE_URL } from '../config/api';
import { getAuthHeaders } from './authApi';
import { authedFetch } from './http';

const BASE_URL = `${API_BASE_URL}/admin/image-generation`;

/* ================================================================
 * 类型定义
 * ================================================================ */

export interface QuotaUser {
  user_id: string;
  daily_limit: number;
  daily_used: number;
  daily_remaining: number;
  monthly_limit: number;
  monthly_used: number;
  monthly_remaining: number;
  valid_from: string | null;
  valid_until: string | null;
  is_valid: boolean;
  granted_by: string;
  notes: string | null;
}

export interface QuotaUserListResponse {
  items: QuotaUser[];
  total: number;
  skip: number;
  limit: number;
}

export interface GrantQuotaRequest {
  daily_limit: number;
  monthly_limit: number;
  valid_from?: string | null;
  valid_until?: string | null;
  notes?: string | null;
}

export interface DifyConfig {
  api_url: string;
  is_api_key_set: boolean;
  workflow_text2img: string;
  workflow_img2img: string;
  workflow_inpaint: string;
  workflow_upload_edit: string;
  default_timeout: number;
}

export interface UpdateDifyConfigRequest {
  api_url?: string;
  app_api_key?: string;
  text2img_workflow_id?: string;
  img2img_workflow_id?: string;
  inpaint_workflow_id?: string;
  upload_edit_workflow_id?: string;
  timeout_seconds?: number;
}

export interface TestConnectionResponse {
  success: boolean;
  message: string;
}

export interface DegradationConfig {
  enabled: boolean;
  failure_threshold: number;
  degrade_duration_seconds: number;
}

export interface DegradationStatus extends DegradationConfig {
  is_degraded: boolean;
  failure_count: number;
  degraded_at: string | null;
}

export interface RetentionConfig {
  mode: 'keep_forever' | 'delete_after_n_days' | 'delete_if_unused_for_n_days';
  n_days: number;
  cleanup_cron: string;
}

export interface RetentionStatus extends RetentionConfig {
  total_files: number;
  total_size_mb: number;
}

export interface StatsResponse {
  days: number;
  total_calls: number;
  success_calls: number;
  failed_calls: number;
  success_rate: number;
  model_distribution: { model: string; count: number }[];
  daily_calls: { date: string; count: number }[];
}

/* ================================================================
 * 工具函数
 * ================================================================ */

async function readError(response: Response, fallback: string): Promise<Error> {
  const error = await response.json().catch(() => ({ detail: response.statusText }));
  const msg =
    typeof error.detail === 'string'
      ? error.detail
      : error.detail?.message || error.message || fallback;
  return new Error(msg);
}

/* ================================================================
 * 配额管理 API
 * ================================================================ */

/**
 * 有配额用户列表 — GET /admin/image-generation/users
 */
export async function listQuotaUsers(
  skip = 0,
  limit = 50,
  search?: string,
): Promise<QuotaUserListResponse> {
  const params = new URLSearchParams();
  params.set('skip', String(skip));
  params.set('limit', String(limit));
  if (search) params.set('search', search);

  const response = await authedFetch(`${BASE_URL}/users?${params.toString()}`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    throw await readError(response, '获取配额用户列表失败');
  }
  return response.json();
}

/**
 * 分配配额 — POST /admin/image-generation/users/{user_id}/grant
 */
export async function grantQuota(
  userId: string,
  data: GrantQuotaRequest,
): Promise<QuotaUser> {
  const response = await authedFetch(`${BASE_URL}/users/${userId}/grant`, {
    method: 'POST',
    headers: {
      ...getAuthHeaders(),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    throw await readError(response, '分配配额失败');
  }
  return response.json();
}

/**
 * 撤销配额 — DELETE /admin/image-generation/users/{user_id}/quota
 */
export async function revokeQuota(userId: string): Promise<{ success: boolean; user_id: string }> {
  const response = await authedFetch(`${BASE_URL}/users/${userId}/quota`, {
    method: 'DELETE',
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    throw await readError(response, '撤销配额失败');
  }
  return response.json();
}

/**
 * 重置计数器 — POST /admin/image-generation/users/{user_id}/reset
 */
export async function resetCounters(userId: string): Promise<{ success: boolean; user_id: string }> {
  const response = await authedFetch(`${BASE_URL}/users/${userId}/reset`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    throw await readError(response, '重置计数器失败');
  }
  return response.json();
}

/**
 * 用户配额详情 — GET /admin/image-generation/quota/{user_id}
 */
export async function getUserQuota(userId: string): Promise<QuotaUser> {
  const response = await authedFetch(`${BASE_URL}/quota/${userId}`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    throw await readError(response, '获取用户配额失败');
  }
  return response.json();
}

/* ================================================================
 * Dify 配置 API
 * ================================================================ */

/**
 * 获取 Dify 配置 — GET /admin/image-generation/config
 */
export async function getDifyConfig(): Promise<DifyConfig> {
  const response = await authedFetch(`${BASE_URL}/config`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    throw await readError(response, '获取 Dify 配置失败');
  }
  return response.json();
}

/**
 * 更新 Dify 配置 — PUT /admin/image-generation/config
 */
export async function updateDifyConfig(data: UpdateDifyConfigRequest): Promise<DifyConfig> {
  const response = await authedFetch(`${BASE_URL}/config`, {
    method: 'PUT',
    headers: {
      ...getAuthHeaders(),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    throw await readError(response, '更新 Dify 配置失败');
  }
  return response.json();
}

/**
 * 测试 Dify 连通性 — POST /admin/image-generation/config/test
 */
export async function testDifyConnection(): Promise<TestConnectionResponse> {
  const response = await authedFetch(`${BASE_URL}/config/test`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    throw await readError(response, '测试连通性失败');
  }
  return response.json();
}

/* ================================================================
 * 降级管理 API
 * ================================================================ */

/**
 * 获取降级状态 — GET /admin/image-generation/degradation
 */
export async function getDegradationStatus(): Promise<DegradationStatus> {
  const response = await authedFetch(`${BASE_URL}/degradation`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    throw await readError(response, '获取降级状态失败');
  }
  return response.json();
}

/**
 * 更新降级配置 — PUT /admin/image-generation/degradation
 */
export async function updateDegradationConfig(
  data: Partial<DegradationConfig>,
): Promise<DegradationStatus> {
  const response = await authedFetch(`${BASE_URL}/degradation`, {
    method: 'PUT',
    headers: {
      ...getAuthHeaders(),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    throw await readError(response, '更新降级配置失败');
  }
  return response.json();
}

/**
 * 手动解除降级 — POST /admin/image-generation/degradation/reset
 */
export async function resetDegradation(): Promise<{ success: boolean }> {
  const response = await authedFetch(`${BASE_URL}/degradation/reset`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    throw await readError(response, '解除降级失败');
  }
  return response.json();
}

/* ================================================================
 * 保留策略 API
 * ================================================================ */

/**
 * 获取保留策略 — GET /admin/image-generation/retention
 */
export async function getRetentionConfig(): Promise<RetentionStatus> {
  const response = await authedFetch(`${BASE_URL}/retention`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    throw await readError(response, '获取保留策略失败');
  }
  return response.json();
}

/**
 * 更新保留策略 — PUT /admin/image-generation/retention
 */
export async function updateRetentionConfig(
  data: Partial<RetentionConfig>,
): Promise<RetentionStatus> {
  const response = await authedFetch(`${BASE_URL}/retention`, {
    method: 'PUT',
    headers: {
      ...getAuthHeaders(),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    throw await readError(response, '更新保留策略失败');
  }
  return response.json();
}

/**
 * 手动触发清理 — POST /admin/image-generation/retention/trigger
 */
export async function triggerRetentionCleanup(): Promise<{ success: boolean }> {
  const response = await authedFetch(`${BASE_URL}/retention/trigger`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    throw await readError(response, '触发清理失败');
  }
  return response.json();
}

/* ================================================================
 * 统计 API
 * ================================================================ */

/**
 * 获取使用统计 — GET /admin/image-generation/stats
 */
export async function getStats(days = 7): Promise<StatsResponse> {
  const response = await authedFetch(`${BASE_URL}/stats?days=${days}`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    throw await readError(response, '获取统计信息失败');
  }
  return response.json();
}
