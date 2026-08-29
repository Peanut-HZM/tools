/**
 * MCP Servers API Client
 *
 * Phase 3-Plan-1A: MCP 工具支持核心骨架
 */

import { getAuthHeaders } from './authApi';
import { AUTH_API_BASE_URL } from '../config/api';
import { authedFetch } from './http';

const API_BASE_URL = AUTH_API_BASE_URL.replace('/auth', '/admin');

/** MCP Server 实体（对应后端 McpServerResponse） */
export interface McpServer {
  id: string;
  name: string;
  server_url: string;
  transport: 'sse';
  is_active: boolean;
  timeout_seconds: number;
  last_connected_at: string | null;
  last_error: string | null;
  tools_count: number;
  created_at: string;
  updated_at: string;
}

/** 创建 MCP Server 请求（对应后端 McpServerCreate） */
export interface McpServerCreate {
  name: string;
  server_url: string;
  transport?: 'sse';
  headers?: Record<string, string>;
  timeout_seconds?: number;
}

/** 更新 MCP Server 请求（对应后端 McpServerUpdate） */
export interface McpServerUpdate {
  name?: string;
  server_url?: string;
  headers?: Record<string, string>;
  timeout_seconds?: number;
  is_active?: boolean;
}

/** 测试连接响应（对应后端 McpServerTestResponse） */
export interface McpServerTestResponse {
  success: boolean;
  tools: Array<{ name: string; description?: string }>;
  error?: string;
}

/** 同步工具响应 */
export interface McpServerSyncResponse {
  success: boolean;
  tools_count: number;
  error?: string;
}

async function parseError(response: Response, fallback: string): Promise<never> {
  const error = await response.json().catch(() => ({ detail: fallback }));
  throw new Error(error.detail || fallback);
}

/** 列出所有 MCP servers */
export async function listServers(): Promise<McpServer[]> {
  const response = await authedFetch(`${API_BASE_URL}/mcp/servers`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) throw new Error('Failed to list MCP servers');
  return response.json();
}

/** 创建 MCP server */
export async function createServer(data: McpServerCreate): Promise<McpServer> {
  const response = await authedFetch(`${API_BASE_URL}/mcp/servers`, {
    method: 'POST',
    headers: {
      ...getAuthHeaders(),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });
  if (!response.ok) await parseError(response, 'Failed to create MCP server');
  return response.json();
}

/** 更新 MCP server */
export async function updateServer(id: string, data: McpServerUpdate): Promise<McpServer> {
  const response = await authedFetch(`${API_BASE_URL}/mcp/servers/${id}`, {
    method: 'PUT',
    headers: {
      ...getAuthHeaders(),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });
  if (!response.ok) await parseError(response, 'Failed to update MCP server');
  return response.json();
}

/** 删除 MCP server（后端返回 204 No Content） */
export async function deleteServer(id: string): Promise<void> {
  const response = await authedFetch(`${API_BASE_URL}/mcp/servers/${id}`, {
    method: 'DELETE',
    headers: getAuthHeaders(),
  });
  if (!response.ok && response.status !== 204) {
    throw new Error(`Failed to delete MCP server: HTTP ${response.status}`);
  }
}

/** 测试 MCP server 连接 */
export async function testServer(id: string): Promise<McpServerTestResponse> {
  const response = await authedFetch(`${API_BASE_URL}/mcp/servers/${id}/test`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  if (!response.ok) await parseError(response, 'Failed to test MCP server');
  return response.json();
}

/** 同步 MCP server 工具到 ToolRegistry */
export async function syncServer(id: string): Promise<McpServerSyncResponse> {
  const response = await authedFetch(`${API_BASE_URL}/mcp/servers/${id}/sync`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  if (!response.ok) await parseError(response, 'Failed to sync MCP server');
  return response.json();
}

/**
 * mcpServersApi 命名空间对象
 * 兼容以下用法：mcpServersApi.list() / .create() / .update() / .delete() / .test() / .sync()
 */
export const mcpServersApi = {
  list: listServers,
  create: createServer,
  update: updateServer,
  delete: deleteServer,
  test: testServer,
  sync: syncServer,
};
