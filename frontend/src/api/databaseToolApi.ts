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
  DisplayPreferences,
} from '../types/databaseTool';
import { DBCache } from '../utils/dbCache';

// Re-export types for use in components
export type { BackupResponse, BackupRecord, BackupListResponse, BackupRequest };

/** 导出数据响应 */
export interface ExportDataResponse {
  file_name: string;
  file_size: number;
  content: string | null;
  download_url: string | null;
  row_count: number;
}

/** 导出格式 */
export type ExportFormat = 'csv' | 'excel' | 'json' | 'sql';

const BASE_URL = `${API_BASE_URL}/database-tool`;

/** 带超时的 fetch 封装 */
async function fetchWithTimeout(url: string, options: RequestInit & { timeout?: number } = {}) {
  const { timeout = 15000, ...rest } = options;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);
  try {
    const response = await fetch(url, {
      ...rest,
      signal: controller.signal,
    });
    return response;
  } catch (err: any) {
    if (err.name === 'AbortError') {
      throw new Error(`请求超时（${timeout / 1000} 秒）`);
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    // 保留 detail 原始结构（对象不被 String 化）
    const err = new Error(typeof error.detail === 'string' ? error.detail : JSON.stringify(error.detail));
    (err as any).detail = error.detail;
    (err as any).response = { detail: error.detail };
    throw err;
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
  const response = await fetchWithTimeout(`${BASE_URL}/databases${query}`, {
    headers: getAuthHeaders(),
    timeout: 30000
  });
  const data = await handleResponse<DatabaseConfig[]>(response);

  if (!includePassword) {
    await DBCache.set('configs', data, 'configs');
  }
  return data;
}

export async function createDatabase(data: CreateDatabaseRequest): Promise<DatabaseConfig> {
  const response = await fetchWithTimeout(`${BASE_URL}/databases`, {
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
  const response = await fetchWithTimeout(`${BASE_URL}/databases/${id}${query}`, {
    headers: getAuthHeaders()
  });
  return handleResponse<DatabaseConfig>(response);
}

export async function decryptPassword(id: string): Promise<string> {
  const response = await fetchWithTimeout(`${BASE_URL}/databases/${id}/decrypt-password`, {
    method: 'POST',
    headers: getAuthHeaders()
  });
  const result = await handleResponse<{ password: string }>(response);
  return result.password;
}

export async function updateDatabase(id: string, data: UpdateDatabaseRequest): Promise<DatabaseConfig> {
  const response = await fetchWithTimeout(`${BASE_URL}/databases/${id}`, {
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
  const response = await fetchWithTimeout(`${BASE_URL}/databases/${id}`, {
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
  const response = await fetchWithTimeout(`${BASE_URL}/databases/test`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(data),
    timeout: 20000
  });
  return handleResponse<ConnectionTestResult>(response);
}

export async function testConnectionById(id: string): Promise<ConnectionTestResult> {
  const response = await fetchWithTimeout(`${BASE_URL}/databases/${id}/test`, {
    method: 'POST',
    headers: getAuthHeaders(),
    timeout: 20000
  });
  return handleResponse<ConnectionTestResult>(response);
}

export async function getDatabasesList(id: string, skipCache = false): Promise<string[]> {
  // v2：返回格式从 "db:schema" 变为 "db"，提升 cacheKey 版本使旧缓存失效
  const cacheKey = `databases:v2:${id}`;
  if (skipCache) {
    await DBCache.invalidate(cacheKey);
  } else {
    const cached = await DBCache.get<string[]>(cacheKey);
    if (cached) return cached;
  }

  // In-flight 去重：同一连接的并发请求共享 Promise，避免重复请求
  if (pendingDatabasesRequests.has(id)) {
    return pendingDatabasesRequests.get(id)!;
  }

  const requestPromise = (async () => {
    try {
      const query = skipCache ? '?skip_cache=true' : '';
      const response = await fetchWithTimeout(`${BASE_URL}/databases/${id}/databases${query}`, {
        headers: getAuthHeaders(),
        timeout: 20000
      });
      const data = await handleResponse<string[]>(response);
      await DBCache.set(cacheKey, data, 'databases');
      return data;
    } finally {
      pendingDatabasesRequests.delete(id);
    }
  })();

  pendingDatabasesRequests.set(id, requestPromise);
  return requestPromise;
}

export async function getSchemasList(
  id: string, databaseName: string, skipCache = false
): Promise<string[]> {
  const cacheKey = `schemas:${id}:${databaseName}`;
  if (skipCache) {
    await DBCache.invalidate(cacheKey);
  } else {
    const cached = await DBCache.get<string[]>(cacheKey);
    if (cached) return cached;
  }

  const pendingKey = `${id}:${databaseName}`;
  if (pendingSchemasRequests.has(pendingKey)) {
    return pendingSchemasRequests.get(pendingKey)!;
  }

  const requestPromise = (async () => {
    try {
      const skipParam = skipCache ? '&skip_cache=true' : '';
      const response = await fetchWithTimeout(
        `${BASE_URL}/databases/${id}/schemas?database_name=${encodeURIComponent(databaseName)}${skipParam}`,
        { headers: getAuthHeaders(), timeout: 20000 }
      );
      const data = await handleResponse<string[]>(response);
      await DBCache.set(cacheKey, data, 'schemas');
      return data;
    } finally {
      pendingSchemasRequests.delete(pendingKey);
    }
  })();

  pendingSchemasRequests.set(pendingKey, requestPromise);
  return requestPromise;
}

export async function getAllSchemas(
  id: string, skipCache = false
): Promise<Record<string, string[]>> {
  const cacheKey = `all_schemas:${id}`;
  if (skipCache) {
    await DBCache.invalidate(cacheKey);
  } else {
    const cached = await DBCache.get<Record<string, string[]>>(cacheKey);
    if (cached) return cached;
  }

  if (pendingAllSchemasRequests.has(id)) {
    return pendingAllSchemasRequests.get(id)!;
  }

  const requestPromise = (async () => {
    try {
      const query = skipCache ? '?skip_cache=true' : '';
      const response = await fetchWithTimeout(`${BASE_URL}/databases/${id}/all-schemas${query}`, {
        headers: getAuthHeaders(),
        timeout: 30000
      });
      const data = await handleResponse<Record<string, string[]>>(response);
      await DBCache.set(cacheKey, data, 'databases');
      return data;
    } finally {
      pendingAllSchemasRequests.delete(id);
    }
  })();

  pendingAllSchemasRequests.set(id, requestPromise);
  return requestPromise;
}

// Database Administration (DDL)

export async function createDatabaseInstance(id: string, name: string, charset?: string): Promise<boolean> {
  const response = await fetchWithTimeout(`${BASE_URL}/databases/${id}/databases`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ name, charset })
  });
  const result = await handleResponse<boolean>(response);
  await DBCache.invalidate(`databases:${id}`);
  return result;
}

export async function dropDatabaseInstance(id: string, name: string): Promise<boolean> {
  const response = await fetchWithTimeout(`${BASE_URL}/databases/${id}/databases/${encodeURIComponent(name)}`, {
    method: 'DELETE',
    headers: getAuthHeaders()
  });
  const result = await handleResponse<boolean>(response);
  await DBCache.invalidate(`databases:${id}`);
  await DBCache.invalidatePrefix(`structure:${id}:${name}`);
  return result;
}

export async function dropTableInstance(id: string, table: string, databaseName: string, schemaName?: string): Promise<boolean> {
  const schemaParam = schemaName ? `&schema_name=${encodeURIComponent(schemaName)}` : '';
  const response = await fetchWithTimeout(`${BASE_URL}/databases/${id}/tables/${encodeURIComponent(table)}?database_name=${encodeURIComponent(databaseName)}${schemaParam}`, {
    method: 'DELETE',
    headers: getAuthHeaders()
  });
  const result = await handleResponse<boolean>(response);
  await DBCache.invalidate(`structure:${id}:${databaseName}${schemaName ? ':' + schemaName : ''}`);
  return result;
}

export async function truncateTableInstance(id: string, table: string, databaseName: string, schemaName?: string): Promise<boolean> {
  const response = await fetchWithTimeout(`${BASE_URL}/databases/${id}/tables/${encodeURIComponent(table)}/truncate`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ database_name: databaseName, schema_name: schemaName })
  });
  const result = await handleResponse<boolean>(response);
  await DBCache.invalidate(`structure:${id}:${databaseName}${schemaName ? ':' + schemaName : ''}`);
  return result;
}

// In-flight 请求去重：相同 (id, databaseName) 的并发请求共享同一个 Promise
const pendingStructureRequests = new Map<string, Promise<DatabaseStructure>>();
// In-flight 去重：相同 configId 的数据库列表并发请求共享同一个 Promise
const pendingDatabasesRequests = new Map<string, Promise<string[]>>();
const pendingSchemasRequests = new Map<string, Promise<string[]>>();
const pendingAllSchemasRequests = new Map<string, Promise<Record<string, string[]>>>();
// 后台静默刷新去重：避免同一 cacheKey 重复触发后台刷新
const pendingBackgroundRevalidations = new Set<string>();

export async function getDatabaseStructure(id: string, databaseName: string, schemaName?: string, skipCache = false): Promise<DatabaseStructure> {
  const schemaParam = schemaName ? `&schema_name=${encodeURIComponent(schemaName)}` : '';
  const cacheKey = `structure:${id}:${databaseName}${schemaName ? ':' + schemaName : ''}`;

  // 1. skipCache 时清除缓存
  if (skipCache) {
    await DBCache.invalidate(cacheKey);
  } else {
    // 2. Stale-While-Revalidate 策略：查 IndexedDB（不管是否过期）
    const raw = await DBCache.getRaw<DatabaseStructure>(cacheKey);
    if (raw) {
      if (raw.isStale) {
        // 缓存已过期：立即返回旧数据，后台静默刷新
        revalidateStructureInBackground(cacheKey, id, databaseName, schemaName);
      }
      return raw.data;
    }
  }

  // 3. 无缓存：走常规 fetch
  if (pendingStructureRequests.has(cacheKey)) {
    return pendingStructureRequests.get(cacheKey)!;
  }

  const requestPromise = (async () => {
    try {
      const response = await fetchWithTimeout(`${BASE_URL}/databases/${id}/structure?database_name=${encodeURIComponent(databaseName)}${schemaParam}`, {
        headers: getAuthHeaders(),
        timeout: 20000
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

// 后台静默刷新 structure 缓存（不阻塞调用方，刷新完通过 CustomEvent 通知）
function revalidateStructureInBackground(cacheKey: string, id: string, databaseName: string, schemaName?: string) {
  if (pendingBackgroundRevalidations.has(cacheKey)) return;
  pendingBackgroundRevalidations.add(cacheKey);

  (async () => {
    try {
      const schemaParam = schemaName ? `&schema_name=${encodeURIComponent(schemaName)}` : '';
      const response = await fetchWithTimeout(`${BASE_URL}/databases/${id}/structure?database_name=${encodeURIComponent(databaseName)}${schemaParam}`, {
        headers: getAuthHeaders(),
        timeout: 20000
      });
      const data = await handleResponse<DatabaseStructure>(response);
      await DBCache.set(cacheKey, data, 'structure');
      // 通知监听者（DatabaseStructureNode）缓存已更新，触发 re-render 显示新数据
      window.dispatchEvent(new CustomEvent('db-cache-updated', { detail: { cacheKey } }));
    } catch (e) {
      // 静默失败：旧数据仍然可用
      console.warn('[DBCache] background revalidate failed:', e);
    } finally {
      pendingBackgroundRevalidations.delete(cacheKey);
    }
  })();
}

export async function getTableDDL(id: string, table: string, databaseName: string, schemaName?: string): Promise<string> {
  const schemaParam = schemaName ? `&schema_name=${encodeURIComponent(schemaName)}` : '';
  const response = await fetchWithTimeout(`${BASE_URL}/databases/${id}/tables/${encodeURIComponent(table)}/ddl?database_name=${encodeURIComponent(databaseName)}${schemaParam}`, {
    headers: getAuthHeaders()
  });
  return handleResponse<string>(response);
}

export async function modifyTableStructure(id: string, request: TableModificationRequest): Promise<boolean> {
  const response = await fetchWithTimeout(`${BASE_URL}/databases/${id}/tables/modify`, {
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
  const response = await fetchWithTimeout(`${BASE_URL}/databases/${id}/all-tables?database_name=${encodeURIComponent(databaseName)}`, {
    method: 'DELETE',
    headers: getAuthHeaders()
  });
  const result = await handleResponse<boolean>(response);
  await DBCache.invalidate(`structure:${id}:${databaseName}`);
  return result;
}

export async function truncateAllTables(id: string, databaseName: string): Promise<boolean> {
  const response = await fetchWithTimeout(`${BASE_URL}/databases/${id}/truncate-all-tables`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ database_name: databaseName })
  });
  const result = await handleResponse<boolean>(response);
  await DBCache.invalidate(`structure:${id}:${databaseName}`);
  return result;
}

export async function getDatabaseDDL(id: string, databaseName: string): Promise<string> {
  const response = await fetchWithTimeout(`${BASE_URL}/databases/${id}/ddl?database_name=${encodeURIComponent(databaseName)}`, {
    headers: getAuthHeaders()
  });
  return handleResponse<string>(response);
}

export async function queryTableData(
  id: string,
  table: string,
  params: {
    database_name?: string;
    schema_name?: string;
    where?: string;
    order_by?: string;
    page?: number;
    page_size?: number
  }
): Promise<SQLExecutionResult> {
  const response = await fetchWithTimeout(`${BASE_URL}/databases/${id}/tables/${table}/data`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(params),
    timeout: 30000
  });
  return handleResponse<SQLExecutionResult>(response);
}

/** 导出表数据（按筛选条件导出全部数据） */
export async function exportTableData(
  id: string,
  request: {
    sql: string;
    format: ExportFormat;
    database_name?: string;
  }
): Promise<ExportDataResponse> {
  const response = await fetchWithTimeout(
    `${BASE_URL}/configs/${encodeURIComponent(id)}/export`,
    {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(request),
      timeout: 120000, // 2 minutes for large exports
    }
  );
  return handleResponse<ExportDataResponse>(response);
}

export async function getTableSchema(id: string, table: string, databaseName?: string, schemaName?: string): Promise<TableSchema> {
  const params = new URLSearchParams();
  if (databaseName) params.set('database_name', databaseName);
  if (schemaName) params.set('schema_name', schemaName);
  const qs = params.toString();
  const url = `${BASE_URL}/databases/${id}/tables/${table}/schema${qs ? '?' + qs : ''}`;
  const response = await fetchWithTimeout(url, {
    headers: getAuthHeaders()
  });
  return handleResponse<TableSchema>(response);
}

// SQL Execution

export async function executeSQL(data: SQLExecutionRequest): Promise<SQLExecutionResult> {
  const response = await fetchWithTimeout(`${BASE_URL}/execute`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(data),
    timeout: 30000
  });
  return handleResponse<SQLExecutionResult>(response);
}

export async function getHistory(limit: number = 50, offset: number = 0): Promise<ExecutionHistory[]> {
  const response = await fetchWithTimeout(`${BASE_URL}/history?limit=${limit}&offset=${offset}`, {
    headers: getAuthHeaders(),
    timeout: 30000
  });
  return handleResponse<ExecutionHistory[]>(response);
}

// Schema Browsing

export async function getTables(id: string): Promise<string[]> {
  const response = await fetchWithTimeout(`${BASE_URL}/databases/${id}/tables`, {
    headers: getAuthHeaders()
  });
  return handleResponse<string[]>(response);
}

export interface BatchDeleteRequest {
  database_name?: string;
  schema_name?: string;
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
  const response = await fetchWithTimeout(
    `${BASE_URL}/databases/${id}/tables/${encodeURIComponent(table)}/batch-delete`,
    {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(params),
      timeout: 30000
    }
  );
  return handleResponse<BatchDeleteResult>(response);
}

export async function searchTables(id: string, keyword: string): Promise<{database: string, table: string, type: string}[]> {
  const response = await fetchWithTimeout(`${BASE_URL}/databases/${id}/search`, {
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
  const response = await fetchWithTimeout(
    `${BASE_URL}/databases/${id}/tables/${encodeURIComponent(table)}/insert-row`,
    {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(params),
      timeout: 30000
    }
  );
  return handleResponse<RowOperationResult>(response);
}

export async function updateRow(
  id: string,
  table: string,
  params: UpdateRowRequest
): Promise<RowOperationResult> {
  const response = await fetchWithTimeout(
    `${BASE_URL}/databases/${id}/tables/${encodeURIComponent(table)}/update-row`,
    {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(params),
      timeout: 30000
    }
  );
  return handleResponse<RowOperationResult>(response);
}

// ============ 表详情 API ============

export async function getTableDetail(
  id: string,
  table: string,
  databaseName: string,
  schemaName?: string
): Promise<TableDetailResponse> {
  const schemaParam = schemaName ? `&schema_name=${encodeURIComponent(schemaName)}` : '';
  const response = await fetchWithTimeout(
    `${BASE_URL}/databases/${id}/tables/${encodeURIComponent(table)}/detail?database_name=${encodeURIComponent(databaseName)}${schemaParam}`,
    { headers: getAuthHeaders() }
  );
  return handleResponse<TableDetailResponse>(response);
}

export async function getTableRowCount(
  id: string,
  table: string,
  databaseName: string,
  schemaName?: string
): Promise<{ table_name: string; row_count: number }> {
  const schemaParam = schemaName ? `&schema_name=${encodeURIComponent(schemaName)}` : '';
  const response = await fetchWithTimeout(
    `${BASE_URL}/databases/${id}/tables/${encodeURIComponent(table)}/row-count?database_name=${encodeURIComponent(databaseName)}${schemaParam}`,
    { headers: getAuthHeaders() }
  );
  return handleResponse<{ table_name: string; row_count: number }>(response);
}

// ============ 备份 API ============

export async function backupDatabase(
  id: string,
  params: BackupRequest
): Promise<BackupResponse> {
  const response = await fetchWithTimeout(
    `${BASE_URL}/configs/${id}/backup`,
    {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(params),
      timeout: 60000
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
  const response = await fetchWithTimeout(url, { headers: getAuthHeaders() });
  return handleResponse<BackupListResponse>(response);
}

export async function deleteBackup(backupId: string): Promise<{ message: string }> {
  const response = await fetchWithTimeout(
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

// ============ 显示偏好 API ============

export async function getDisplayPreferences(): Promise<DisplayPreferences> {
  const response = await fetchWithTimeout(`${BASE_URL}/preferences`, {
    headers: getAuthHeaders()
  });
  return handleResponse<DisplayPreferences>(response);
}

export async function saveDisplayPreferences(
  prefs: DisplayPreferences
): Promise<DisplayPreferences> {
  const response = await fetchWithTimeout(`${BASE_URL}/preferences`, {
    method: 'PUT',
    headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
    body: JSON.stringify({
      visible_connections: prefs.visible_connections,
      visible_databases: prefs.visible_databases,
    })
  });
  return handleResponse<DisplayPreferences>(response);
}
