/**
 * URL 与 Query Params 双向同步工具
 *
 * 设计：
 * - params 表格为启用参数的最终事实来源，启用参数始终同步进 URL query
 * - URL 编辑时：解析 query 重建参数表；已禁用的表格参数（不出现在 URL 中）保留
 * - URL 中的 path 部分始终去除 query 后存储
 */

import { KeyValueItem } from '../../../../services/httpClientApi';

/** 从 URL 中拆分出 path 与 query 参数（破坏性解析，仅用于编辑联动） */
export function splitUrlQuery(url: string): { path: string; query: KeyValueItem[] } {
  const items: KeyValueItem[] = [];
  if (!url) return { path: '', query: items };
  const qIndex = url.indexOf('?');
  if (qIndex === -1) return { path: url, query: items };
  const path = url.slice(0, qIndex);
  const qs = url.slice(qIndex + 1);
  for (const pair of qs.split('&')) {
    if (!pair) continue;
    const eq = pair.indexOf('=');
    if (eq > 0) {
      items.push({ key: pair.slice(0, eq), value: pair.slice(eq + 1), enabled: true, description: '' });
    } else {
      items.push({ key: pair, value: '', enabled: true, description: '' });
    }
  }
  return { path, query: items };
}

/** 将启用的参数拼回 URL */
export function buildUrlWithQuery(path: string, params: KeyValueItem[]): string {
  const enabled = (params || []).filter(p => p.enabled && p.key.trim());
  if (enabled.length === 0) return path;
  const qs = enabled.map(p => `${p.key}=${p.value}`).join('&');
  return path.includes('?') ? `${path}&${qs}` : `${path}?${qs}`;
}

/**
 * URL 变更后重建参数表：
 * - 以 URL query 为准生成新列表
 * - 保留原表中已禁用（enabled=false）且未出现在 URL 中的参数
 */
export function rebuildParamsFromUrl(currentParams: KeyValueItem[], newUrl: string): KeyValueItem[] {
  const { query } = splitUrlQuery(newUrl);
  const keysInUrl = new Set(query.map(q => q.key));
  const disabledKept = (currentParams || []).filter(
    p => !p.enabled && p.key.trim() && !keysInUrl.has(p.key)
  );
  return [...query, ...disabledKept];
}
