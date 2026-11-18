import { describe, expect, it } from 'vitest';
import { formatTokens, sumBuckets, topN, usageDeltaPercent } from './usageRules';

describe('formatTokens', () => {
  it('亿级', () => {
    expect(formatTokens(5781914701)).toBe('57.82亿');
    expect(formatTokens(100_000_000)).toBe('1.00亿');
  });

  it('万级', () => {
    expect(formatTokens(130_920_281 / 10)).toBe('1309.2万');
    expect(formatTokens(10_000)).toBe('1.0万');
  });

  it('普通数字带千分位', () => {
    expect(formatTokens(1234)).toBe('1,234');
    expect(formatTokens(0)).toBe('0');
  });

  it('非法值返回占位', () => {
    expect(formatTokens(Number.NaN)).toBe('—');
    expect(formatTokens(-5)).toBe('—');
  });
});

describe('usageDeltaPercent', () => {
  it('正常计算增减', () => {
    expect(usageDeltaPercent(10, 15)).toBeCloseTo(50);
    expect(usageDeltaPercent(10, 5)).toBeCloseTo(-50);
    expect(usageDeltaPercent(10, 10)).toBeCloseTo(0);
  });

  it('前值为 0 或非法时返回 null', () => {
    expect(usageDeltaPercent(0, 5)).toBeNull();
    expect(usageDeltaPercent(Number.NaN, 5)).toBeNull();
  });
});

describe('topN', () => {
  it('按成本降序取前 N', () => {
    const buckets = [
      { key: 'a', costUsd: 1, requests: 1, totalTokens: 1 },
      { key: 'b', costUsd: 9, requests: 1, totalTokens: 1 },
      { key: 'c', costUsd: 5, requests: 1, totalTokens: 1 },
    ];
    expect(topN(buckets, 2).map((b) => b.key)).toEqual(['b', 'c']);
  });

  it('n <= 0 返回空', () => {
    expect(topN([{ key: 'a', costUsd: 1, requests: 1, totalTokens: 1 }], 0)).toEqual([]);
  });

  it('不修改原数组', () => {
    const buckets = [
      { key: 'a', costUsd: 1, requests: 1, totalTokens: 1 },
      { key: 'b', costUsd: 9, requests: 1, totalTokens: 1 },
    ];
    topN(buckets, 1);
    expect(buckets[0].key).toBe('a');
  });
});

describe('sumBuckets', () => {
  it('累加成本 / 请求 / token', () => {
    const result = sumBuckets([
      { key: 'a', costUsd: 1.5, requests: 10, totalTokens: 100 },
      { key: 'b', costUsd: 2.5, requests: 20, totalTokens: 200 },
    ]);
    expect(result.costUsd).toBeCloseTo(4.0);
    expect(result.requests).toBe(30);
    expect(result.totalTokens).toBe(300);
  });

  it('空数组返回全 0', () => {
    expect(sumBuckets([])).toEqual({ costUsd: 0, requests: 0, totalTokens: 0 });
  });
});
