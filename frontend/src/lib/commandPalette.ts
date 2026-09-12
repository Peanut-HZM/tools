import type { Tool } from '../types';

/** 命令面板条目：工具 + 静态页面 */
export interface CommandItem {
  id: string;
  label: string;
  hint?: string;
  group: '工具' | '页面';
  route: string;
  /** 仅工具条目有：跳转工作区时通过 route state 传递，与 App.tsx handleToolClick 约定一致 */
  toolId?: string;
}

/** 面板固定收录的静态页面入口 */
export const PAGE_ITEMS: CommandItem[] = [
  { id: 'page-home', label: '首页', group: '页面', route: '/' },
  { id: 'page-marketplace', label: '工具市场', group: '页面', route: '/marketplace' },
  { id: 'page-courses', label: '课程', group: '页面', route: '/courses' },
  { id: 'page-tech-contents', label: '技术内容', group: '页面', route: '/tech-contents' },
  { id: 'page-account', label: '账户设置', group: '页面', route: '/account-settings' },
];

/** 后端工具列表 → 面板条目（description 作为 hint；toolId 供工作区 state 跳转） */
export function buildCommandItems(tools: Tool[]): CommandItem[] {
  return tools.map((tool) => ({
    id: `tool-${tool.id}`,
    label: tool.title,
    hint: tool.description,
    group: '工具' as const,
    route: '/workspace',
    toolId: tool.id,
  }));
}

/** 过滤：大小写不敏感，匹配 label/hint/route；空串返回全部 */
export function filterCommands(items: CommandItem[], query: string): CommandItem[] {
  const q = query.trim().toLowerCase();
  if (!q) return items;
  return items.filter(
    (item) =>
      item.label.toLowerCase().includes(q) ||
      (item.hint ?? '').toLowerCase().includes(q) ||
      item.route.toLowerCase().includes(q)
  );
}
