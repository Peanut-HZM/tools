/**
 * 订阅额度的纯函数（对照 cc-switch 的 `src/components/quota/quotaRules.ts`）
 *
 * 约定：后端返回的 `utilization` 是**已用**百分比，前端按剩余展示。
 * 这里全部是纯函数，便于单测覆盖。
 */

export type CredentialStatus =
  | 'valid'
  | 'expired'
  | 'refresh_pending'
  | 'not_found'
  | 'parse_error';

export interface QuotaTier {
  name: string;
  /** 已用百分比 0–100 */
  utilization: number;
  resetsAt: string | null;
  usedValueUsd?: number | null;
  maxValueUsd?: number | null;
}

export interface SubscriptionQuota {
  tool: string;
  credentialStatus: CredentialStatus;
  credentialMessage: string | null;
  success: boolean;
  tiers: QuotaTier[];
  planName: string | null;
  error: string | null;
  queriedAt: number | null;
}

/** 额度紧张阈值：剩余低于该值显示橙色 */
export const WARN_BELOW_PERCENT = 20;

export type QuotaTone = 'normal' | 'warning' | 'danger';

/** 把「已用」百分比换成「剩余」百分比（夹在 0–100） */
export function remainingPercent(utilization: number): number {
  if (!Number.isFinite(utilization)) return 0;
  return Math.max(0, Math.min(100, 100 - utilization));
}

/** 按剩余百分比给色调：<=0 红、<20 橙、否则绿 */
export function toneForRemaining(remaining: number): QuotaTone {
  if (remaining <= 0) return 'danger';
  if (remaining < WARN_BELOW_PERCENT) return 'warning';
  return 'normal';
}

/** 档位窗口的中文名 */
export const TIER_LABELS: Record<string, string> = {
  five_hour: '5 小时',
  seven_day: '每周',
  seven_day_fable: '每周 Fable',
  seven_day_opus: '每周 Opus',
  seven_day_sonnet: '每周 Sonnet',
  weekly_limit: '每周',
  '30_day': '30 天',
  monthly: '每月',
  gemini_pro: 'Gemini Pro',
  gemini_flash: 'Gemini Flash',
  gemini_flash_lite: 'Gemini Flash Lite',
  credits: 'Credits',
};

export function tierLabel(name: string): string {
  const known = TIER_LABELS[name];
  if (known) return known;
  // 形如 12_hour / 3_day 的未知窗口，尽量可读
  const match = /^(\d+)_(hour|day)$/.exec(name);
  if (match) {
    const value = match[1];
    return match[2] === 'hour' ? `${value} 小时` : `${value} 天`;
  }
  return name || '额度';
}

/** 档位窗口的排序权重（越小越靠前） */
const TIER_ORDER: Record<string, number> = {
  five_hour: 0,
  seven_day: 1,
  seven_day_fable: 1,
  seven_day_opus: 1,
  seven_day_sonnet: 1,
  weekly_limit: 1,
  '30_day': 2,
  monthly: 2,
  gemini_pro: 0,
  gemini_flash: 1,
  gemini_flash_lite: 2,
  credits: 3,
};

export function tierOrder(name: string): number {
  const known = TIER_ORDER[name];
  if (known !== undefined) return known;
  return 99;
}

/** 按窗口排序（稳定排序，未知窗口保持原顺序排在最后） */
export function sortTiers(tiers: QuotaTier[]): QuotaTier[] {
  return tiers
    .map((tier, index) => ({ tier, index }))
    .sort((a, b) => tierOrder(a.tier.name) - tierOrder(b.tier.name) || a.index - b.index)
    .map(({ tier }) => tier);
}

/**
 * 倒计时的纯时间字符串（如 "2h30m"、"3d12h"）
 * 没有重置时间或已过期时返回 null。
 */
export function countdownStr(resetsAt: string | null | undefined, now = Date.now()): string | null {
  if (!resetsAt) return null;
  const target = Date.parse(resetsAt);
  if (!Number.isFinite(target)) return null;
  const diffMs = target - now;
  if (diffMs <= 0) return null;
  const totalMinutes = Math.floor(diffMs / 60000);
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  if (hours >= 24) {
    const days = Math.floor(hours / 24);
    return `${days}d${hours % 24}h`;
  }
  if (hours > 0) return `${hours}h${minutes}m`;
  return `${minutes}m`;
}

/** 相对时间（「3 分钟前」） */
export function relativeTime(timestamp: number | null | undefined, now = Date.now()): string {
  if (!timestamp || !Number.isFinite(timestamp)) return '';
  const diffSeconds = Math.max(0, Math.floor((now - timestamp) / 1000));
  if (diffSeconds < 60) return '刚刚';
  if (diffSeconds < 3600) return `${Math.floor(diffSeconds / 60)} 分钟前`;
  if (diffSeconds < 86400) return `${Math.floor(diffSeconds / 3600)} 小时前`;
  return `${Math.floor(diffSeconds / 86400)} 天前`;
}

/**
 * 一家供应商是否还有可展示的额度：
 * 有档位、或成功但档位为空（如未开始使用的套餐）
 */
export function hasDisplayableQuota(quota: SubscriptionQuota): boolean {
  return quota.success;
}

/** 供应商名称（后端也会返回，这里兜底） */
export const TOOL_LABELS: Record<string, string> = {
  claude: 'Claude Code',
  codex: 'Codex (ChatGPT)',
  gemini: 'Gemini CLI',
  kimi: 'Kimi Code',
  minimax: 'MiniMax',
  zhipu: '智谱 GLM',
};

export function toolLabel(tool: string): string {
  return TOOL_LABELS[tool] ?? tool;
}

/** 凭据状态的中文说明 */
export function credentialStatusText(status: CredentialStatus): string {
  switch (status) {
    case 'valid':
      return '已登录';
    case 'expired':
      return '登录已过期';
    case 'refresh_pending':
      return '令牌待刷新';
    case 'parse_error':
      return '凭据解析失败';
    case 'not_found':
    default:
      return '未检测到登录';
  }
}

/**
 * 卡片上最多显示几行：剩余最少的优先，再按原顺序排回去。
 * 与 cc-switch 的 `pickLines` 语义一致。
 */
export function pickTiers(tiers: QuotaTier[], max = 2): QuotaTier[] {
  if (tiers.length <= max) return tiers;
  return tiers
    .map((tier, index) => ({ tier, index, remaining: remainingPercent(tier.utilization) }))
    .sort((a, b) => a.remaining - b.remaining)
    .slice(0, max)
    .sort((a, b) => a.index - b.index)
    .map(({ tier }) => tier);
}
