/**
 * 高亮工具函数 - 搜索结果文本高亮
 *
 * 提供高亮搜索结果中匹配文本的功能。
 * 支持大小写不敏感匹配，正确处理正则特殊字符。
 */
import type { ReactNode } from 'react';
import { createElement } from 'react';

/**
 * 转义字符串中的正则表达式特殊字符
 * 用于将用户输入安全地嵌入正则表达式中
 */
export function escapeRegex(str: string): string {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/**
 * 高亮文本中的匹配部分
 *
 * 将文本按照查询字符串分割，匹配部分用 <mark> 包裹。
 * 使用大小写不敏感匹配，与搜索面板的默认行为一致。
 *
 * @param text - 待高亮的原始文本
 * @param query - 查询字符串（会被转义，不作为正则处理）
 * @returns 高亮后的 React 节点（字符串或 React 元素数组）
 */
export function highlightText(text: string, query: string): ReactNode {
  // 无查询时直接返回原文本
  if (!query) {
    return text;
  }

  // 使用捕获组进行分割，匹配项会出现在奇数索引位置
  // 例如: 'foo bar foo'.split(/(foo)/gi) => ['', 'foo', ' bar ', 'foo', '']
  const regex = new RegExp(`(${escapeRegex(query)})`, 'gi');
  const parts = text.split(regex);

  // 没有匹配项时返回原文本
  if (parts.length === 1) {
    return text;
  }

  // 将匹配项用 <mark> 包裹
  return parts.map((part, index) =>
    index % 2 === 1
      ? createElement('mark', { key: index, className: 'search-highlight' }, part)
      : part
  );
}
