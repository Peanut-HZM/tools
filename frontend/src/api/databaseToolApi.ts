import { API_BASE_URL } from '../config/api';
import { getAuthHeaders } from './authApi';
import {
  DatabaseConfig,
  CreateDatabaseRequest,
  UpdateDatabaseRequest,
  TestConnectionRequest,
  ConnectionTestResult,
  SQLExecutionRequest,
  SQLExecutionResult,
  ExecutionHistory,
  TableSchema,
  DatabaseStructure,
  TableModificationRequest,
  InsertRowRequest,
  UpdateRowRequest,
  RowOperationResult,
  TableDetailResponse,
  BackupRequest,
  BackupResponse,
  BackupListResponse,
  BackupRecord,
} from '../types/databaseTool';
import { DBCache } from '../utils/dbCache';

// Re-export types for use in components
export type { BackupResponse, BackupRecord, BackupListResponse, BackupRequest };

const BASE_URL = `${API_BASE_URL}/database-tool`;

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || 'Request failed');
  }
  return response.json();
}

// Database Configs

export async function getDatabases(includePassword = false): Promise<DatabaseConfig[]> {
  // includePassword=true 时不走缓存（通常只在编辑连接时使用）
  if (!includePassword) {
    const cached = await DBCache.get<DatabaseConfig[]>('configs');
    if (cached) return cached;
  }

  const query = includePassword ? '?include_password=true' : '';
  const response = await fetch(`${BASE_URL}/databases${query}`, {
    headers: getAuthHeaders()
  });
  const data = await handleResponse<DatabaseConfig[]>(response);

  if (!includePassword) {
    await DBCache.set('configs', data, 'configs');
  }
  return data;
}

export async function createDatabase(data: CreateDatabaseRequest): Promise<DatabaseConfig> {
  const response = await fetch(`${BASE_URL}/databases`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(data)
  });
  const result = await handleResponse<DatabaseConfig>(response);
  // 配置变更：清除连接列表缓存
  await DBCache.invalidate('configs');
  return result;
}

export async function getDatabase(id: string, includePassword = false): Promise<DatabaseConfig> {
  const query = includePassword ? '?include_password=true' : '';
  const response = await fetch(`${BASE_URL}/databases/${id}${query}`, {
    headers: getAuthHeaders()
  });
  return handleResponse<DatabaseConfig>(response);
}

export async function decryptPassword(id: string): Promise<string> {
  const response = await fetch(`${BASE_URL}/databases/${id}/decrypt-password`, {
    method: 'POST',
    headers: getAuthHeaders()
  });
  const result = await handleResponse<{ password: string }>(response);
  return result.password;
}

export async function updateDatabase(id: string, data: UpdateDatabaseRequest): Promise<DatabaseConfig> {
  const response = await fetch(`${BASE_URL}/databases/${id}`, {
    method: 'PUT',
    headers: getAuthHeaders(),
    body: JSON.stringify(data)
  });
  const result = await handleResponse<DatabaseConfig>(response);
  // 配置变更：清除连接列表 + 该配置下所有数据库列表 + 结构缓存
  await DBCache.invalidate('configs');
  await DBCache.invalidatePrefix(`databases:${id}`);
  await DBCache.invalidatePrefix(`structure:${id}`);
  return result;
}

export async function deleteDatabase(id: string): Promise<void> {
  const response = await fetch(`${BASE_URL}/databases/${id}`, {
    method: 'DELETE',
    headers: getAuthHeaders()
  });
  await handleResponse<void>(response);
  // 配置删除：清除连接列表 + 该配置下所有缓存
  await DBCache.invalidate('configs');
  await DBCache.invalidatePrefix(`databases:${id}`);
  await DBCache.invalidatePrefix(`structure:${id}`);
}

export async function testConnection(data: TestConnectionRequest): Promise<ConnectionTestResult> {
  const response = await fetch(`${BASE_URL}/databases/test`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(data)
  });
  return handleResponse<ConnectionTestResult>(response);
}

export async function testConnectionById(id: string): Promise<ConnectionTestResult> {
  const response = await fetch(`${BASE_URL}/databases/${id}/test`, {
    method: 'POST',
    headers: getAuthHeaders()
  });
  return handleResponse<ConnectionTestResult>(response);
}

export async function getDatabasesList(id: string): Promise<string[]> {
  const cacheKey = `databases:${id}`;
  const cached = await DBCache.get<string[]>(cacheKey);
  if (cached) return cached;

  const response = await fetch(`${BASE_URL}/databases/${id}/databases`, {
    headers: getAuthHeaders()
  });
  const data = await handleResponse<string[]>(response);
  await DBCache.set(cacheKey, data, 'databases');
  return data;
}

// Database Administration (DDL)

export async function createDatabaseInstance(id: string, name: string, charset?: string): Promise<boolean> {
  const response = await fetch(`${BASE_URL}/databases/${id}/databases`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ name, charset })
  });
  const result = await handleResponse<boolean>(response);
  await DBCache.invalidate(`databases:${id}`);
  return result;
}

export async function dropDatabaseInstance(id: string, name: string): Promise<boolean> {
  const response = await fetch(`${BASE_URL}/databases/${id}/databases/${encodeURIComponent(name)}`, {
    method: 'DELETE',
    headers: getAuthHeaders()
  });
  const result = await handleResponse<boolean>(response);
  await DBCache.invalidate(`databases:${id}`);
  await DBCache.invalidatePrefix(`structure:${id}:${name}`);
  return result;
}

export async function dropTableInstance(id: string, table: string, databaseName: string): Promise<boolean> {
  const response = await fetch(`${BASE_URL}/databases/${id}/tables/${encodeURIComponent(table)}?database_name=${encodeURIComponent(databaseName)}`, {
    method: 'DELETE',
    headers: getAuthHeaders()
  });
  const result = await handleResponse<boolean>(response);
  await DBCache.invalidate(`structure:${id}:${databaseName}`);
  return result;
}

export async function truncateTableInstance(id: string, table: string, databaseName: string): Promise<boolean> {
  const response = await fetch(`${BASE_URL}/databases/${id}/tables/${encodeURIComponent(table)}/truncate`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ database_name: databaseName })
  });
  const result = await handleResponse<boolean>(response);
  await DBCache.invalidate(`structure:${id}:${databaseName}`);
  return result;
}

// In-flight 请求去重：相同 (id, databaseName) 的并发请求共享同一个 Promise
const pendingStructureRequests = new Map<string, Promise<DatabaseStructure>>();

export async function getDatabaseStructure(id: string, databaseName: string): Promise<DatabaseStructure> {
  const cacheKey = `structure:${id}:${databaseName}`;

  // 1. 查 IndexedDB 缓存
  const cached = await DBCache.get<DatabaseStructure>(cacheKey);
  if (cached) return cached;

  // 2. 检查是否已有相同请求在飞行中
  if (pendingStructureRequests.has(cacheKey)) {
    return pendingStructureRequests.get(cacheKey)!;
  }

  // 3. 发起请求并注册到 in-flight 追踪
  const requestPromise = (async () => {
    try {
      const response = await fetch(`${BASE_URL}/databases/${id}/structure?database_name=${encodeURIComponent(databaseName)}`, {
        headers: getAuthHeaders()
      });
      const data = await handleResponse<DatabaseStructure>(response);
      await DBCache.set(cacheKey, data, 'structure');
      return data;
    } finally {
      pendingStructureRequests.delete(cacheKey);
    }
  })();

  pendingStructureRequests.set(cacheKey, requestPromise);
  return requestPromise;
}

export async function getTableDDL(id: string, table: string, databaseName: string): Promise<string> {
  const response = await fetch(`${BASE_URL}/databases/${id}/tables/${encodeURIComponent(table)}/ddl?database_name=${encodeURIComponent(databaseName)}`, {
    headers: getAuthHeaders()
  });
  return handleResponse<string>(response);
}

export async function modifyTableStructure(id: string, request: TableModificationRequest): Promise<boolean> {
  const response = await fetch(`${BASE_URL}/databases/${id}/tables/modify`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(request)
  });
  const result = await handleResponse<boolean>(response);
  // 结构变更：清除该数据库的结构缓存
  await DBCache.invalidate(`structure:${id}:${request.database_name}`);
  return result;
}

export async function deleteAllTables(id: string, databaseName: string): Promise<boolean> {
  const response = await fetch(`${BASE_URL}/databases/${id}/all-tables?database_name=${encodeURIComponent(databaseName)}`, {
    method: 'DELETE',
    headers: getAuthHeaders()
  });
  const result = await handleResponse<boolean>(response);
  await DBCache.invalidate(`structure:${id}:${databaseName}`);
  return result;
}

export async function truncateAllTables(id: string, databaseName: string): Promise<boolean> {
  const response = await fetch(`${BASE_URL}/databases/${id}/truncate-all-tables`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ database_name: databaseName })
  });
  const result = await handleResponse<boolean>(response);
  await DBCache.invalidate(`structure:${id}:${databaseName}`);
  return result;
}

export async function getDatabaseDDL(id: string, databaseName: string): Promise<string> {
  const response = await fetch(`${BASE_URL}/databases/${id}/ddl?database_name=${encodeURIComponent(databaseName)}`, {
    headers: getAuthHeaders()
  });
  return handleResponse<string>(response);
}

export async function queryTableData(
  id: string, 
  table: string, 
  params: { 
    database_name?: string;
    where?: string; 
    order_by?: string; 
    page?: number; 
    page_size?: number 
  }
): Promise<SQLExecutionResult> {
  const response = await fetch(`${BASE_URL}/databases/${id}/tables/${table}/data`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(params)
  });
  return handleResponse<SQLExecutionResult>(response);
}

export async function getTableSchema(id: string, table: string, databaseName?: string): Promise<TableSchema> {
  let url = `${BASE_URL}/databases/${id}/tables/${table}/schema`;
  if (databaseName) {
    url += `?database_name=${encodeURIComponent(databaseName)}`;
  }
  const response = await fetch(url, {
    headers: getAuthHeaders()
  });
  return handleResponse<TableSchema>(response);
}

// SQL Execution

export async function executeSQL(data: SQLExecutionRequest): Promise<SQLExecutionResult> {
  const response = await fetch(`${BASE_URL}/execute`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(data)
  });
  return handleResponse<SQLExecutionResult>(response);
}

export async function getHistory(limit: number = 50, offset: number = 0): Promise<ExecutionHistory[]> {
  const response = await fetch(`${BASE_URL}/history?limit=${limit}&offset=${offset}`, {
    headers: getAuthHeaders()
  });
  return handleResponse<ExecutionHistory[]>(response);
}

// Schema Browsing

export async function getTables(id: string): Promise<string[]> {
  const response = await fetch(`${BASE_URL}/databases/${id}/tables`, {
    headers: getAuthHeaders()
  });
  return handleResponse<string[]>(response);
}

export interface BatchDeleteRequest {
  database_name?: string;
  primary_keys: string[];
  key_values: Record<string, any>[];
}

export interface BatchDeleteResult {
  success: boolean;
  deleted_count: number;
  failed_count: number;
  error_message?: string;
  execution_time_ms: number;
}

export async function batchDeleteRows(
  id: string,
  table: string,
  params: BatchDeleteRequest
): Promise<BatchDeleteResult> {
  const response = await fetch(
    `${BASE_URL}/databases/${id}/tables/${encodeURIComponent(table)}/batch-delete`,
    {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(params)
    }
  );
  return handleResponse<BatchDeleteResult>(response);
}

export async function searchTables(id: string, keyword: string): Promise<{database: string, table: string, type: string}[]> {
  const response = await fetch(`${BASE_URL}/databases/${id}/search`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ keyword })
  });
  return handleResponse<{database: string, table: string, type: string}[]>(response);
}

export async function insertRow(
  id: string,
  table: string,
  params: InsertRowRequest
): Promise<RowOperationResult> {
  const response = await fetch(
    `${BASE_URL}/databases/${id}/tables/${encodeURIComponent(table)}/insert-row`,
    {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(params)
    }
  );
  return handleResponse<RowOperationResult>(response);
}

export async function updateRow(
  id: string,
  table: string,
  params: UpdateRowRequest
): Promise<RowOperationResult> {
  const response = await fetch(
    `${BASE_URL}/databases/${id}/tables/${encodeURIComponent(table)}/update-row`,
    {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(params)
    }
  );
  return handleResponse<RowOperationResult>(response);
}

// ============ 表详情 API ============

export async function getTableDetail(
  id: string,
  table: string,
  databaseName: string
): Promise<TableDetailResponse> {
  const response = await fetch(
    `${BASE_URL}/databases/${id}/tables/${encodeURIComponent(table)}/detail?database_name=${encodeURIComponent(databaseName)}`,
    { headers: getAuthHeaders() }
  );
  return handleResponse<TableDetailResponse>(response);
}

export async function getTableRowCount(
  id: string,
  table: string,
  databaseName: string
): Promise<{ table_name: string; row_count: number }> {
  const response = await fetch(
    `${BASE_URL}/databases/${id}/tables/${encodeURIComponent(table)}/row-count?database_name=${encodeURIComponent(databaseName)}`,
    { headers: getAuthHeaders() }
  );
  return handleResponse<{ table_name: string; row_count: number }>(response);
}

// ============ 备份 API ============

export async function backupDatabase(
  id: string,
  params: BackupRequest
): Promise<BackupResponse> {
  const response = await fetch(
    `${BASE_URL}/configs/${id}/backup`,
    {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(params)
    }
  );
  return handleResponse<BackupResponse>(response);
}

export async function listBackups(
  id: string,
  databaseName?: string,
  page: number = 1,
  pageSize: number = 20
): Promise<BackupListResponse> {
  let url = `${BASE_URL}/configs/${id}/backups?page=${page}&page_size=${pageSize}`;
  if (databaseName) {
    url += `&database_name=${encodeURIComponent(databaseName)}`;
  }
  const response = await fetch(url, { headers: getAuthHeaders() });
  return handleResponse<BackupListResponse>(response);
}

export async function deleteBackup(backupId: string): Promise<{ message: string }> {
  const response = await fetch(
    `${BASE_URL}/backups/${backupId}`,
    {
      method: 'DELETE',
      headers: getAuthHeaders()
    }
  );
  return handleResponse<{ message: string }>(response);
}

export function getBackupDownloadUrl(backupId: string): string {
  return `${BASE_URL}/backups/${backupId}/download`;
}
