// Neo4j 浏览器工具 —— API 客户端与类型定义
// 与 redisToolApi.ts 同模式：authedFetch + getAuthHeaders，401 全局处理
import { API_BASE_URL } from '../config/api';
import { getAuthHeaders } from './authApi';
import { authedFetch } from './http';

const BASE = `${API_BASE_URL}/neo4j-tool`;

// ---------------------------------------------------------------------------
// 类型定义（Task 7/8 复用）
// ---------------------------------------------------------------------------

/** Neo4j 连接（响应不含密码） */
export interface Neo4jConnection {
  id: string;
  user_id?: string;
  name: string;
  uri: string;
  username: string;
  database: string;
  readonly: boolean;
  created_at?: string;
  updated_at?: string;
}

/** 新建连接请求体 */
export interface CreateNeo4jConnectionRequest {
  name: string;
  uri: string;
  username: string;
  password: string;
  database?: string;
}

/** 更新连接请求体（password 留空表示不变） */
export interface UpdateNeo4jConnectionRequest {
  name?: string;
  uri?: string;
  username?: string;
  password?: string;
  database?: string;
}

/** 连通性测试结果 */
export interface Neo4jTestResult {
  ok: boolean;
  server_version: string | null;
  error: string | null;
}

/** Schema 概览 —— Label 信息 */
export interface Neo4jLabelInfo {
  name: string;
  count: number;
  /** true 表示 count 为采样估算值（精确计数超时降级） */
  estimated: boolean;
  sampleProperties: string[];
}

/** Schema 概览 —— 关系类型信息 */
export interface Neo4jRelTypeInfo {
  name: string;
  count: number;
}

/** Schema 概览完整响应 */
export interface Neo4jSchema {
  labels: Neo4jLabelInfo[];
  relationshipTypes: Neo4jRelTypeInfo[];
  propertyKeys: string[];
}

/** 统一图格式 —— 节点 */
export interface GraphNode {
  id: string;
  labels: string[];
  properties: Record<string, unknown>;
}

/** 统一图格式 —— 关系 */
export interface GraphRel {
  id: string;
  type: string;
  source: string;
  target: string;
  properties: Record<string, unknown>;
}

/** 统一图格式 —— 图数据（Task 7 探索 / Task 8 查询复用） */
export interface GraphData {
  nodes: GraphNode[];
  relationships: GraphRel[];
  truncated: boolean;
}

// ---------------------------------------------------------------------------
// HTTP 封装（与 redisToolApi 的 request 一致）
// ---------------------------------------------------------------------------

async function request<T>(url: string, options: RequestInit = {}): Promise<T> {
  const headers = {
    ...getAuthHeaders(),
    ...options.headers,
  } as HeadersInit;

  const response = await authedFetch(url, { ...options, headers });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `Request failed with status ${response.status}`);
  }

  return response.json();
}

// ---------------------------------------------------------------------------
// 连接 CRUD
// ---------------------------------------------------------------------------

/** 列出当前用户的全部 Neo4j 连接 */
export const listConnections = () => {
  return request<Neo4jConnection[]>(`${BASE}/connections`);
};

/** 新建 Neo4j 连接 */
export const createConnection = (data: CreateNeo4jConnectionRequest) => {
  return request<Neo4jConnection>(`${BASE}/connections`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
};

/** 更新连接（password 传空字符串/不传表示不变） */
export const updateConnection = (id: string, data: UpdateNeo4jConnectionRequest) => {
  return request<Neo4jConnection>(`${BASE}/connections/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
};

/** 删除连接 */
export const deleteConnection = (id: string) => {
  return request<{ ok: boolean }>(`${BASE}/connections/${id}`, {
    method: 'DELETE',
  });
};

/** 测试连接连通性 */
export const testConnection = (id: string) => {
  return request<Neo4jTestResult>(`${BASE}/connections/${id}/test`, {
    method: 'POST',
  });
};

// ---------------------------------------------------------------------------
// Schema / 图数据（Task 7/8 使用，本任务仅消费 getSchema）
// ---------------------------------------------------------------------------

/** 获取 Schema 概览（labels / relationshipTypes / propertyKeys） */
export const getSchema = (id: string) => {
  return request<Neo4jSchema>(`${BASE}/connections/${id}/schema`);
};

/** 按 Label 采样子图（Task 7） */
export const sampleGraph = (
  id: string,
  body: { labels?: string[]; relTypes?: string[]; nodeLimitPerLabel?: number; relLimit?: number } = {},
) => {
  return request<GraphData>(`${BASE}/connections/${id}/graph/sample`, {
    method: 'POST',
    body: JSON.stringify(body),
  });
};

/** 邻居展开（Task 7） */
export const expandGraph = (
  id: string,
  body: { nodeId: string; direction?: string; relTypes?: string[]; limit?: number; offset?: number },
) => {
  return request<{ graph: GraphData; total: number | null }>(`${BASE}/connections/${id}/graph/expand`, {
    method: 'POST',
    body: JSON.stringify(body),
  });
};

/** 跨属性搜索节点（Task 7） */
export const searchNodes = (id: string, q: string, limit: number = 20) => {
  return request<GraphData>(
    `${BASE}/connections/${id}/nodes/search?q=${encodeURIComponent(q)}&limit=${limit}`,
  );
};

/** 执行只读 Cypher 查询（Task 8）
 * 行内 Node/Relationship/Path 值为 §6.5 序列化结构（含 __type/elementId），
 * graph.nodes/relationships 同样为序列化原始值（非统一 GraphData），由 ResultView 负责映射去重。
 */
export interface Neo4jQueryResult {
  columns: string[];
  rows: Array<Record<string, unknown>>;
  graph: {
    nodes: Array<Record<string, unknown>>;
    relationships: Array<Record<string, unknown>>;
  };
  truncated: boolean;
  elapsedMs: number;
}

export const runQuery = (
  id: string,
  body: { cypher: string; limit?: number; timeoutMs?: number },
) => {
  return request<Neo4jQueryResult>(`${BASE}/connections/${id}/query`, {
    method: 'POST',
    body: JSON.stringify(body),
  });
};
