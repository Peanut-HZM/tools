import { API_BASE_URL } from '../config/api';
import { getAuthHeaders } from './authApi';
import { authedFetch } from './http';

const BASE_URL = `${API_BASE_URL}/gateway`;

export interface MaskingConfig {
  enabled: boolean;
  maskCards: boolean;
  maskIds: boolean;
  extraWords: string[];
}

export interface GatewayConfigDto {
  enabled: boolean;
  port: number;
  host: string;
  masking: MaskingConfig;
  groups: Record<string, string[]>;
  intentRouting: boolean;
  failover: { enabled?: boolean; maxRetries?: number };
}

export interface PluginDto {
  name: string;
  enabled: boolean;
  error: string | null;
}

export interface GatewayConfigResponse {
  config: GatewayConfigDto;
  plugins: PluginDto[];
  endpoints: { openai: string; anthropic: string; models: string };
  hint: string;
}

export interface GatewayModelDto {
  id: string;
  object: string;
  owned_by: string;
  provider_id?: string;
  label?: string;
  members?: string[];
}

export interface WarmupResultDto {
  providerId: string;
  label: string;
  ok: boolean;
  statusCode: number | null;
  message: string | null;
}

async function parseJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const body = await response.json();
      if (body && typeof body.detail === 'string') detail = body.detail;
    } catch {
      /* 非 JSON */
    }
    throw new Error(detail);
  }
  return (await response.json()) as T;
}

export async function getGatewayConfig(): Promise<GatewayConfigResponse> {
  const response = await authedFetch(`${BASE_URL}/config`, {
    method: 'GET',
    headers: getAuthHeaders(),
  });
  return parseJson<GatewayConfigResponse>(response);
}

export async function updateGatewayConfig(
  patch: Partial<GatewayConfigDto>
): Promise<{ config: GatewayConfigDto }> {
  const response = await authedFetch(`${BASE_URL}/config`, {
    method: 'PUT',
    headers: getAuthHeaders(),
    body: JSON.stringify(patch),
  });
  return parseJson(response);
}

export async function getGatewayModels(): Promise<{ data: GatewayModelDto[] }> {
  const response = await authedFetch(`${BASE_URL}/v1/models`, {
    method: 'GET',
    headers: getAuthHeaders(),
  });
  return parseJson(response);
}

export async function runWarmup(
  targets: { providerId: string; model: string; protocol?: string }[]
): Promise<{ results: WarmupResultDto[] }> {
  const response = await authedFetch(`${BASE_URL}/warmup/run`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ targets }),
  });
  return parseJson(response);
}
