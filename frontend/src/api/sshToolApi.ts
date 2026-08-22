import { API_BASE_URL } from '../config/api';
import { getAuthHeaders } from './authApi';
import { authedFetch } from './http';

const SSH_API_URL = `${API_BASE_URL}/ssh-tool`;

export interface SSHConfig {
  id: string;
  alias: string;
  host: string;
  port: number;
  username: string;
  group_name?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CreateSSHRequest {
  alias: string;
  host: string;
  port: number;
  username: string;
  password?: string;
  private_key?: string;
  passphrase?: string;
  group_name?: string;
}

export interface UpdateSSHRequest extends Partial<CreateSSHRequest> {
  id: string;
  is_active?: boolean;
}

export interface TestSSHConnectionRequest {
  host: string;
  port: number;
  username: string;
  password?: string;
  private_key?: string;
  passphrase?: string;
}

export interface TestSSHConnectionResponse {
  success: boolean;
  message?: string;
}

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

export const getSSHConfigs = () => {
  return request<SSHConfig[]>(`${SSH_API_URL}/configs`);
};

export const createSSHConfig = (data: CreateSSHRequest) => {
  return request<SSHConfig>(`${SSH_API_URL}/configs`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
};

export const updateSSHConfig = (data: UpdateSSHRequest) => {
  return request<SSHConfig>(`${SSH_API_URL}/configs/update`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
};

export const deleteSSHConfig = (id: string) => {
  return request<{ message: string }>(`${SSH_API_URL}/configs/delete`, {
    method: 'DELETE',
    body: JSON.stringify({ id }),
  });
};

export const testSSHConnection = (data: TestSSHConnectionRequest) => {
  return request<TestSSHConnectionResponse>(`${SSH_API_URL}/test-connection`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
};

export const buildSSHWebSocketUrl = (configId: string, token: string, cols: number, rows: number) => {
  if (API_BASE_URL.startsWith('http')) {
    const wsBase = API_BASE_URL.replace(/^http/, 'ws');
    return `${wsBase}/ssh-tool/ws?configId=${encodeURIComponent(configId)}&token=${encodeURIComponent(token)}&cols=${cols}&rows=${rows}`;
  }
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
  const wsBase = `${protocol}://${window.location.host}${API_BASE_URL}`;
  return `${wsBase}/ssh-tool/ws?configId=${encodeURIComponent(configId)}&token=${encodeURIComponent(token)}&cols=${cols}&rows=${rows}`;
};
