/**
 * K8s 控制台工具 - 类型定义
 *
 * 对应后端 k8s_tool_models.py 中的模型字段
 */

// K8s 连接配置
export interface K8sConnection {
  id: string;
  user_id: string;
  name: string;
  source_type: 'kubeconfig_file' | 'kubeconfig_text' | 'manual';
  cluster_name: string;
  context_name: string;
  server: string;
  auth_type: 'bearer_token' | 'client_cert' | 'basic_auth';
  has_auth_data: boolean;
  has_ca_cert: boolean;
  namespace_filter: string[];
  is_metrics_available: boolean;
  last_test_at: string | null;
  last_test_error: string | null;
  created_at: string;
  updated_at: string;
}

// 手动创建连接请求
export interface CreateK8sManualRequest {
  name: string;
  server: string;
  auth_type: 'bearer_token' | 'client_cert' | 'basic_auth';
  token?: string;
  client_cert?: string;
  client_key?: string;
  username?: string;
  password?: string;
  ca_cert?: string;
  namespace_filter?: string[];
}

// 粘贴 kubeconfig 文本创建请求
export interface CreateK8sPasteRequest {
  kubeconfig_text: string;
  namespace_filter?: string[];
}

// 更新连接配置请求
export interface UpdateK8sRequest {
  id: string;
  name?: string;
  namespace_filter?: string[];
}

// 连接测试结果
export interface TestK8sConnectionResponse {
  reachable: boolean;
  server_version?: string;
  is_metrics_available: boolean;
}

// Namespace 信息
export interface K8sNamespaceInfo {
  name: string;
  status: string;
  created_at?: string;
}

// Pod 摘要（列表用）
export interface K8sPodSummary {
  name: string;
  namespace: string;
  status: string;
  phase: string;
  ready: string;
  restarts: number;
  node: string;
  pod_ip?: string;
  created_at?: string;
  containers: string[];
}

// Pod 详情
export interface K8sPodDetail {
  name: string;
  namespace: string;
  uid: string;
  phase: string;
  status: string;
  node: string;
  pod_ip?: string;
  host_ip?: string;
  qos_class?: string;
  created_at?: string;
  labels: Record<string, string>;
  annotations: Record<string, string>;
  containers: K8sContainerInfo[];
  init_containers: K8sContainerInfo[];
  conditions: K8sCondition[];
  owner_references: K8sOwnerReference[];
}

// 容器信息
export interface K8sContainerInfo {
  name: string;
  image: string;
  ready: boolean;
  state: 'running' | 'waiting' | 'terminated' | 'unknown';
  state_detail: string;
  restart_count: number;
  started_at?: string;
  resources_requests: Record<string, string>;
  resources_limits: Record<string, string>;
}

// K8s 资源状态条件
export interface K8sCondition {
  type: string;
  status: string;
  reason?: string;
  message?: string;
  last_transition_time?: string;
}

// 资源属主引用
export interface K8sOwnerReference {
  kind: string;
  name: string;
  uid: string;
}

// Node 摘要
export interface K8sNodeSummary {
  name: string;
  status: string;
  roles: string[];
  version: string;
  os_image: string;
  kernel_version: string;
  container_runtime: string;
  created_at?: string;
  conditions: K8sCondition[];
  capacity_cpu?: string;
  capacity_memory?: string;
}

// 工作负载摘要（Deployment / StatefulSet / DaemonSet 等）
export interface K8sWorkloadSummary {
  name: string;
  namespace: string;
  kind: string;
  ready: string;
  desired: number;
  available: number;
  images: string[];
  created_at?: string;
  labels: Record<string, string>;
}

// 事件信息
export interface K8sEventInfo {
  type: 'Normal' | 'Warning';
  reason: string;
  message: string;
  object_kind: string;
  object_name: string;
  object_namespace: string;
  count: number;
  first_seen?: string;
  last_seen?: string;
}

// K8s API 错误
export interface K8sError {
  code: string;
  message: string;
  k8s_reason: string;
  status_code?: number;
}

// ============ Metrics 指标相关类型 ============

// 单个容器的 CPU/内存使用量
export interface K8sMetricsContainer {
  name: string;
  // 原始值（如 "100m"、"256Mi"），前端解析为数值用于图表展示
  cpu_usage: string;
  memory_usage: string;
}

// Pod 级别 Metrics 快照
export interface K8sPodMetrics {
  pod_name: string;
  namespace: string;
  timestamp: string;
  containers: K8sMetricsContainer[];
}

// Pod 分页列表响应
export interface PaginatedPodsResponse {
  items: K8sPodSummary[];
  total: number;
}
