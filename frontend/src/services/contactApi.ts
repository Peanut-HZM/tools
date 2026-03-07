/**
 * Contact Message API Service
 */
import axios from 'axios';
import { getAuthToken } from '../api/authApi';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

const getAuthHeaders = () => {
  const token = getAuthToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
};

const api = {
  post: async (url: string, data?: any) => {
    const response = await axios.post(`${API_BASE_URL}${url}`, data, { headers: getAuthHeaders() });
    return response.data;
  },
  get: async (url: string, params?: any) => {
    const response = await axios.get(`${API_BASE_URL}${url}`, { params, headers: getAuthHeaders() });
    return response.data;
  },
  patch: async (url: string, data?: any) => {
    const response = await axios.patch(`${API_BASE_URL}${url}`, data, { headers: getAuthHeaders() });
    return response.data;
  },
  delete: async (url: string) => {
    const response = await axios.delete(`${API_BASE_URL}${url}`, { headers: getAuthHeaders() });
    return response.data;
  },
};

export interface ContactMessage {
  id: string;
  name: string;
  email: string;
  subject: string | null;
  content: string;
  status: 'unread' | 'read' | 'processing' | 'resolved';
  admin_reply: string | null;
  ip_address: string | null;
  created_at: string;
  updated_at: string;
}

export interface ContactMessageCreate {
  name: string;
  email: string;
  subject?: string;
  content: string;
}

export interface ContactMessageUpdate {
  status?: 'unread' | 'read' | 'processing' | 'resolved';
  admin_reply?: string;
}

export interface ContactMessageListResponse {
  items: ContactMessage[];
  total: number;
  page: number;
  page_size: number;
}

/**
 * Submit a contact message (public API)
 */
export const submitContactMessage = async (data: ContactMessageCreate): Promise<ContactMessage> => {
  const response = await api.post('/contact', data);
  return response;
};

/**
 * Get all contact messages (admin only)
 */
export const getContactMessages = async (
  page: number = 1,
  page_size: number = 20,
  status?: string,
  keyword?: string
): Promise<ContactMessageListResponse> => {
  const params: Record<string, string | number> = { page, page_size };
  if (status) params.status = status;
  if (keyword) params.keyword = keyword;

  const response = await api.get('/admin/contact-messages', { params });
  return response;
};

/**
 * Get a single contact message (admin only)
 */
export const getContactMessage = async (id: string): Promise<ContactMessage> => {
  const response = await api.get(`/admin/contact-messages/${id}`);
  return response;
};

/**
 * Update a contact message (admin only)
 */
export const updateContactMessage = async (
  id: string,
  data: ContactMessageUpdate
): Promise<ContactMessage> => {
  const response = await api.patch(`/admin/contact-messages/${id}`, data);
  return response;
};

/**
 * Delete a contact message (admin only)
 */
export const deleteContactMessage = async (id: string): Promise<{ message: string }> => {
  const response = await api.delete(`/admin/contact-messages/${id}`);
  return response;
};

/**
 * Batch update message status (admin only)
 */
export const batchUpdateMessageStatus = async (
  message_ids: string[],
  status: 'unread' | 'read' | 'processing' | 'resolved'
): Promise<{ message: string; updated_count: number }> => {
  const response = await api.post('/admin/contact-messages/batch-update', {
    message_ids,
    status,
  });
  return response;
};

/**
 * Batch delete messages (admin only)
 */
export const batchDeleteMessages = async (
  message_ids: string[]
): Promise<{ message: string; deleted_count: number }> => {
  const response = await api.post('/admin/contact-messages/batch-delete', {
    message_ids,
  });
  return response;
};
