/**
 * MemoryRenderer 单元测试
 *
 * 覆盖：
 * - memory_read：
 *   - 工具名 badge "memory_read" 渲染
 *   - pending 状态显示「正在读取记忆...」
 *   - 单条记录：key + value JSON + summary + updated_at
 *   - 单条未找到（value=null）：「未找到该记忆条目」
 *   - 列表：「共 N 条记忆」+ 前 20 条 + 「...还有 N 条」
 *   - 空列表：「暂无记忆」
 *   - 失败：error message
 * - memory_write：
 *   - action=created：新建 badge
 *   - action=updated：更新 badge
 *   - 失败：error message
 *
 * 兼容性：
 *   - result.content 为 string（JSON）时正确解析
 */
import React from 'react';
import { describe, it, expect, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import { MemoryRenderer } from '../MemoryRenderer';
import type { ToolCall, ToolResult } from '@/types/tool';

afterEach(() => {
  cleanup();
});

const makeCall = (name: string, args: Record<string, unknown> = {}): ToolCall => ({
  id: 'call-1',
  name,
  arguments: args,
});

const makeResult = (
  content: unknown,
  success = true,
  error?: string
): ToolResult => ({
  id: 'result-1',
  name: 'memory_read',
  success,
  content_type: 'json',
  content,
  attachments: [],
  ...(error !== undefined ? { error } : {}),
});

describe('MemoryRenderer — memory_read', () => {
  it('渲染工具名 badge "memory_read"', () => {
    render(<MemoryRenderer call={makeCall('memory_read')} pending />);
    // 至少出现一次 memory_read
    expect(screen.getAllByText('memory_read').length).toBeGreaterThanOrEqual(1);
  });

  it('pending 且无 result 时显示「正在读取记忆...」', () => {
    render(<MemoryRenderer call={makeCall('memory_read')} pending />);
    expect(screen.getByText('正在读取记忆...')).toBeTruthy();
  });

  it('单条记录：显示 key + value JSON + summary + updated_at', () => {
    const value = { preference: 'dark mode', language: 'zh-CN' };
    render(
      <MemoryRenderer
        call={makeCall('memory_read', { key: 'user_preferences' })}
        result={makeResult({
          key: 'user_preferences',
          value,
          summary: '用户偏好设置',
          updated_at: '2026-08-29T10:30:00Z',
        })}
      />
    );

    // key 渲染
    expect(screen.getByText('user_preferences')).toBeTruthy();
    // summary 渲染
    expect(screen.getByText(/用户偏好设置/)).toBeTruthy();
    // updated_at 渲染
    expect(screen.getByText(/2026-08-29T10:30:00Z/)).toBeTruthy();
    // value JSON 序列化后展示
    expect(screen.getByText(/"preference"/)).toBeTruthy();
    expect(screen.getByText(/"dark mode"/)).toBeTruthy();
  });

  it('单条未找到（value=null）：显示「未找到该记忆条目」', () => {
    render(
      <MemoryRenderer
        call={makeCall('memory_read', { key: 'nonexistent_key' })}
        result={makeResult({
          key: 'nonexistent_key',
          value: null,
          summary: null,
          updated_at: null,
        })}
      />
    );

    expect(screen.getByText(/未找到该记忆条目/)).toBeTruthy();
    expect(screen.getByText(/nonexistent_key/)).toBeTruthy();
  });

  it('列表：显示「共 N 条记忆」+ 列表项', () => {
    const records = [
      { key: 'pref_a', value: { x: 1 }, summary: '摘要 A', updated_at: '2026-08-29T10:00:00Z' },
      { key: 'pref_b', value: { y: 2 }, summary: '摘要 B', updated_at: '2026-08-29T11:00:00Z' },
      { key: 'pref_c', value: { z: 3 }, summary: null, updated_at: '2026-08-29T12:00:00Z' },
    ];
    render(
      <MemoryRenderer
        call={makeCall('memory_read')}
        result={makeResult({ records, count: 3 })}
      />
    );

    expect(screen.getByText('共 3 条记忆')).toBeTruthy();
    // 三条 key 全部渲染
    expect(screen.getByText('pref_a')).toBeTruthy();
    expect(screen.getByText('pref_b')).toBeTruthy();
    expect(screen.getByText('pref_c')).toBeTruthy();
    // summary 渲染（除 null 外）
    expect(screen.getByText('摘要 A')).toBeTruthy();
    expect(screen.getByText('摘要 B')).toBeTruthy();
  });

  it('列表 >20 条时只显示前 20 条 + 「...还有 N 条」', () => {
    const records = Array.from({ length: 25 }, (_, i) => ({
      key: `key_${i}`,
      value: {},
      summary: null,
      updated_at: null,
    }));
    const { container } = render(
      <MemoryRenderer
        call={makeCall('memory_read')}
        result={makeResult({ records, count: 25 })}
      />
    );

    expect(screen.getByText('共 25 条记忆')).toBeTruthy();
    expect(screen.getByText('...还有 5 条')).toBeTruthy();

    // 只渲染 20 条 <li>
    const items = container.querySelectorAll('ul > li');
    expect(items.length).toBe(20);
    // 前 20 个 key 渲染
    expect(screen.getByText('key_0')).toBeTruthy();
    expect(screen.getByText('key_19')).toBeTruthy();
    // 第 21 个 key 不应渲染
    expect(screen.queryByText('key_20')).toBeNull();
  });

  it('空列表：显示「暂无记忆」', () => {
    render(
      <MemoryRenderer
        call={makeCall('memory_read')}
        result={makeResult({ records: [], count: 0 })}
      />
    );

    expect(screen.getByText('暂无记忆')).toBeTruthy();
  });

  it('失败：显示 error 信息', () => {
    render(
      <MemoryRenderer
        call={makeCall('memory_read', { key: 'k' })}
        result={makeResult('', false, '数据库连接不可用')}
      />
    );

    expect(screen.getByText(/读取失败/)).toBeTruthy();
    expect(screen.getByText(/数据库连接不可用/)).toBeTruthy();
  });
});

describe('MemoryRenderer — memory_write', () => {
  it('action=created：显示「新建」badge + key', () => {
    render(
      <MemoryRenderer
        call={makeCall('memory_write', { key: 'new_pref', value: { a: 1 } })}
        result={makeResult({ action: 'created', key: 'new_pref' })}
      />
    );

    // 工具名 badge
    expect(screen.getAllByText('memory_write').length).toBeGreaterThanOrEqual(1);
    // action 中文标签
    expect(screen.getByText('新建')).toBeTruthy();
    // key 渲染
    expect(screen.getByText('new_pref')).toBeTruthy();
  });

  it('action=updated：显示「更新」badge + key', () => {
    render(
      <MemoryRenderer
        call={makeCall('memory_write', { key: 'existing_pref', value: { a: 2 } })}
        result={makeResult({ action: 'updated', key: 'existing_pref' })}
      />
    );

    expect(screen.getByText('更新')).toBeTruthy();
    expect(screen.getByText('existing_pref')).toBeTruthy();
  });

  it('失败：显示 error 信息', () => {
    render(
      <MemoryRenderer
        call={makeCall('memory_write', { key: 'k', value: {} })}
        result={makeResult('', false, '记忆条目已达上限（100 条）')}
      />
    );

    expect(screen.getByText(/写入失败/)).toBeTruthy();
    expect(screen.getByText(/记忆条目已达上限/)).toBeTruthy();
  });
});

describe('MemoryRenderer — 兼容性', () => {
  it('result.content 为字符串（JSON）时正确解析', () => {
    const content = JSON.stringify({
      records: [{ key: 'k1', value: { x: 1 }, summary: null, updated_at: null }],
      count: 1,
    });
    render(
      <MemoryRenderer
        call={makeCall('memory_read')}
        result={makeResult(content)}
      />
    );

    expect(screen.getByText('共 1 条记忆')).toBeTruthy();
    expect(screen.getByText('k1')).toBeTruthy();
  });

  it('非法 JSON 字符串降级为空内容，不抛错', () => {
    // memory_read 列表模式 + 非法 JSON
    const invalidJson = '{not valid json';
    render(
      <MemoryRenderer
        call={makeCall('memory_read')}
        result={makeResult(invalidJson)}
      />
    );

    // 不抛错，组件正常渲染（具体降级文本视实现而定）
    expect(screen.getByText('memory_read')).toBeTruthy();
  });
});
