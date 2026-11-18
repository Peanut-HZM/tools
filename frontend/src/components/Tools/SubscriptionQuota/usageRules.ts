/**
 * 用量面板的纯函数（对照 magpie 的 usage / cost 展示口径）
 */

export interface UsageBucketLike {
  key: string;
  costUsd: number;
  requests: number;
  totalTokens: number;
}

/** 大数字可读化：1.2亿 / 345.6万 / 12,345 */
export function formatTokens(value: number): string {
  if (!Number.isFinite(value) || value < 0) return '—';
  if (value >= 1e8) return `${(value / 1e8).toFixed(2)}亿`;
  if (value >= 1e4) return `${(value / 1e4).toFixed(1)}万`;
  return value.toLocaleString('zh-CN');
}

/** 成本变化百分比；前值为 0 时无法计算，返回 null */
export function usageDeltaPercent(previous: number, current: number): number | null {
  if (!Number.isFinite(previous) || !Number.isFinite(current)) return null;
  if (previous <= 0) return null;
  return ((current - previous) / previous) * 100;
}

/** 取成本最高的前 N 项（已排序的输入保持稳定） */
export function topN<T extends UsageBucketLike>(buckets: T[], n: number): T[] {
  if (n <= 0) return [];
  return [...buckets].sort((a, b) => b.costUsd - a.costUsd).slice(0, n);
}

/** 汇总若干桶的总和 */
export function sumBuckets<T extends UsageBucketLike>(
  buckets: T[]
): { costUsd: number; requests: number; totalTokens: number } {
  return buckets.reduce(
    (acc, bucket) => ({
      costUsd: acc.costUsd + bucket.costUsd,
      requests: acc.requests + bucket.requests,
      totalTokens: acc.totalTokens + bucket.totalTokens,
    }),
    { costUsd: 0, requests: 0, totalTokens: 0 }
  );
}
