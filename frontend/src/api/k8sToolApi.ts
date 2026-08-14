/**
 * K8s 控制台工具 - API 客户端
 *
 * 提供连接配置 CRUD、K8s 资源查询、WebSocket URL 构造等功能
 * 复用现有 getAuthHeaders / getAuthToken 认证工具
 */

import { API_BASE_URL } from '../config/api';
import { getAuthHeaders, getAuthToken } from './authApi';
import type {
  K8sConnection,
  CreateK8sManualRequest,
  CreateK8sPasteRequest,
  UpdateK8sRequest,
  TestK8sConnectionResponse,
  K8sNamespaceInfo,
  K8sPodSummary,
  K8sPodDetail,
  K8sNodeSummary,
  K8sWorkloadSummary,
  K8sEventInfo,
  K8sPodMetrics,
} from '../components/Tools/K8sTool/types';

const K8S_API_URL = `${API_BASE_URL}/k8s-tool`;

// ============ 通用请求封装 ============

/**
 * 通用 HTTP 请求函数
 * 自动注入 Authorization 头，失败时抛出含错误详情的 Error
 */
async function request<T>(url: string, options: RequestInit = {}): Promise<T> {
  const defaultHeaders = getAuthHeaders() as Record<string, string>;
  let headers = { ...defaultHeaders, ...options.headers } as Record<string, string>;

  // 如果 body 是 FormData，删除 Content-Type，让浏览器自动设置 multipart/form-data boundary
  if (options.body instanceof FormData) {
    delete headers['Content-Type'];
  }

  const response = await fetch(url, { ...options, headers: headers as HeadersInit });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));

    // FastAPI 422 错误返回 { detail: [{ loc, msg, type }] }
    // 其他错误返回 { detail: "..." }
    let errorMessage = 'Unknown error';
    if (Array.isArray(error.detail)) {
      // 422 验证错误：提取所有错误消息
      errorMessage = error.detail.map((e: any) => e.msg || JSON.stringify(e)).join('; ');
    } else if (typeof error.detail === 'string') {
      errorMessage = error.detail;
    } else if (error.detail) {
      errorMessage = JSON.stringify(error.detail);
    }

    throw new Error(errorMessage);
  }

  return response.json();
}

// ============ 连接配置 CRUD ============

/** 获取当前用户所有 K8s 连接配置列表 */
export const getK8sConfigs = () =>
  request<K8sConnection[]>(`${K8S_API_URL}/configs`);

/** 上传 kubeconfig 文件创建连接（multipart/form-data） */
export const uploadKubeconfig = (file: File, namespaceFilter: string[] = []) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('namespace_filter', JSON.stringify(namespaceFilter));

  // request() 函数会自动检测 FormData 并删除 Content-Type
  return request<K8sConnection[]>(`${K8S_API_URL}/configs/upload`, {
    method: 'POST',
    body: formData,
  });
};

/** 粘贴 kubeconfig 文本创建连接 */
export const pasteKubeconfig = (data: CreateK8sPasteRequest) =>
  request<K8sConnection[]>(`${K8S_API_URL}/configs/paste`, {
    method: 'POST',
    body: JSON.stringify(data),
  });

/** 手动填写连接信息创建配置 */
export const createK8sManual = (data: CreateK8sManualRequest) =>
  request<K8sConnection>(`${K8S_API_URL}/configs/manual`, {
    method: 'POST',
    body: JSON.stringify(data),
  });

/** 更新连接配置（名称、命名空间过滤） */
export const updateK8sConfig = (data: UpdateK8sRequest) =>
  request<K8sConnection>(`${K8S_API_URL}/configs/update`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });

/** 更新连接配置的认证信息（敏感字段） */
export const updateK8sConfigAuth = (payload: {
  id: string;
  token?: string;
  client_cert?: string;
  client_key?: string;
  username?: string;
  password?: string;
  ca_cert?: string;
}) =>
  request<K8sConnection>(`${K8S_API_URL}/configs/update-auth`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });

/** 删除连接配置 */
export const deleteK8sConfig = (id: string) =>
  request<{ message: string }>(`${K8S_API_URL}/configs/delete`, {
    method: 'DELETE',
    body: JSON.stringify({ id }),
  });

/** 更新连接配置的排序顺序 */
export const updateK8sConfigSort = (configIds: string[]) =>
  request<{ message: string }>(`${K8S_API_URL}/configs/sort`, {
    method: 'POST',
    body: JSON.stringify({ config_ids: configIds }),
  });

/** 测试连接是否可达 */
export const testK8sConnection = (configId: string) =>
  request<TestK8sConnectionResponse>(
    `${K8S_API_URL}/configs/${encodeURIComponent(configId)}/test`,
    { method: 'POST' }
  );

// ============ 资源查询 ============

/** 获取集群所有 Namespace */
export const listNamespaces = (configId: string) =>
  request<K8sNamespaceInfo[]>(
    `${K8S_API_URL}/${encodeURIComponent(configId)}/namespaces`
  );

/** 获取指定 Namespace 下的 Pod 列表 */
export const listPods = (configId: string, namespace: string) =>
  request<K8sPodSummary[]>(
    `${K8S_API_URL}/${encodeURIComponent(configId)}/pods?namespace=${encodeURIComponent(namespace)}`
  );

/** 获取单个 Pod 的详细信息 */
export const getPodDetail = (configId: string, name: string, namespace: string) =>
  request<K8sPodDetail>(
    `${K8S_API_URL}/${encodeURIComponent(configId)}/pods/${encodeURIComponent(name)}?namespace=${encodeURIComponent(namespace)}`
  );

/** 获取单个 Pod 的 YAML 内容 */
export const getPodYaml = (configId: string, name: string, namespace: string) =>
  request<{ yaml: string }>(
    `${K8S_API_URL}/${encodeURIComponent(configId)}/pods/${encodeURIComponent(name)}/yaml?namespace=${encodeURIComponent(namespace)}`
  );

/** 获取集群所有 Node */
export const listNodes = (configId: string) =>
  request<K8sNodeSummary[]>(
    `${K8S_API_URL}/${encodeURIComponent(configId)}/nodes`
  );

/** 获取指定 Namespace 下的 Deployment 列表 */
export const listDeployments = (configId: string, namespace: string) =>
  request<K8sWorkloadSummary[]>(
    `${K8S_API_URL}/${encodeURIComponent(configId)}/deployments?namespace=${encodeURIComponent(namespace)}`
  );

/** 获取指定 Namespace 下的事件列表（可选 fieldSelector 过滤） */
export const listEvents = (configId: string, namespace: string, fieldSelector?: string) => {
  const params = new URLSearchParams({ namespace });
  if (fieldSelector) params.append('field_selector', fieldSelector);
  return request<K8sEventInfo[]>(
    `${K8S_API_URL}/${encodeURIComponent(configId)}/events?${params}`
  );
};

/** 获取 Pod 的实时 Metrics 指标（CPU/内存使用量） */
export const getPodMetrics = (configId: string, podName: string, namespace: string) =>
  request<K8sPodMetrics>(
    `${K8S_API_URL}/${encodeURIComponent(configId)}/pods/${encodeURIComponent(podName)}/metrics?namespace=${encodeURIComponent(namespace)}`
  );

// ============ WebSocket URL 构造 ============

/**
 * 将 HTTP(S) 基础 URL 转换为 WS(S) 协议
 * - 若 API_BASE_URL 以 http 开头，直接替换协议前缀
 * - 否则根据当前页面协议推断 ws/wss
 */
function toWsBase(): string {
  if (API_BASE_URL.startsWith('http')) {
    return API_BASE_URL.replace(/^http/, 'ws');
  }
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
  return `${protocol}://${window.location.host}${API_BASE_URL}`;
}

/** 构造 Pod 日志 WebSocket 连接 URL */
export const buildLogsWebSocketUrl = (
  configId: string,
  podName: string,
  namespace: string,
  container?: string,
  tailLines: number = 100,
  follow: boolean = true,
): string => {
  const token = getAuthToken();
  const params = new URLSearchParams({
    namespace,
    tail_lines: String(tailLines),
    follow: String(follow),
    token: token || '',
  });
  if (container) params.append('container', container);

  return `${toWsBase()}/k8s-tool/${encodeURIComponent(configId)}/ws/pods/${encodeURIComponent(podName)}/logs?${params}`;
};

/** 下载容器完整日志 */
export const downloadPodLogs = async (
  configId: string,
  podName: string,
  namespace: string,
  container?: string,
): Promise<string> => {
  const params = new URLSearchParams({ namespace });
  if (container) params.append('container', container);

  const response = await fetch(
    `${K8S_API_URL}/${encodeURIComponent(configId)}/pods/${encodeURIComponent(podName)}/logs/download?${params}`,
    { headers: getAuthHeaders() }
  );
  if (!response.ok) {
    throw new Error(`下载日志失败：${response.status}`);
  }
  return response.text();
};

/** 构造 Pod Exec WebSocket 连接 URL */
export const buildExecWebSocketUrl = (
  configId: string,
  podName: string,
  namespace: string,
  container?: string,
  command: string = '/bin/sh',
): string => {
  const token = getAuthToken();
  const params = new URLSearchParams({
    namespace,
    command,
    token: token || '',
  });
  if (container) params.append('container', container);

  return `${toWsBase()}/k8s-tool/${encodeURIComponent(configId)}/ws/pods/${encodeURIComponent(podName)}/exec?${params}`;
};
