/**
 * 图像生成 API 层
 *
 * 对应后端路由 POST/GET /api/image-generation/*
 * 使用 authedFetch + getAuthHeaders 鉴权模式
 */

import { API_BASE_URL } from '../config/api';
import { getAuthHeaders } from './authApi';
import { authedFetch } from './http';

const BASE_URL = `${API_BASE_URL}/image-generation`;

/* ================================================================
 * 类型定义
 * ================================================================ */

export type Operation = 'text2img' | 'img2img' | 'inpaint' | 'upload_edit';

export type EditType =
  | 'upscale'
  | 'denoise'
  | 'relight'
  | 'style_transfer'
  | 'background_remove';

export type ModelPreference =
  | 'auto'
  | 'doubao_seedream'
  | 'qwen_image'
  | 'dall_e_3'
  | 'sdxl';

export type ImageSize =
  | '1024x1024'
  | '1024x1792'
  | '1792x1024'
  | '512x512'
  | '768x768';

/** generate 请求参数 */
export interface GenerateParams {
  operation: Operation;
  prompt: string;
  size?: ImageSize;
  n?: number;
  style?: string;
  strength?: number;
  model_preference?: ModelPreference;
  polish_prompt?: boolean;
  reference_image?: File | null;
  mask_image?: File | null;
  edit_type?: EditType;
}

/** generate 响应 */
export interface GenerateResponse {
  history_id: string;
  image_urls: string[];
  model_used: string;
  duration_ms: number;
  operation: Operation;
  prompt: string;
}

/** polish-prompt 响应 */
export interface PolishPromptResponse {
  polished_prompt: string;
  was_polished: boolean;
}

/** 历史记录条目 */
export interface HistoryItem {
  id: string;
  user_id: string;
  operation: Operation;
  prompt: string;
  params: Record<string, any>;
  reference_oss_key: string | null;
  mask_oss_key: string | null;
  result_oss_key: string | null;
  result_width: number | null;
  result_height: number | null;
  model_used: string | null;
  status: 'success' | 'failed' | 'cancelled';
  error_message: string | null;
  duration_ms: number | null;
  is_deleted: boolean;
  last_accessed_at: string | null;
  created_at: string | null;
}

/** 历史列表响应 */
export interface HistoryListResponse {
  items: HistoryItem[];
  skip: number;
  limit: number;
  count: number;
}

/** 配额信息 */
export interface QuotaInfo {
  daily_limit: number;
  daily_used: number;
  daily_remaining: number;
  monthly_limit: number;
  monthly_used: number;
  monthly_remaining: number;
  valid_from?: string | null;
  valid_until?: string | null;
}

/** result/{history_id} 响应 */
export interface ResultResponse {
  history_id: string;
  result_url: string;
  status: string;
}

/* ================================================================
 * 工具函数
 * ================================================================ */

async function readError(response: Response, fallback: string): Promise<Error> {
  const error = await response.json().catch(() => ({ detail: response.statusText }));
  const msg =
    typeof error.detail === 'string'
      ? error.detail
      : error.detail?.message || error.message || fallback;
  return new Error(msg);
}

/* ================================================================
 * API 函数
 * ================================================================ */

/**
 * 生成图像 — POST /image-generation/generate
 * multipart/form-data，支持 AbortController signal
 */
export async function generate(
  params: GenerateParams,
  signal?: AbortSignal,
): Promise<GenerateResponse> {
  const formData = new FormData();
  formData.append('operation', params.operation);
  formData.append('prompt', params.prompt);
  formData.append('size', params.size || '1024x1024');
  formData.append('n', String(params.n ?? 1));
  formData.append('model_preference', params.model_preference || 'auto');
  formData.append('polish_prompt', String(params.polish_prompt ?? false));

  if (params.style) formData.append('style', params.style);
  if (params.strength !== undefined) formData.append('strength', String(params.strength));
  if (params.edit_type) formData.append('edit_type', params.edit_type);
  if (params.reference_image) formData.append('reference_image', params.reference_image);
  if (params.mask_image) formData.append('mask_image', params.mask_image);

  const token = localStorage.getItem('auth_token');
  const headers: Record<string, string> = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;
  // 不手动设 Content-Type，让浏览器自动设 multipart boundary

  const response = await fetch(`${BASE_URL}/generate`, {
    method: 'POST',
    headers,
    body: formData,
    signal,
  });

  if (!response.ok) {
    throw await readError(response, '图像生成失败');
  }
  return response.json();
}

/**
 * 润色提示词 — POST /image-generation/polish-prompt
 */
export async function polishPrompt(
  prompt: string,
  operation: Operation = 'text2img',
): Promise<PolishPromptResponse> {
  const formData = new FormData();
  formData.append('prompt', prompt);
  formData.append('operation', operation);

  const token = localStorage.getItem('auth_token');
  const headers: Record<string, string> = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const response = await fetch(`${BASE_URL}/polish-prompt`, {
    method: 'POST',
    headers,
    body: formData,
  });

  if (!response.ok) {
    throw await readError(response, '提示词润色失败');
  }
  return response.json();
}

/**
 * 历史列表 — GET /image-generation/history
 */
export async function getHistory(
  skip = 0,
  limit = 20,
  operation?: Operation,
): Promise<HistoryListResponse> {
  const search = new URLSearchParams();
  search.set('skip', String(skip));
  search.set('limit', String(limit));
  if (operation) search.set('operation', operation);

  const response = await authedFetch(`${BASE_URL}/history?${search.toString()}`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    throw await readError(response, '获取历史记录失败');
  }
  return response.json();
}

/**
 * 历史详情 — GET /image-generation/history/{id}
 */
export async function getHistoryDetail(historyId: string): Promise<HistoryItem> {
  const response = await authedFetch(`${BASE_URL}/history/${historyId}`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    throw await readError(response, '获取历史详情失败');
  }
  return response.json();
}

/**
 * 删除历史 — DELETE /image-generation/history/{id}
 */
export async function deleteHistory(historyId: string): Promise<{ success: boolean; history_id: string }> {
  const response = await authedFetch(`${BASE_URL}/history/${historyId}`, {
    method: 'DELETE',
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    throw await readError(response, '删除历史记录失败');
  }
  return response.json();
}

/**
 * 获取配额 — GET /image-generation/quota/me
 */
export async function getMyQuota(): Promise<QuotaInfo> {
  const response = await authedFetch(`${BASE_URL}/quota/me`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    throw await readError(response, '获取配额信息失败');
  }
  return response.json();
}

/**
 * 获取结果图签名 URL — GET /image-generation/result/{history_id}
 */
export async function getResultUrl(historyId: string): Promise<ResultResponse> {
  const response = await authedFetch(`${BASE_URL}/result/${historyId}`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    throw await readError(response, '获取结果图片失败');
  }
  return response.json();
}

/* ================================================================
 * 对话式生成（Task 9 stub — Task 10 将替换实现）
 * ================================================================ */

/** 对话式生成请求参数 */
export interface ChatParams {
  size?: ImageSize;
  n?: number;
  style?: string;
  strength?: number;
  model_preference?: ModelPreference;
  polish_prompt?: boolean;
  edit_type?: EditType;
  referenceImage?: File | null;
  maskImage?: File | null;
}

/** 对话式生成响应 */
export interface ChatResult {
  conversation_id: string;
  answer: string;
  image_urls: string[];
  status: 'asking' | 'generated';
  history_id?: string;
  model_used?: string;
}

/**
 * 对话式生成 — POST /image-generation/chat
 */
export async function chatGenerate(
  operation: Operation,
  prompt: string,
  conversationId: string | null,
  params?: ChatParams,
  referenceImage?: File | null,
  maskImage?: File | null,
): Promise<ChatResult> {
  const formData = new FormData();
  formData.append('operation', operation);
  formData.append('prompt', prompt);
  if (conversationId) formData.append('conversation_id', conversationId);
  if (params?.size) formData.append('size', params.size);
  if (params?.n) formData.append('n', String(params.n));
  if (params?.style) formData.append('style', params.style);
  if (params?.strength !== undefined) formData.append('strength', String(params.strength));
  if (params?.model_preference) formData.append('model_preference', params.model_preference);
  if (params?.edit_type) formData.append('edit_type', params.edit_type);
  if (referenceImage) formData.append('reference_image', referenceImage);
  if (maskImage) formData.append('mask_image', maskImage);

  const response = await authedFetch(`${BASE_URL}/chat`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: formData,
  });

  if (!response.ok) {
    throw await readError(response, '对话失败');
  }
  return response.json();
}
