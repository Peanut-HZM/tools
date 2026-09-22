/**
 * HTTP Client API 服务
 */

import axios from 'axios';
import { API_BASE_URL } from '../config/api';
import { getAuthToken } from '../api/authApi';
import { registerAuthFailureHandler } from '../api/http';

// 注册全局 axios 401 拦截器
// 当任何 axios 请求返回 401 时，触发登录弹窗
axios.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      // 复用 http.ts 中注册的回调（清除 token + 弹登录窗）
      if (getAuthToken()) {
        const handler = (window as any).__authFailureHandler;
        if (handler) handler();
      }
    }
    return Promise.reject(error);
  }
);

const httpClient = axios.create({
  baseURL: `${API_BASE_URL}/http-client`,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器 - 添加 JWT token
httpClient.interceptors.request.use((config) => {
  const token = getAuthToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ============= Types =============

/** Key-Value 条目（Headers / Query Params 通用，支持启用/禁用与描述） */
export interface KeyValueItem {
  key: string;
  value: string;
  enabled: boolean;
  description?: string;
}

/** 将旧版 dict 格式键值对转换为 list 格式 */
export const kvFromDict = (obj?: Record<string, string> | null): KeyValueItem[] =>
  Object.entries(obj || {})
    .filter(([k]) => k)
    .map(([key, value]) => ({ key, value: String(value ?? ''), enabled: true, description: '' }));

/** Form-data 单条目 */
export interface FormDataEntry {
  key: string;
  value: string;
  type: 'text' | 'file';
  enabled?: boolean;
  file?: File;
  description?: string;
}

/** Body 类型 */
export type BodyType = 'none' | 'json' | 'xml' | 'form' | 'form-data' | 'raw' | 'binary' | 'graphql';

/** 可视化断言规则 */
export interface AssertionRule {
  name?: string;
  source: 'status' | 'header' | 'body_json' | 'body_text' | 'response_time';
  expression: string;
  operator: string;
  value: string;
  enabled: boolean;
}

/** 断言比较方式 */
export const ASSERTION_OPERATORS: { value: string; label: string }[] = [
  { value: 'equal', label: '等于' },
  { value: 'not_equal', label: '不等于' },
  { value: 'contains', label: '包含' },
  { value: 'not_contains', label: '不包含' },
  { value: 'greater_than', label: '大于' },
  { value: 'less_than', label: '小于' },
  { value: 'greater_or_equal', label: '大于等于' },
  { value: 'less_or_equal', label: '小于等于' },
  { value: 'is_empty', label: '为空' },
  { value: 'not_empty', label: '不为空' },
  { value: 'exists', label: '存在' },
  { value: 'not_exists', label: '不存在' },
  { value: 'regex_match', label: '正则匹配' },
  { value: 'starts_with', label: '以...开始' },
  { value: 'ends_with', label: '以...结束' },
];

/** 后置提取变量规则 */
export interface ExtractVariableRule {
  name: string;
  source: 'body_json' | 'body_text' | 'header' | 'status' | 'response_time';
  expression: string;
  index?: number | null;
  enabled: boolean;
}

/** 断言执行结果 */
export interface AssertionResult {
  name: string;
  source: string;
  expression: string;
  operator: string;
  expected: string;
  actual: string;
  passed: boolean;
  message: string;
}

export interface Collection {
  id: string;
  name: string;
  description?: string;
  workspace_id?: string;
  parent_id?: string;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export interface HttpRequest {
  id: string;
  collection_id: string;
  name: string;
  method: string;
  url: string;
  headers: KeyValueItem[];
  params: KeyValueItem[];
  body_type: BodyType;
  body?: string;
  form_data?: FormDataEntry[];
  auth_type: 'bearer' | 'basic' | 'apikey' | 'none';
  auth_config: Record<string, any>;
  extract_variables: ExtractVariableRule[];
  assertions: AssertionRule[];
  description?: string;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

/** 补全请求对象的可选字段（历史数据兼容） */
export const normalizeHttpRequest = (req: Partial<HttpRequest> & { id: string; collection_id: string; name: string }): HttpRequest => {
  const defaults: HttpRequest = {
    id: req.id,
    collection_id: req.collection_id,
    name: req.name,
    method: 'GET',
    url: '',
    headers: [],
    params: [],
    body_type: 'none',
    form_data: [],
    auth_type: 'none',
    auth_config: {},
    extract_variables: [],
    assertions: [],
    sort_order: 0,
    created_at: '',
    updated_at: '',
  };
  const merged = { ...defaults, ...req } as HttpRequest;
  merged.headers = kvList(merged.headers);
  merged.params = kvList(merged.params);
  merged.form_data = merged.form_data || [];
  merged.extract_variables = merged.extract_variables || [];
  merged.assertions = merged.assertions || [];
  return merged;
};

function kvList(v: unknown): KeyValueItem[] {
  if (Array.isArray(v)) return v as KeyValueItem[];
  return kvFromDict(v as Record<string, string>);
}

export interface Environment {
  id: string;
  name: string;
  workspace_id: string;
  base_url: string;
  variables: Record<string, string>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface RequestHistory {
  id: string;
  user_id: string;
  request_id?: string;
  method: string;
  url: string;
  status_code: number;
  response_time: number;
  request_data: Record<string, any>;
  response_data: Record<string, any>;
  timestamp: string;
}

export interface SendRequestPayload {
  method: string;
  url: string;
  headers: KeyValueItem[];
  params: KeyValueItem[];
  body_type?: BodyType;
  body?: string;
  form_data?: FormDataEntry[];
  auth_type?: string;
  auth_config?: Record<string, any>;
  assertions?: AssertionRule[];
  extract_variables?: ExtractVariableRule[];
  request_id?: string;
  timeout?: number;
  follow_redirects?: boolean;
  workspace_id?: string;
}

export interface SendRequestResponse {
  status_code: number;
  status_text: string;
  headers: Record<string, string>;
  body: string;
  response_time: number;
  size: number;
  content_type?: string;
  request_url: string;
  request_headers: Record<string, string>;
  extracted_variables: Record<string, string>;
  assertion_results: AssertionResult[];
  error?: string | null;
}

// ============= Collection APIs =============

export const fetchCollections = async (workspaceId = 'default'): Promise<Collection[]> => {
  const response = await httpClient.get('/collections', { params: { workspace_id: workspaceId } });
  return response.data;
};

export const createCollection = async (data: {
  name: string;
  description?: string;
  workspace_id?: string;
  parent_id?: string;
  sort_order?: number;
}): Promise<Collection> => {
  const response = await httpClient.post('/collections', data);
  return response.data;
};

export const updateCollection = async (
  id: string,
  data: { name?: string; description?: string; sort_order?: number; parent_id?: string }
): Promise<Collection> => {
  const response = await httpClient.put(`/collections/${id}`, data);
  return response.data;
};

export const deleteCollection = async (id: string): Promise<void> => {
  await httpClient.delete(`/collections/${id}`);
};

// ============= Request APIs =============

export const fetchRequests = async (collectionId: string): Promise<HttpRequest[]> => {
  const response = await httpClient.get('/requests', { params: { collection_id: collectionId } });
  return response.data;
};

export const fetchRequest = async (id: string): Promise<HttpRequest> => {
  const response = await httpClient.get(`/requests/${id}`);
  return response.data;
};

export const createRequest = async (data: Partial<HttpRequest> & { collection_id: string; name: string }): Promise<HttpRequest> => {
  const response = await httpClient.post('/requests', data);
  return response.data;
};

export const updateRequest = async (
  id: string,
  data: Partial<HttpRequest>
): Promise<HttpRequest> => {
  const response = await httpClient.put(`/requests/${id}`, data);
  return response.data;
};

export const deleteRequest = async (id: string): Promise<void> => {
  await httpClient.delete(`/requests/${id}`);
};

// ============= Environment APIs =============

export const fetchEnvironments = async (workspaceId = 'default'): Promise<Environment[]> => {
  const response = await httpClient.get('/environments', { params: { workspace_id: workspaceId } });
  return response.data;
};

export const fetchActiveEnvironment = async (workspaceId = 'default'): Promise<Environment | null> => {
  const response = await httpClient.get('/environments/active', { params: { workspace_id: workspaceId } });
  return response.data;
};

export const createEnvironment = async (data: {
  name: string;
  workspace_id?: string;
  base_url?: string;
  variables?: Record<string, string>;
  is_active?: boolean;
}): Promise<Environment> => {
  const response = await httpClient.post('/environments', data);
  return response.data;
};

export const updateEnvironment = async (
  id: string,
  data: { name?: string; base_url?: string; variables?: Record<string, string>; is_active?: boolean }
): Promise<Environment> => {
  const response = await httpClient.put(`/environments/${id}`, data);
  return response.data;
};

export const activateEnvironment = async (id: string): Promise<Environment> => {
  const response = await httpClient.post(`/environments/${id}/activate`);
  return response.data;
};

export const deleteEnvironment = async (id: string): Promise<void> => {
  await httpClient.delete(`/environments/${id}`);
};

// ============= Send Request API =============

export const sendHttpRequest = async (data: SendRequestPayload): Promise<SendRequestResponse> => {
  const response = await httpClient.post('/send', data);
  return response.data;
};

// ============= History APIs =============

export const fetchHistory = async (limit = 50): Promise<RequestHistory[]> => {
  const response = await httpClient.get('/history', { params: { limit } });
  return response.data;
};

export const deleteHistoryItem = async (id: string): Promise<void> => {
  await httpClient.delete(`/history/${id}`);
};

export const clearHistory = async (): Promise<void> => {
  await httpClient.post('/history/clear');
};

// ============= Import/Export APIs =============

export const importPostman = async (collectionData: any, workspaceId = 'default'): Promise<ImportResult> => {
  const response = await httpClient.post('/import', collectionData, { params: { workspace_id: workspaceId } });
  return response.data;
};

export const importOpenApi = async (spec: string, collectionId: string): Promise<ImportResult> => {
  const response = await httpClient.post('/import/openapi', { spec, collection_id: collectionId });
  return response.data;
};

export const importCurl = async (curlCommand: string, collectionId: string, name: string): Promise<HttpRequest> => {
  const response = await httpClient.post('/import/curl', {
    curl_command: curlCommand,
    collection_id: collectionId,
    name,
  });
  return response.data;
};

/** 解析 cURL 命令（不落库，供快速填充） */
export const parseCurl = async (curlCommand: string): Promise<CurlParseResult> => {
  const response = await httpClient.post('/import/curl/parse', {
    curl_command: curlCommand,
    collection_id: '',
    name: '',
  });
  return response.data;
};

export interface ImportResult {
  success: boolean;
  imported_count: number;
  failed_count: number;
  errors: string[];
  collection_id?: string;
}

export interface CurlParseResult {
  method: string;
  url: string;
  headers: KeyValueItem[];
  params: KeyValueItem[];
  body?: string;
  body_type: string;
  auth_type: string;
  auth_config: Record<string, any>;
}

export const exportCollection = async (collectionId: string): Promise<any> => {
  const response = await httpClient.get(`/export/${collectionId}`);
  return response.data;
};

// ============= Request duplicate =============

export const duplicateRequest = async (
  request: HttpRequest,
  targetCollectionId: string,
): Promise<HttpRequest> => {
  // 序列化 form_data：去除 File 对象（不可 JSON 序列化），仅保留可序列化字段
  const serializedFormData = request.form_data?.map((entry) => ({
    key: entry.key,
    value: entry.type === 'file' ? entry.file?.name || entry.value : entry.value,
    type: entry.type,
    enabled: entry.enabled ?? true,
    description: entry.description,
  }));
  const response = await httpClient.post('/requests', {
    collection_id: targetCollectionId,
    name: `${request.name} (副本)`,
    method: request.method,
    url: request.url,
    headers: request.headers,
    params: request.params,
    body_type: request.body_type,
    body: request.body,
    form_data: serializedFormData,
    auth_type: request.auth_type,
    auth_config: request.auth_config,
    extract_variables: request.extract_variables,
    assertions: request.assertions,
    description: request.description || '',
    sort_order: 0,
  });
  return response.data;
};
