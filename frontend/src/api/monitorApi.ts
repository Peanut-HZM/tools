// frontend/src/api/monitorApi.ts
import { API_BASE_URL } from '../config/api';
import { getAuthHeaders } from './authApi';

const MONITOR_API_URL = `${API_BASE_URL}/monitor`;

export interface MonitorServerMetric {
  cpu_percent: number | null;
  mem_percent: number | null;
  disk_percent: number | null;
  net_recv_rate: number | null;
  net_sent_rate: number | null;
  disk_read_rate: number | null;
  disk_write_rate: number | null;
  /** 以下字段仅本机采集提供，SSH 远端可能缺失 */
  cpu_per_core?: number[] | null;
  load_avg?: number[] | null;
  mem_total?: number | null;
  mem_used?: number | null;
  swap_percent?: number | null;
  disk_total?: number | null;
  disk_used?: number | null;
  process_count?: number | null;
  uptime_seconds?: number | null;
}

export interface MonitorServer {
  id: string;
  user_id: string;
  name: string;
  server_type: 'local' | 'ssh';
  host: string;
  port: number;
  username: string;
  group_name?: string | null;
  status: string;
  last_error?: string | null;
  last_seen_at?: string | null;
  created_at: string;
  metric?: MonitorServerMetric | null;
}

export interface CreateMonitorServerRequest {
  name: string;
  server_type?: string;
  host?: string;
  port?: number;
  username?: string;
  password?: string;
  private_key?: string;
  passphrase?: string;
  group_name?: string;
}

export interface MetricPoint {
  collected_at: string;
  cpu_percent?: number | null;
  cpu_per_core?: number[] | null;
  load_avg?: number[] | null;
  mem_percent?: number | null;
  mem_total?: number | null;
  mem_used?: number | null;
  swap_percent?: number | null;
  swap_total?: number | null;
  swap_used?: number | null;
  disk_percent?: number | null;
  disk_total?: number | null;
  disk_used?: number | null;
  net_recv_rate?: number | null;
  net_sent_rate?: number | null;
  disk_read_rate?: number | null;
  disk_write_rate?: number | null;
  process_count?: number | null;
  uptime_seconds?: number | null;
}

export interface AlertRule {
  id: string;
  user_id: string;
  server_id: string;
  metric: string;
  operator: string;
  threshold: number;
  duration: number;
  enabled: boolean;
  created_at: string;
}

export interface AlertLog {
  id: number;
  rule_id: string;
  server_id: string;
  server_name: string;
  metric: string;
  actual_value: number;
  status: 'firing' | 'recovered';
  is_read: boolean;
  notified_at: string;
}

export interface ServiceInfo {
  name: string;
  load: string;
  active: string;
  state: string;
  description: string;
  enabled: boolean;
}

export interface MonitorSettings {
  webhook_url: string;
  collect_interval: number;
}

async function request<T>(url: string, options: RequestInit = {}): Promise<T> {
  const headers = {
    ...getAuthHeaders(),
    ...options.headers,
  } as HeadersInit;
  const response = await fetch(url, { ...options, headers });
  // 401 时触发全局登录弹窗（与 authedFetch 保持一致）
  if (response.status === 401) {
    const handler = (window as any).__authFailureHandler;
    if (handler) handler();
  }
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: '未知错误' }));
    throw new Error(error.detail || `请求失败 (${response.status})`);
  }
  return response.json() as Promise<T>;
}

// 泛型参数：interface 类型（如 ProcessParams）无隐式索引签名，无法赋给 Record，故用泛型兼容
function buildQuery<T extends object>(params: T): string {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== '') search.append(key, String(value));
  });
  const qs = search.toString();
  return qs ? `?${qs}` : '';
}

export const getServers = () => request<MonitorServer[]>(`${MONITOR_API_URL}/servers`);

/** 从 SSH 工具同步全部服务器（幂等） */
export interface SshSyncItem {
  sshConfigId: string;
  name: string;
  action: 'created' | 'updated' | 'unchanged' | 'disabled' | 'failed';
  fields?: string[];
  reason?: string;
}
export interface SshSyncResult {
  sshTotal: number;
  created: number;
  updated: number;
  disabled: number;
  unchanged: number;
  items: SshSyncItem[];
}
export const syncServersFromSsh = () =>
  request<SshSyncResult>(`${MONITOR_API_URL}/servers/sync-ssh`, { method: 'POST' });
export const createServer = (data: CreateMonitorServerRequest) =>
  request<MonitorServer>(`${MONITOR_API_URL}/servers`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
  });
export const updateServer = (id: string, data: Partial<CreateMonitorServerRequest>) =>
  request<MonitorServer>(`${MONITOR_API_URL}/servers/${id}`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
  });
export const deleteServer = (id: string) =>
  request<{ success: boolean }>(`${MONITOR_API_URL}/servers/${id}`, { method: 'DELETE' });
export const importFromSsh = (sshConfigId: string) =>
  request<MonitorServer>(`${MONITOR_API_URL}/servers/import-ssh`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ssh_config_id: sshConfigId }),
  });
export const retryServer = (id: string) =>
  request<{ success: boolean }>(`${MONITOR_API_URL}/servers/${id}/retry`, { method: 'POST' });
export const testServerConnection = (data: Omit<CreateMonitorServerRequest, 'name' | 'server_type'>) =>
  request<{ success: boolean; message: string }>(`${MONITOR_API_URL}/servers/test`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
  });

export const getOverview = (serverId: string) =>
  request<{ server: MonitorServer; metric: MetricPoint | null }>(
    `${MONITOR_API_URL}/servers/${serverId}/overview`);
export const getMetrics = (serverId: string, range: string) =>
  request<{ server_id: string; range: string; points: MetricPoint[] }>(
    `${MONITOR_API_URL}/servers/${serverId}/metrics${buildQuery({ range })}`);
export const getPartitions = (serverId: string) =>
  request<{ partitions: Array<{ device: string; mountpoint: string; fstype: string; total: number; used: number; free: number; percent: number }> }>(
    `${MONITOR_API_URL}/servers/${serverId}/partitions`);
export const getSystemInfo = (serverId: string) =>
  request<Record<string, string | number>>(`${MONITOR_API_URL}/servers/${serverId}/system-info`);

export interface ProcessParams {
  sort_by?: string;
  sort_order?: string;
  search?: string;
  project_type?: string;
  page?: number;
  page_size?: number;
}

export interface MonitorProcess {
  pid: number;
  name: string;
  username: string;
  status: string;
  cpu_percent: number;
  memory_percent: number;
  memory_rss: number;
  memory_vms: number;
  num_threads: number;
  create_time: string;
  command_line: string;
  project_type: string;
}

/** 按类型聚合（份额之和等于进程总量） */
export interface ProcessTypeSummary {
  type: string;
  count: number;
  cpu_percent: number;
  memory_percent: number;
  memory_rss: number;
}

/** 顶部总览：全量口径，不受分页影响 */
export interface ProcessSummary {
  process_count: number;
  /** 各进程 CPU 之和（单核 100% 口径，多核可 >100） */
  cpu_percent_total: number;
  /** 换算成整机占用率（已除以逻辑核数） */
  cpu_percent_of_machine: number;
  memory_rss_total: number;
  memory_percent_total: number;
  thread_count_total: number;
  logical_cpus: number;
  top_cpu: { pid: number; name: string; cpu_percent: number; project_type: string }[];
  top_memory: { pid: number; name: string; memory_rss: number; project_type: string }[];
}

export interface ProcessListResponse {
  processes: MonitorProcess[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  type_summary?: ProcessTypeSummary[];
  summary?: ProcessSummary;
}

export const getProcesses = (serverId: string, params: ProcessParams = {}) =>
  request<ProcessListResponse>(
    `${MONITOR_API_URL}/servers/${serverId}/processes${buildQuery(params)}`);
export const killProcess = (serverId: string, pid: number) =>
  request<{ success: boolean; pid: number }>(
    `${MONITOR_API_URL}/servers/${serverId}/processes/${pid}/kill`, { method: 'POST' });

export const getServices = (serverId: string) =>
  request<{ services: ServiceInfo[] }>(`${MONITOR_API_URL}/servers/${serverId}/services`);
export const serviceAction = (serverId: string, unit: string, action: 'start' | 'stop' | 'restart') =>
  request<{ success: boolean; message: string }>(
    `${MONITOR_API_URL}/servers/${serverId}/services/${encodeURIComponent(unit)}/action`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action }),
    });
export const getPrivileges = (serverId: string) =>
  request<{ sudo_available: boolean }>(`${MONITOR_API_URL}/servers/${serverId}/privileges`);

export interface AlertRulePayload {
  server_id: string;
  metric: string;
  operator: string;
  threshold: number;
  duration: number;
  enabled?: boolean;
}

// 契约校验：形状不符就抛错。
// 组件把返回值直接放进 state 后会在渲染期读 .length，若此处不校验，
// 一次接口异常就会让整个页面白屏崩溃且无任何提示；抛错后由调用方 catch 显示错误。
export const getAlerts = async (): Promise<AlertRule[]> => {
  const data = await request<AlertRule[]>(`${MONITOR_API_URL}/alerts`);
  if (!Array.isArray(data)) {
    throw new Error('告警规则数据格式异常');
  }
  return data;
};
export const createAlert = (data: AlertRulePayload) =>
  request<AlertRule>(`${MONITOR_API_URL}/alerts`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
  });
export const updateAlert = (id: string, data: Partial<AlertRulePayload>) =>
  request<AlertRule>(`${MONITOR_API_URL}/alerts/${id}`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
  });
export const deleteAlert = (id: string) =>
  request<{ success: boolean }>(`${MONITOR_API_URL}/alerts/${id}`, { method: 'DELETE' });
export const getAlertLogs = async (page = 1, pageSize = 20) => {
  const data = await request<{ logs: AlertLog[]; total: number; unread_count: number; page: number; page_size: number }>(
    `${MONITOR_API_URL}/alerts/logs${buildQuery({ page, page_size: pageSize })}`);
  if (!data || !Array.isArray(data.logs)) {
    throw new Error('告警记录数据格式异常');
  }
  return data;
};
export const markAlertLogsRead = () =>
  request<{ success: boolean }>(`${MONITOR_API_URL}/alerts/logs/read`, { method: 'PUT' });

export const getSettings = () => request<MonitorSettings>(`${MONITOR_API_URL}/settings`);
export const saveSettings = (data: MonitorSettings) =>
  request<{ success: boolean }>(`${MONITOR_API_URL}/settings`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
  });
