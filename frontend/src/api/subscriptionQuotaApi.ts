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

export type ProviderKind = 'window' | 'balance' | 'subscription' | 'manual';

export interface QuotaTierDto {
  name: string;
  utilization: number;
  resetsAt: string | null;
  usedValueUsd?: number | null;
  maxValueUsd?: number | null;
  balanceAmount?: number | null;
  balanceUnit?: string | null;
}

export interface ProviderSpecDto {
  id: string;
  name: string;
  kind: ProviderKind;
  needs: string[];
  needsBaseUrl: boolean;
  regions: string[];
  localSource: string | null;
  hint: string;
  extraFields: Record<string, string>;
  configuredCount: number;
  addable: boolean;
}

export interface ProvidersResponse {
  providers: ProviderSpecDto[];
  displayNames: Record<string, string>;
  subscriptionIds: string[];
  manualProviderIds: string[];
}

export interface QuotaAccountDto {
  id: string;
  providerId: string;
  label: string;
  maskedKey: string | null;
  hasKey: boolean;
  extra: Record<string, unknown>;
  enabled: boolean;
  sortOrder: number;
  createdAt: string | null;
  updatedAt: string | null;
  /** 合并 agent-hub 新增字段 */
  category: string;
  app: string;
  notes: string;
  websiteUrl: string;
  manualTotal: number;
  manualUsed: number;
  quotaUnit: string;
  windowType: string;
  windowResetAt: string;
  isManual: boolean;
  lastGood: Record<string, unknown> | null;
}

export interface QuotaResultDto {
  tool: string;
  providerId: string;
  label: string;
  kind: ProviderKind;
  credentialStatus: CredentialStatus;
  credentialMessage: string | null;
  success: boolean;
  tiers: QuotaTierDto[];
  planName: string | null;
  error: string | null;
  queriedAt: number | null;
  accountId: string | null;
  maskedKey: string | null;
  /** 本机自动发现的凭据（不可删除） */
  isLocal?: boolean;
  readOnly?: boolean;
}

export interface ProviderAggregateDto {
  providerId: string;
  label: string;
  kind: ProviderKind;
  /** 该供应商下的账号数 */
  accounts: number;
  /** 还能用的账号数 */
  available: number;
  /** 所有账号里最紧张的剩余百分比（None 表示不适用，如纯余额） */
  tightestRemaining: number | null;
  /** 推荐使用的账号 id（smart 策略） */
  recommendedAccountId: string | null;
  /** 多账号可切换 */
  isFailoverReady: boolean;
}

export interface QueryResponse {
  accounts: QuotaResultDto[];
  subscriptions: QuotaResultDto[];
  aggregates?: ProviderAggregateDto[];
  queriedAt: number;
  configured: boolean;
}

export interface SubscriptionStatusDto {
  providerId: string;
  name: string;
  credentialStatus: CredentialStatus;
  credentialMessage: string | null;
  hasCredential: boolean;
  localSource: string | null;
}

export interface LocalCredentialNoteDto {
  providerId: string;
  name: string;
  /** available | needs_manual_key | absent */
  status: string;
  message: string;
}

export interface AgentSwitchStatusDto {
  agent: string;
  files: { path: string; exists: boolean }[];
  configured: boolean;
  currentProviderId: string;
  currentProviderName: string;
  switchedAt: string;
}

export interface SwitchPreviewDto {
  agent: string;
  files: { path: string; exists: boolean; backed_up: boolean }[];
  floor: Record<string, string>;
}

export interface ImportedProviderDto {
  providerId: string;
  sourceApp: string;
  sourceName: string;
  /** 是否来自 cc-switch 的控制面 Key（OpenDesign 必须用这个） */
  fromControlKey: boolean;
  maskedKey: string;
  /** skip = 已存在（默认不覆盖，保留用户已有数据） */
  action: 'create' | 'update' | 'skip';
}

export interface ImportResponse {
  imported: number;
  created: number;
  updated: number;
  /** 已存在而跳过的数量（默认不覆盖用户已有数据） */
  skipped: number;
  dryRun: boolean;
  items: ImportedProviderDto[];
}

async function parseJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const body = await response.json();
      if (body && typeof body.detail === 'string') detail = body.detail;
    } catch {
      /* 非 JSON 响应，沿用状态码 */
    }
    throw new Error(detail);
  }
  return (await response.json()) as T;
}

/** 供应商目录 */
export async function getProviders(): Promise<ProvidersResponse> {
  const response = await authedFetch(`${BASE_URL}/providers`, {
    method: 'GET',
    headers: getAuthHeaders(),
  });
  return parseJson<ProvidersResponse>(response);
}

/** 本机订阅凭据状态 */
export async function getSubscriptions(): Promise<{
  subscriptions: SubscriptionStatusDto[];
  localCredentials?: LocalCredentialNoteDto[];
}> {
  const response = await authedFetch(`${BASE_URL}/subscriptions`, {
    method: 'GET',
    headers: getAuthHeaders(),
  });
  return parseJson(response);
}

/** 我的账号列表（只有掩码） */
export async function getAccounts(): Promise<{ accounts: QuotaAccountDto[] }> {
  const response = await authedFetch(`${BASE_URL}/accounts`, {
    method: 'GET',
    headers: getAuthHeaders(),
  });
  return parseJson(response);
}

/** 添加账号 */
export async function addAccount(input: {
  providerId: string;
  label?: string;
  apiKey?: string;
  extra?: Record<string, unknown>;
  manualTotal?: number;
  manualUsed?: number;
  quotaUnit?: string;
  windowType?: string;
  windowResetAt?: string;
}): Promise<{ account: QuotaAccountDto }> {
  const response = await authedFetch(`${BASE_URL}/accounts`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({
      provider_id: input.providerId,
      label: input.label ?? '',
      api_key: input.apiKey ?? null,
      extra: input.extra ?? {},
      manual_total: input.manualTotal,
      manual_used: input.manualUsed,
      quota_unit: input.quotaUnit,
      window_type: input.windowType,
      window_reset_at: input.windowResetAt,
    }),
  });
  return parseJson(response);
}

/** 修改账号 */
export async function updateAccount(
  accountId: string,
  input: {
    label?: string;
    apiKey?: string;
    extra?: Record<string, unknown>;
    enabled?: boolean;
    notes?: string;
    websiteUrl?: string;
    manualTotal?: number;
    manualUsed?: number;
    quotaUnit?: string;
    windowType?: string;
    windowResetAt?: string;
  }
): Promise<{ account: QuotaAccountDto }> {
  const response = await authedFetch(`${BASE_URL}/accounts/${accountId}`, {
    method: 'PUT',
    headers: getAuthHeaders(),
    body: JSON.stringify({
      label: input.label,
      api_key: input.apiKey,
      extra: input.extra,
      enabled: input.enabled,
      notes: input.notes,
      website_url: input.websiteUrl,
      manual_total: input.manualTotal,
      manual_used: input.manualUsed,
      quota_unit: input.quotaUnit,
      window_type: input.windowType,
      window_reset_at: input.windowResetAt,
    }),
  });
  return parseJson(response);
}

/** 删除账号 */
export async function deleteAccount(accountId: string): Promise<{ success: boolean }> {
  const response = await authedFetch(`${BASE_URL}/accounts/${accountId}`, {
    method: 'DELETE',
    headers: getAuthHeaders(),
  });
  return parseJson(response);
}

/** 从本机 cc-switch 导入供应商（含 OpenDesign 控制面 Key） */
export async function importFromCcSwitch(dryRun = false): Promise<ImportResponse> {
  const response = await authedFetch(`${BASE_URL}/import/cc-switch`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ dry_run: dryRun }),
  });
  return parseJson<ImportResponse>(response);
}

export interface MagpieSyncItemDto {
  source: string;
  providerId: string;
  sourceName: string;
  preset: string;
  maskedKey: string;
  action: string;
}

export interface MagpieSkippedItemDto {
  source: string;
  name: string;
  preset: string;
  reason: string;
}

export interface MagpieSyncResponse {
  imported: number;
  created: number;
  updated: number;
  skipped: number;
  dryRun: boolean;
  items: MagpieSyncItemDto[];
  skippedItems: MagpieSkippedItemDto[];
  message?: string;
}

export interface MagpieStatusDto {
  available: boolean;
  providersPath: string;
  providersFileExists: boolean;
  binary: string;
}

/** magpie 是否可用于同步 */
export async function getMagpieStatus(): Promise<MagpieStatusDto> {
  const response = await authedFetch(`${BASE_URL}/magpie/status`, {
    method: 'GET',
    headers: getAuthHeaders(),
  });
  return parseJson<MagpieStatusDto>(response);
}

/** 从本机 magpie 同步已配置的供应商与订阅账号 */
export async function importFromMagpie(
  dryRun = false,
  includeAccounts = true
): Promise<MagpieSyncResponse> {
  const response = await authedFetch(`${BASE_URL}/import/magpie`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ dry_run: dryRun, include_accounts: includeAccounts }),
  });
  return parseJson<MagpieSyncResponse>(response);
}

/** 手动额度调整（合并 agent-hub：额度支持手动增加） */
export async function adjustQuota(
  accountId: string,
  input: { total?: number; used?: number; add?: number; unit?: string; windowType?: string; windowResetAt?: string }
): Promise<{ account: QuotaAccountDto }> {
  const response = await authedFetch(`${BASE_URL}/accounts/${accountId}/quota`, {
    method: 'PUT',
    headers: getAuthHeaders(),
    body: JSON.stringify({
      total: input.total,
      used: input.used,
      add: input.add,
      unit: input.unit,
      window_type: input.windowType,
      window_reset_at: input.windowResetAt,
    }),
  });
  return parseJson(response);
}

/** 本机各 agent 的配置状态（只读） */
export async function listAgents(): Promise<{ agents: AgentSwitchStatusDto[]; supported: string[] }> {
  const response = await authedFetch(`${BASE_URL}/agents`, {
    method: 'GET',
    headers: getAuthHeaders(),
  });
  return parseJson(response);
}

/** 切换预览（dry-run，不写文件） */
export async function previewAgentSwitch(
  agent: string,
  accountId: string,
  model = ''
): Promise<SwitchPreviewDto> {
  const params = new URLSearchParams({ account_id: accountId, model });
  const response = await authedFetch(
    `${BASE_URL}/agents/${agent}/config-preview?${params.toString()}`,
    { method: 'GET', headers: getAuthHeaders() }
  );
  return parseJson<SwitchPreviewDto>(response);
}

/** 执行切换（写本机配置，带首写备份） */
export async function switchAgent(
  agent: string,
  accountId: string,
  model = ''
): Promise<{ ok: boolean; agent: string; providerName: string; written: string[] }> {
  const params = new URLSearchParams({ account_id: accountId });
  const response = await authedFetch(`${BASE_URL}/agents/${agent}/switch?${params.toString()}`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ model }),
  });
  return parseJson(response);
}

/** 恢复备份 */
export async function restoreAgent(agent: string): Promise<{ ok: boolean; restored: string[] }> {
  const response = await authedFetch(`${BASE_URL}/agents/${agent}/restore`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  return parseJson(response);
}

/** 测试单个账号（可传临时凭据） */
export async function testAccount(
  accountId: string,
  input?: { apiKey?: string; extra?: Record<string, unknown> }
): Promise<{ quota: QuotaResultDto }> {
  const response = await authedFetch(`${BASE_URL}/accounts/${accountId}/test`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({
      api_key: input?.apiKey ?? null,
      extra: input?.extra ?? {},
    }),
  });
  return parseJson(response);
}

/** 查询额度（只返回已配置项） */
export async function queryQuotas(options?: {
  accountIds?: string[];
  includeSubscriptions?: boolean;
  forceRefresh?: boolean;
}): Promise<QueryResponse> {
  const response = await authedFetch(`${BASE_URL}/query`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({
      account_ids: options?.accountIds ?? null,
      include_subscriptions: options?.includeSubscriptions ?? true,
      force_refresh: options?.forceRefresh ?? false,
    }),
  });
  return parseJson<QueryResponse>(response);
}
