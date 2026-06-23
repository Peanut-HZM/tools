/** GLM-Coding Pro 抢购工具 API */

const BASE_URL = '/api/glm-coding-rusher';

export interface RusherConfig {
  target_package: string;
  sale_time: string;
  preheat_seconds: number;
  refresh_interval_ms: number;
  timeout_seconds: number;
  headless: boolean;
}

export interface LoginStatus {
  logged_in: boolean;
  state_file_exists: boolean;
  login_time?: string;
  message: string;
}

export interface RusherStatus {
  is_running: boolean;
  current_phase: 'idle' | 'preheating' | 'refreshing' | 'clicking' | 'success' | 'failed';
  message: string;
  next_sale_time?: string;
  countdown_seconds?: number;
  last_error?: string;
}

export interface RusherLog {
  id: string;
  task_id: string;
  phase: string;
  message: string;
  created_at: string;
}

export interface LogListResponse {
  items: RusherLog[];
  total: number;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

/** 启动登录浏览器 */
export async function startLogin(headless = false): Promise<{ success: boolean; message: string }> {
  return request('/login', {
    method: 'POST',
    body: JSON.stringify({ headless }),
  });
}

/** 检查登录状态 */
export async function getLoginStatus(): Promise<LoginStatus> {
  return request('/login-status');
}

/** 保存配置 */
export async function saveConfig(config: Partial<RusherConfig>): Promise<RusherConfig> {
  return request('/config', {
    method: 'POST',
    body: JSON.stringify(config),
  });
}

/** 获取当前配置 */
export async function getConfig(): Promise<RusherConfig> {
  return request('/config');
}

/** 启动抢购 */
export async function startRush(): Promise<{ success: boolean; message: string; task_id: string }> {
  return request('/start', { method: 'POST' });
}

/** 停止抢购 */
export async function stopRush(): Promise<{ success: boolean; message: string }> {
  return request('/stop', { method: 'POST' });
}

/** 获取状态 */
export async function getStatus(): Promise<RusherStatus> {
  return request('/status');
}

/** 获取日志 */
export async function getLogs(limit = 100): Promise<LogListResponse> {
  return request(`/logs?limit=${limit}`);
}

export interface PaymentInfo {
  has_payment: boolean;
  payment_url: string | null;
  browser_alive: boolean;
  message: string;
}

/** 获取支付信息 */
export async function getPaymentInfo(): Promise<PaymentInfo> {
  return request('/payment-info');
}

/** 关闭支付浏览器 */
export async function closePaymentBrowser(): Promise<{ success: boolean; message: string }> {
  return request('/close-payment', { method: 'POST' });
}

export interface TaskSummary {
  id: string;
  result: string;
  target_package: string;
  started_at: string;
  ended_at: string | null;
  refresh_count: number;
  payment_url: string | null;
}

export interface TaskDetail extends TaskSummary {
  config_snapshot: Record<string, unknown>;
}

export interface TaskListResponse {
  items: TaskSummary[];
  total: number;
}

/** 获取抢购任务记录列表 */
export async function getTasks(limit = 50): Promise<TaskListResponse> {
  return request(`/tasks?limit=${limit}`);
}

/** 获取指定任务的日志（从 DB） */
export async function getTaskLogs(taskId: string, limit = 500): Promise<LogListResponse> {
  return request(`/tasks/${taskId}/logs?limit=${limit}`);
}
