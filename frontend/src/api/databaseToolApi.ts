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
} from '../types/databaseTool';

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
  const query = includePassword ? '?include_password=true' : '';
  const response = await fetch(`${BASE_URL}/databases${query}`, {
    headers: getAuthHeaders()
  });
  return handleResponse<DatabaseConfig[]>(response);
}

export async function createDatabase(data: CreateDatabaseRequest): Promise<DatabaseConfig> {
  const response = await fetch(`${BASE_URL}/databases`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(data)
  });
  return handleResponse<DatabaseConfig>(response);
}

export async function getDatabase(id: string, includePassword = false): Promise<DatabaseConfig> {
  const query = includePassword ? '?include_password=true' : '';
  const response = await fetch(`${BASE_URL}/databases/${id}${query}`, {
    headers: getAuthHeaders()
  });
  return handleResponse<DatabaseConfig>(response);
}

export async function updateDatabase(id: string, data: UpdateDatabaseRequest): Promise<DatabaseConfig> {
  const response = await fetch(`${BASE_URL}/databases/${id}`, {
    method: 'PUT',
    headers: getAuthHeaders(),
    body: JSON.stringify(data)
  });
  return handleResponse<DatabaseConfig>(response);
}

export async function deleteDatabase(id: string): Promise<void> {
  const response = await fetch(`${BASE_URL}/databases/${id}`, {
    method: 'DELETE',
    headers: getAuthHeaders()
  });
  return handleResponse<void>(response);
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
  const response = await fetch(`${BASE_URL}/databases/${id}/databases`, {
    headers: getAuthHeaders()
  });
  return handleResponse<string[]>(response);
}

// Database Administration (DDL)

export async function createDatabaseInstance(id: string, name: string, charset?: string): Promise<boolean> {
  const response = await fetch(`${BASE_URL}/databases/${id}/databases`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ name, charset })
  });
  return handleResponse<boolean>(response);
}

export async function dropDatabaseInstance(id: string, name: string): Promise<boolean> {
  const response = await fetch(`${BASE_URL}/databases/${id}/databases/${encodeURIComponent(name)}`, {
    method: 'DELETE',
    headers: getAuthHeaders()
  });
  return handleResponse<boolean>(response);
}

export async function dropTableInstance(id: string, table: string, databaseName: string): Promise<boolean> {
  const response = await fetch(`${BASE_URL}/databases/${id}/tables/${encodeURIComponent(table)}?database_name=${encodeURIComponent(databaseName)}`, {
    method: 'DELETE',
    headers: getAuthHeaders()
  });
  return handleResponse<boolean>(response);
}

export async function truncateTableInstance(id: string, table: string, databaseName: string): Promise<boolean> {
  const response = await fetch(`${BASE_URL}/databases/${id}/tables/${encodeURIComponent(table)}/truncate`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ database_name: databaseName })
  });
  return handleResponse<boolean>(response);
}

export async function getDatabaseStructure(id: string, databaseName: string): Promise<DatabaseStructure> {
  const response = await fetch(`${BASE_URL}/databases/${id}/structure?database_name=${encodeURIComponent(databaseName)}`, {
    headers: getAuthHeaders()
  });
  return handleResponse<DatabaseStructure>(response);
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
  return handleResponse<boolean>(response);
}

export async function deleteAllTables(id: string, databaseName: string): Promise<boolean> {
  const response = await fetch(`${BASE_URL}/databases/${id}/all-tables?database_name=${encodeURIComponent(databaseName)}`, {
    method: 'DELETE',
    headers: getAuthHeaders()
  });
  return handleResponse<boolean>(response);
}

export async function truncateAllTables(id: string, databaseName: string): Promise<boolean> {
  const response = await fetch(`${BASE_URL}/databases/${id}/truncate-all-tables`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ database_name: databaseName })
  });
  return handleResponse<boolean>(response);
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
