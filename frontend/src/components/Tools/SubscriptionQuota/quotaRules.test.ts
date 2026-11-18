import { describe, expect, it } from 'vitest';
import {
  countdownStr,
  credentialStatusText,
  pickTiers,
  relativeTime,
  remainingPercent,
  sortTiers,
  tierLabel,
  tierOrder,
  toneForRemaining,
  toolLabel,
  type QuotaTier,
} from './quotaRules';

describe('remainingPercent', () => {
  it('把已用百分比换算成剩余百分比', () => {
    expect(remainingPercent(0)).toBe(100);
    expect(remainingPercent(26)).toBe(74);
    expect(remainingPercent(100)).toBe(0);
  });

  it('把越界值夹在 0–100', () => {
    expect(remainingPercent(-10)).toBe(100);
    expect(remainingPercent(130)).toBe(0);
    expect(remainingPercent(Number.NaN)).toBe(0);
  });
});

describe('toneForRemaining', () => {
  it('剩余充足为 normal', () => {
    expect(toneForRemaining(100)).toBe('normal');
    expect(toneForRemaining(20)).toBe('normal');
  });

  it('剩余低于 20% 为 warning', () => {
    expect(toneForRemaining(19.9)).toBe('warning');
    expect(toneForRemaining(1)).toBe('warning');
  });

  it('用完为 danger', () => {
    expect(toneForRemaining(0)).toBe('danger');
    expect(toneForRemaining(-5)).toBe('danger');
  });
});

describe('tierLabel / tierOrder', () => {
  it('已知窗口有中文名', () => {
    expect(tierLabel('five_hour')).toBe('5 小时');
    expect(tierLabel('weekly_limit')).toBe('每周');
    expect(tierLabel('seven_day_opus')).toBe('每周 Opus');
  });

  it('未知窗口可读降级', () => {
    expect(tierLabel('12_hour')).toBe('12 小时');
    expect(tierLabel('3_day')).toBe('3 天');
    expect(tierLabel('mystery')).toBe('mystery');
    expect(tierLabel('')).toBe('额度');
  });

  it('窗口排序：短窗口在前', () => {
    expect(tierOrder('five_hour')).toBeLessThan(tierOrder('weekly_limit'));
    expect(tierOrder('weekly_limit')).toBeLessThan(tierOrder('monthly'));
    expect(tierOrder('unknown_window')).toBe(99);
  });
});

describe('sortTiers', () => {
  it('按窗口从短到长排序，未知排最后', () => {
    const tiers: QuotaTier[] = [
      { name: 'monthly', utilization: 10, resetsAt: null },
      { name: 'five_hour', utilization: 50, resetsAt: null },
      { name: 'unknown_x', utilization: 30, resetsAt: null },
      { name: 'weekly_limit', utilization: 20, resetsAt: null },
    ];
    expect(sortTiers(tiers).map((t) => t.name)).toEqual([
      'five_hour',
      'weekly_limit',
      'monthly',
      'unknown_x',
    ]);
  });
});

describe('countdownStr', () => {
  const base = Date.parse('2026-11-18T12:00:00Z');

  it('没有重置时间返回 null', () => {
    expect(countdownStr(null, base)).toBeNull();
    expect(countdownStr(undefined, base)).toBeNull();
  });

  it('已过期返回 null', () => {
    expect(countdownStr('2026-11-18T11:00:00Z', base)).toBeNull();
  });

  it('小时级倒计时', () => {
    expect(countdownStr('2026-11-18T14:30:00Z', base)).toBe('2h30m');
  });

  it('天级倒计时', () => {
    expect(countdownStr('2026-11-21T15:00:00Z', base)).toBe('3d3h');
  });

  it('分钟级倒计时', () => {
    expect(countdownStr('2026-11-18T12:45:00Z', base)).toBe('45m');
  });

  it('非法时间返回 null', () => {
    expect(countdownStr('not-a-date', base)).toBeNull();
  });
});

describe('relativeTime', () => {
  const now = Date.parse('2026-11-18T12:00:00Z');

  it('刚刚', () => {
    expect(relativeTime(now - 10_000, now)).toBe('刚刚');
  });

  it('分钟 / 小时 / 天', () => {
    expect(relativeTime(now - 5 * 60_000, now)).toBe('5 分钟前');
    expect(relativeTime(now - 3 * 3600_000, now)).toBe('3 小时前');
    expect(relativeTime(now - 2 * 86400_000, now)).toBe('2 天前');
  });

  it('空值返回空字符串', () => {
    expect(relativeTime(null, now)).toBe('');
    expect(relativeTime(0, now)).toBe('');
  });
});

describe('pickTiers', () => {
  const tiers: QuotaTier[] = [
    { name: 'a', utilization: 10, resetsAt: null }, // 剩余 90
    { name: 'b', utilization: 95, resetsAt: null }, // 剩余 5
    { name: 'c', utilization: 60, resetsAt: null }, // 剩余 40
  ];

  it('不超过上限时原样返回', () => {
    expect(pickTiers(tiers, 5)).toEqual(tiers);
  });

  it('超出上限时保留剩余最少的，再按原顺序排回', () => {
    const picked = pickTiers(tiers, 2);
    expect(picked.map((t) => t.name)).toEqual(['b', 'c']);
  });
});

describe('标签兜底', () => {
  it('已知工具名', () => {
    expect(toolLabel('kimi')).toBe('Kimi Code');
    expect(toolLabel('zhipu')).toBe('智谱 GLM');
  });

  it('未知工具名原样返回', () => {
    expect(toolLabel('whatever')).toBe('whatever');
  });

  it('凭据状态文案', () => {
    expect(credentialStatusText('valid')).toBe('已登录');
    expect(credentialStatusText('expired')).toBe('登录已过期');
    expect(credentialStatusText('not_found')).toBe('未检测到登录');
    expect(credentialStatusText('parse_error')).toBe('凭据解析失败');
  });
});
