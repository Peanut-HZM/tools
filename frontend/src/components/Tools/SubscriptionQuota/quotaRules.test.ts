import { describe, expect, it } from 'vitest';
import {
  countdownStr,
  credentialStatusText,
  formatAmount,
  isBalanceTier,
  kindLabel,
  needsHint,
  pickTiers,
  providerInitials,
  relativeTime,
  remainingPercent,
  sortTiers,
  tierLabel,
  tierOrder,
  toneForBalance,
  toneForRemaining,
} from './quotaRules';

interface Tier {
  name: string;
  utilization: number;
  resetsAt: string | null;
  balanceAmount?: number | null;
  balanceUnit?: string | null;
}

describe('remainingPercent', () => {
  it('已用 → 剩余', () => {
    expect(remainingPercent(0)).toBe(100);
    expect(remainingPercent(26)).toBe(74);
    expect(remainingPercent(100)).toBe(0);
  });

  it('越界夹在 0–100', () => {
    expect(remainingPercent(-10)).toBe(100);
    expect(remainingPercent(130)).toBe(0);
    expect(remainingPercent(Number.NaN)).toBe(0);
  });
});

describe('toneForRemaining / toneForBalance', () => {
  it('剩余充足 normal', () => {
    expect(toneForRemaining(100)).toBe('normal');
    expect(toneForRemaining(20)).toBe('normal');
  });

  it('剩余 <20% warning，用完 danger', () => {
    expect(toneForRemaining(19.9)).toBe('warning');
    expect(toneForRemaining(0)).toBe('danger');
  });

  it('余额 <=0 才 danger', () => {
    expect(toneForBalance(12.5)).toBe('normal');
    expect(toneForBalance(0)).toBe('danger');
    expect(toneForBalance(-3)).toBe('danger');
  });
});

describe('tierLabel / tierOrder', () => {
  it('已知窗口中文名', () => {
    expect(tierLabel('five_hour')).toBe('5 小时');
    expect(tierLabel('weekly_limit')).toBe('每周');
    expect(tierLabel('monthly')).toBe('每月');
    expect(tierLabel('seven_day_opus')).toBe('每周 Opus');
  });

  it('余额窗口带币种', () => {
    expect(tierLabel('balance_CNY')).toBe('余额 CNY');
    expect(tierLabel('balance_USD')).toBe('余额 USD');
  });

  it('未知窗口可读降级', () => {
    expect(tierLabel('12_hour')).toBe('12 小时');
    expect(tierLabel('3_day')).toBe('3 天');
  });

  it('排序：短窗口在前，余额最后', () => {
    expect(tierOrder('five_hour')).toBeLessThan(tierOrder('weekly_limit'));
    expect(tierOrder('weekly_limit')).toBeLessThan(tierOrder('monthly'));
    expect(tierOrder('monthly')).toBeLessThan(tierOrder('balance_USD'));
  });
});

describe('sortTiers', () => {
  it('按窗口排序，余额排最后', () => {
    const tiers: Tier[] = [
      { name: 'balance_USD', utilization: 0, resetsAt: null, balanceAmount: 5, balanceUnit: 'USD' },
      { name: 'monthly', utilization: 10, resetsAt: null },
      { name: 'five_hour', utilization: 50, resetsAt: null },
      { name: 'weekly_limit', utilization: 20, resetsAt: null },
    ];
    expect(sortTiers(tiers).map((t) => t.name)).toEqual([
      'five_hour',
      'weekly_limit',
      'monthly',
      'balance_USD',
    ]);
  });
});

describe('isBalanceTier', () => {
  it('有 balanceAmount 才是余额型', () => {
    expect(isBalanceTier({ name: 'balance_USD', utilization: 0, resetsAt: null, balanceAmount: 1 })).toBe(true);
    expect(isBalanceTier({ name: 'five_hour', utilization: 10, resetsAt: null })).toBe(false);
  });
});

describe('countdownStr', () => {
  const base = Date.parse('2026-11-18T12:00:00Z');

  it('无 / 过期 / 非法 → null', () => {
    expect(countdownStr(null, base)).toBeNull();
    expect(countdownStr('2026-11-18T11:00:00Z', base)).toBeNull();
    expect(countdownStr('bad', base)).toBeNull();
  });

  it('小时 / 天 / 分钟', () => {
    expect(countdownStr('2026-11-18T14:30:00Z', base)).toBe('2h30m');
    expect(countdownStr('2026-11-21T15:00:00Z', base)).toBe('3d3h');
    expect(countdownStr('2026-11-18T12:45:00Z', base)).toBe('45m');
  });
});

describe('relativeTime', () => {
  const now = Date.parse('2026-11-18T12:00:00Z');

  it('刚刚 / 分 / 时 / 天', () => {
    expect(relativeTime(now - 10_000, now)).toBe('刚刚');
    expect(relativeTime(now - 5 * 60_000, now)).toBe('5 分钟前');
    expect(relativeTime(now - 3 * 3600_000, now)).toBe('3 小时前');
    expect(relativeTime(now - 2 * 86400_000, now)).toBe('2 天前');
  });

  it('空值返回空串', () => {
    expect(relativeTime(null, now)).toBe('');
    expect(relativeTime(0, now)).toBe('');
  });
});

describe('formatAmount', () => {
  it('小额保留两位', () => {
    expect(formatAmount(12.345, 'CNY')).toBe('12.35 CNY');
  });

  it('大额不带小数并千分位', () => {
    expect(formatAmount(12345.6, 'USD')).toBe('12,346 USD');
  });

  it('无单位时不追加', () => {
    expect(formatAmount(5.5)).toBe('5.50');
  });

  it('非法值返回占位', () => {
    expect(formatAmount(Number.NaN)).toBe('—');
  });
});

describe('pickTiers', () => {
  it('不超上限原样返回', () => {
    const tiers: Tier[] = [{ name: 'a', utilization: 1, resetsAt: null }];
    expect(pickTiers(tiers, 4)).toEqual(tiers);
  });

  it('超上限时余额优先，其余按剩余少的优先', () => {
    const tiers: Tier[] = [
      { name: 'five_hour', utilization: 10, resetsAt: null }, // 剩 90
      { name: 'weekly_limit', utilization: 95, resetsAt: null }, // 剩 5
      { name: 'balance_USD', utilization: 0, resetsAt: null, balanceAmount: 3, balanceUnit: 'USD' },
      { name: 'monthly', utilization: 60, resetsAt: null }, // 剩 40
    ];
    const picked = pickTiers(tiers, 2);
    expect(picked.map((t) => t.name).sort()).toEqual(['balance_USD', 'weekly_limit']);
  });
});

describe('文案助手', () => {
  it('kindLabel', () => {
    expect(kindLabel('window')).toBe('套餐');
    expect(kindLabel('balance')).toBe('余额');
    expect(kindLabel('subscription')).toBe('订阅');
  });

  it('credentialStatusText', () => {
    expect(credentialStatusText('valid')).toBe('已登录');
    expect(credentialStatusText('expired')).toBe('登录已过期');
    expect(credentialStatusText('not_found')).toBe('未检测到登录');
  });

  it('needsHint 列出所需字段', () => {
    expect(needsHint(['api_key'], {})).toBe('需要 API Key');
    expect(needsHint(['access_key', 'secret_key'], {})).toBe(
      '需要 AccessKey ID + Secret AccessKey'
    );
    expect(needsHint([], {})).toBe('无需额外凭据');
  });

  it('providerInitials 取首字母', () => {
    expect(providerInitials('Kimi Code')).toBe('KC');
    expect(providerInitials('智谱 GLM')).toBe('GL');
    expect(providerInitials('')).toBe('?');
  });
});
