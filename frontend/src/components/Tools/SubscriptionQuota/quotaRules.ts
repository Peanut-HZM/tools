/**
 * 订阅额度的纯函数（对照 cc-switch 的 quotaRules.ts + 余额展示）
 *
 * 后端返回的 `utilization` 是**已用**百分比；余额型条目改用
 * `balanceAmount` / `balanceUnit`，`utilization` 恒为 0。
 */

export type QuotaTone = 'normal' | 'warning' | 'danger';

/** 额度紧张阈值：剩余低于该值显示橙色 */
export const WARN_BELOW_PERCENT = 20;

export interface TierLike {
  name: string;
  utilization: number;
  resetsAt: string | null;
  balanceAmount?: number | null;
  balanceUnit?: string | null;
  usedValueUsd?: number | null;
  maxValueUsd?: number | null;
}

/** 是否是余额型条目 */
export function isBalanceTier(tier: TierLike): boolean {
  return typeof tier.balanceAmount === 'number' && Number.isFinite(tier.balanceAmount);
}

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

/** 余额色调：<=0 红，其余中性（不做「快用完」的加深） */
export function toneForBalance(amount: number): QuotaTone {
  return amount <= 0 ? 'danger' : 'normal';
}

/** 档位窗口中文名 */
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
  balance: '余额',
};

export function tierLabel(name: string): string {
  const known = TIER_LABELS[name];
  if (known) return known;
  if (name.startsWith('balance_')) {
    return `余额 ${name.slice('balance_'.length)}`;
  }
  const match = /^(\d+)_(hour|day)$/.exec(name);
  if (match) {
    const value = match[1];
    return match[2] === 'hour' ? `${value} 小时` : `${value} 天`;
  }
  return name || '额度';
}

const TIER_ORDER: Record<string, number> = {
  five_hour: 0,
  seven_day: 1,
  seven_day_fable: 1,
  seven_day_opus: 1,
  seven_day_sonnet: 1,
  weekly_limit: 1,
  monthly: 2,
  '30_day': 2,
  gemini_pro: 0,
  gemini_flash: 1,
  gemini_flash_lite: 2,
  credits: 3,
};

export function tierOrder(name: string): number {
  if (name.startsWith('balance_')) return 10;
  const known = TIER_ORDER[name];
  return known !== undefined ? known : 99;
}

/** 排序：窗口从短到长，余额排最后 */
export function sortTiers<T extends TierLike>(tiers: T[]): T[] {
  return tiers
    .map((tier, index) => ({ tier, index }))
    .sort(
      (a, b) => tierOrder(a.tier.name) - tierOrder(b.tier.name) || a.index - b.index
    )
    .map(({ tier }) => tier);
}

/** 倒计时字符串（"2h30m" / "3d12h"）；没有或已过期为 null */
export function countdownStr(
  resetsAt: string | null | undefined,
  now = Date.now()
): string | null {
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
export function relativeTime(
  timestamp: number | null | undefined,
  now = Date.now()
): string {
  if (!timestamp || !Number.isFinite(timestamp)) return '';
  const diffSeconds = Math.max(0, Math.floor((now - timestamp) / 1000));
  if (diffSeconds < 60) return '刚刚';
  if (diffSeconds < 3600) return `${Math.floor(diffSeconds / 60)} 分钟前`;
  if (diffSeconds < 86400) return `${Math.floor(diffSeconds / 3600)} 小时前`;
  return `${Math.floor(diffSeconds / 86400)} 天前`;
}

/** 金额格式化：小于 1 保留 2 位，其余保留 2 位但带千分位 */
export function formatAmount(amount: number, unit?: string | null): string {
  if (!Number.isFinite(amount)) return '—';
  const abs = Math.abs(amount);
  const digits = abs >= 1000 ? 0 : 2;
  const text = amount.toLocaleString('zh-CN', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
  return unit ? `${text} ${unit}` : text;
}

/** 供应商类别标签 */
export function kindLabel(kind: string): string {
  switch (kind) {
    case 'balance':
      return '余额';
    case 'subscription':
      return '订阅';
    case 'window':
    default:
      return '套餐';
  }
}

/** 凭据状态文案 */
export function credentialStatusText(status: string): string {
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
 * 卡片上最多显示几行：余额优先（金额是主要信息），其余按剩余最少的优先。
 */
export function pickTiers<T extends TierLike>(tiers: T[], max = 4): T[] {
  if (tiers.length <= max) return tiers;
  return tiers
    .map((tier, index) => ({
      tier,
      index,
      score: isBalanceTier(tier)
        ? -1000
        : remainingPercent(tier.utilization),
    }))
    .sort((a, b) => a.score - b.score)
    .slice(0, max)
    .sort((a, b) => a.index - b.index)
    .map(({ tier }) => tier);
}

/** 某个供应商需要哪些字段的提示文案 */
export function needsHint(needs: string[], extraFields: Record<string, string>): string {
  const names: Record<string, string> = {
    api_key: 'API Key',
    control_key: 'Control Key',
    access_key: 'AccessKey ID',
    secret_key: 'Secret AccessKey',
    organization_id: '组织 ID',
    project_id: '项目 ID',
  };
  const parts = needs.map((n) => names[n] ?? extraFields[n] ?? n);
  return parts.length > 0 ? `需要 ${parts.join(' + ')}` : '无需额外凭据';
}

/** 供应商首字母（无图标时占位） */
export function providerInitials(name: string): string {
  const trimmed = name.trim();
  if (!trimmed) return '?';
  const ascii = trimmed.replace(/[^A-Za-z0-9 ]/g, '').trim();
  if (ascii) {
    const words = ascii.split(/\s+/).filter(Boolean);
    if (words.length >= 2) {
      return (words[0][0] + words[1][0]).toUpperCase();
    }
    return ascii.slice(0, 2).toUpperCase();
  }
  return trimmed.slice(0, 2);
}
