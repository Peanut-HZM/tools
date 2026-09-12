import { describe, it, expect } from 'vitest';
import { buildCommandItems, filterCommands, type CommandItem } from './commandPalette';

// 测试工具数据：字段以 src/types/index.ts 的 Tool 实际定义为准（title/description/id）
const tools = [
  { id: 'json-formatter', title: 'JSON 格式化', description: '校验、压缩', route: '/tools/json-formatter' },
  { id: 'ocr', title: 'OCR 文字识别', description: '图片转文字', route: '/tools/ocr' },
] as any[];

const PAGES: CommandItem[] = [
  { id: 'page-marketplace', label: '工具市场', group: '页面', route: '/marketplace' },
  { id: 'page-courses', label: '课程', group: '页面', route: '/courses' },
];

describe('buildCommandItems', () => {
  it('工具与静态页面合并，工具在前', () => {
    const items = [...buildCommandItems(tools), ...PAGES];
    expect(items[0].label).toBe('JSON 格式化');
    expect(items.at(-1)!.group).toBe('页面');
  });
});

describe('filterCommands', () => {
  const items = [...buildCommandItems(tools), ...PAGES];
  it('空 query 返回全部', () => {
    expect(filterCommands(items, '')).toHaveLength(items.length);
  });
  it('大小写不敏感匹配 label 与 route', () => {
    expect(filterCommands(items, 'json')).toHaveLength(1);
    expect(filterCommands(items, 'OCR')).toHaveLength(1);
  });
  it('无匹配返回空数组', () => {
    expect(filterCommands(items, '不存在的工具xyz')).toHaveLength(0);
  });
});
