/**
 * 存储位置与配置迁移 API 客户端
 */
import { API_BASE_URL } from '../config/api';
import { getAuthHeaders } from './authApi';
import { authedFetch } from './http';
import type {
  MigrateAllResult,
  MigrateResult,
  StorageLocation,
  StorageStatus,
  StorageTool,
} from '../types/storage';

const STORAGE_API_URL = `${API_BASE_URL}/storage`;

async function request<T>(url: string, options: RequestInit = {}): Promise<T> {
  const headers = {
    ...(getAuthHeaders() as Record<string, string>),
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  const response = await authedFetch(url, { ...options, headers });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    const detail = (error as { detail?: unknown }).detail;
    let message = 'Unknown error';
    if (Array.isArray(detail)) {
      // FastAPI 422 校验错误：detail 为数组，逐条拼接 msg
      message = detail
        .map((e: { msg?: string }) => e.msg || JSON.stringify(e))
        .join('; ');
    } else if (typeof detail === 'string') {
      message = detail;
    } else if (detail) {
      message = JSON.stringify(detail);
    }
    throw new Error(message);
  }

  return response.json() as Promise<T>;
}

/** 获取存储状态：远程服务器是否可用 + 本地库路径 */
export async function getStorageStatus(): Promise<StorageStatus> {
  return request<StorageStatus>(`${STORAGE_API_URL}/status`, { method: 'GET' });
}

/** 迁移单条配置到目标存储位置 */
export async function migrateConfig(
  tool: StorageTool,
  configId: string,
  target: StorageLocation,
): Promise<MigrateResult> {
  return request<MigrateResult>(
    `${STORAGE_API_URL}/${tool}/configs/${encodeURIComponent(configId)}/migrate`,
    {
      method: 'POST',
      body: JSON.stringify({ target }),
    },
  );
}

/** 批量迁移该用户的全部配置到目标存储位置 */
export async function migrateAllConfigs(
  tool: StorageTool,
  target: StorageLocation,
): Promise<MigrateAllResult> {
  return request<MigrateAllResult>(`${STORAGE_API_URL}/${tool}/configs/migrate-all`, {
    method: 'POST',
    body: JSON.stringify({ target }),
  });
}
