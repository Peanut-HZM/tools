import { API_BASE_URL } from '../config/api';
import { getAuthHeaders } from './authApi';
import { authedFetch } from './http';

const BASE_URL = `${API_BASE_URL}/subscription-quota`;

export type CredentialStatus =
  | 'valid'
  | 'expired'
  | 'refresh_pending'
  | 'not_found'
  | 'parse_error';

export interface QuotaTierDto {
  name: string;
  utilization: number;
  resetsAt: string | null;
  usedValueUsd?: number | null;
  maxValueUsd?: number | null;
}

export interface SubscriptionQuotaDto {
  tool: string;
  credentialStatus: CredentialStatus;
  credentialMessage: string | null;
  success: boolean;
  tiers: QuotaTierDto[];
  planName: string | null;
  error: string | null;
  queriedAt: number | null;
}

export interface ProviderInfo {
  tool: string;
  displayName: string;
  credentialStatus: CredentialStatus;
  credentialMessage: string | null;
  hasCredential: boolean;
  supported: boolean;
}

export interface ProvidersResponse {
  tools: string[];
  displayNames: Record<string, string>;
  providers: ProviderInfo[];
}

export interface QueryResponse {
  quotas: SubscriptionQuotaDto[];
  queriedAt: number;
}

async function parseJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const body = await response.json();
      if (body && typeof body.detail === 'string') {
        detail = body.detail;
      }
    } catch {
      /* 响应体不是 JSON，沿用状态码 */
    }
    throw new Error(detail);
  }
  return (await response.json()) as T;
}

/** 列出供应商与本地凭据状态（不含 token） */
export async function getProviders(): Promise<ProvidersResponse> {
  const response = await authedFetch(`${BASE_URL}/providers`, {
    method: 'GET',
    headers: getAuthHeaders(),
  });
  return parseJson<ProvidersResponse>(response);
}

/** 查询订阅额度 */
export async function queryQuotas(options?: {
  tools?: string[];
  forceRefresh?: boolean;
}): Promise<QueryResponse> {
  const response = await authedFetch(`${BASE_URL}/query`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({
      tools: options?.tools ?? null,
      force_refresh: options?.forceRefresh ?? false,
    }),
  });
  return parseJson<QueryResponse>(response);
}
