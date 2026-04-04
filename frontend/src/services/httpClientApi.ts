/**
 * HTTP Client API 服务
 */

import axios from 'axios';
import { API_BASE_URL } from '../config/api';

const httpClient = axios.create({
  baseURL: `${API_BASE_URL}/http-client`,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器 - 添加 JWT token
httpClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ============= Types =============

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
  headers: Record<string, string>;
  params: Record<string, string>;
  body_type: 'json' | 'form' | 'raw' | 'none';
  body?: string;
  auth_type: 'bearer' | 'basic' | 'apikey' | 'none';
  auth_config: Record<string, any>;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export interface Environment {
  id: string;
  name: string;
  workspace_id: string;
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
  headers: Record<string, string>;
  params: Record<string, string>;
  body_type?: 'json' | 'form' | 'raw' | 'none';
  body?: string;
  timeout?: number;
  follow_redirects?: boolean;
}

export interface SendRequestResponse {
  status_code: number;
  headers: Record<string, string>;
  body: string;
  response_time: number;
  content_type?: string;
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
  data: { name?: string; description?: string; sort_order?: number }
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

export const createRequest = async (data: Omit<HttpRequest, 'id' | 'created_at' | 'updated_at'>): Promise<HttpRequest> => {
  const response = await httpClient.post('/requests', data);
  return response.data;
};

export const updateRequest = async (
  id: string,
  data: Partial<Omit<HttpRequest, 'id' | 'created_at' | 'updated_at'>>
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
  variables?: Record<string, string>;
  is_active?: boolean;
}): Promise<Environment> => {
  const response = await httpClient.post('/environments', data);
  return response.data;
};

export const updateEnvironment = async (
  id: string,
  data: { name?: string; variables?: Record<string, string>; is_active?: boolean }
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

export const clearHistory = async (): Promise<void> => {
  await httpClient.post('/history/clear');
};
