/**
 * MemoryViewer 单元测试
 *
 * Phase 3-Plan-1B / Task 7
 * 覆盖：
 *  - 初始加载后渲染记忆列表
 *  - 搜索按钮触发 search API
 *  - 搜索框回车触发搜索
 *  - 重置按钮恢复列表
 *  - 删除按钮触发 confirm + 删除 API
 *  - 空状态「暂无记忆」展示
 *  - 错误状态展示
 *  - 向量化状态标签
 */
import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react';
import { MemoryViewer } from '../MemoryViewer';

// Mock harnessMemoriesApi
vi.mock('../../../api/harnessMemoriesApi', () => ({
  harnessMemoriesApi: {
    list: vi.fn(),
    delete: vi.fn(),
    search: vi.fn(),
  },
}));

import { harnessMemoriesApi } from '../../../api/harnessMemoriesApi';

const mockList = harnessMemoriesApi.list as unknown as ReturnType<typeof vi.fn>;
const mockDelete = harnessMemoriesApi.delete as unknown as ReturnType<typeof vi.fn>;
const mockSearch = harnessMemoriesApi.search as unknown as ReturnType<typeof vi.fn>;

beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(() => {
  cleanup();
});

describe('MemoryViewer', () => {
  it('初始加载后渲染记忆列表', async () => {
    mockList.mockResolvedValueOnce({
      records: [
        {
          key: 'user_pref_lang',
          value: { text: '中文' },
          importance: 0.8,
          access_count: 3,
          summary: '用户偏好语言',
          has_embedding: true,
        },
        {
          key: 'user_name',
          value: { text: '小明' },
          importance: 0.9,
          access_count: 0,
          summary: null,
          has_embedding: false,
        },
      ],
      count: 2,
    });

    render(<MemoryViewer agentId="test-agent-1" />);

    await waitFor(() => {
      expect(screen.getByText('user_pref_lang')).toBeTruthy();
    });

    expect(screen.getByText('user_name')).toBeTruthy();
    expect(screen.getByText('重要度: 0.80')).toBeTruthy();
    expect(screen.getByText('访问 3 次')).toBeTruthy();
    expect(screen.getByText('✅ 已向量化')).toBeTruthy();
    expect(screen.getByText('⏳ 待向量化')).toBeTruthy();
    expect(mockList).toHaveBeenCalledWith('test-agent-1');
  });

  it('列表为空时展示「暂无记忆」', async () => {
    mockList.mockResolvedValueOnce({ records: [], count: 0 });

    render(<MemoryViewer agentId="agent-empty" />);

    await waitFor(() => {
      expect(screen.getByText('暂无记忆')).toBeTruthy();
    });
  });

  it('加载失败时展示错误信息', async () => {
    mockList.mockRejectedValueOnce(new Error('网络错误'));

    render(<MemoryViewer agentId="agent-fail" />);

    await waitFor(() => {
      expect(screen.getByText('网络错误')).toBeTruthy();
    });
  });

  it('搜索按钮触发 search API', async () => {
    mockList.mockResolvedValueOnce({ records: [], count: 0 });
    mockSearch.mockResolvedValueOnce({
      records: [
        {
          key: 'searched_key',
          value: { text: '搜索结果' },
          score: 0.85,
          summary: null,
        },
      ],
      count: 1,
    });

    render(<MemoryViewer agentId="agent-search" />);

    await waitFor(() => {
      expect(screen.getByText('暂无记忆')).toBeTruthy();
    });

    const input = screen.getByPlaceholderText(/搜索记忆/);
    fireEvent.change(input, { target: { value: '测试查询' } });

    const searchBtn = screen.getByRole('button', { name: '搜索' });
    fireEvent.click(searchBtn);

    await waitFor(() => {
      expect(mockSearch).toHaveBeenCalledWith('agent-search', '测试查询');
    });

    await waitFor(() => {
      expect(screen.getByText('searched_key')).toBeTruthy();
    });
  });

  it('搜索框回车触发搜索', async () => {
    mockList.mockResolvedValueOnce({ records: [], count: 0 });
    mockSearch.mockResolvedValueOnce({ records: [], count: 0 });

    render(<MemoryViewer agentId="agent-enter" />);

    await waitFor(() => {
      expect(screen.getByText('暂无记忆')).toBeTruthy();
    });

    const input = screen.getByPlaceholderText(/搜索记忆/);
    fireEvent.change(input, { target: { value: '回车查询' } });
    fireEvent.keyDown(input, { key: 'Enter' });

    await waitFor(() => {
      expect(mockSearch).toHaveBeenCalledWith('agent-enter', '回车查询');
    });
  });

  it('重置按钮恢复完整列表', async () => {
    mockList.mockResolvedValueOnce({
      records: [
        { key: 'original', value: {}, importance: 0.5, access_count: 0, has_embedding: true },
      ],
      count: 1,
    });
    mockSearch.mockResolvedValueOnce({ records: [], count: 0 });
    // 重置后再次调用 list
    mockList.mockResolvedValueOnce({
      records: [
        { key: 'original', value: {}, importance: 0.5, access_count: 0, has_embedding: true },
      ],
      count: 1,
    });

    render(<MemoryViewer agentId="agent-reset" />);

    await waitFor(() => {
      expect(screen.getByText('original')).toBeTruthy();
    });

    // 搜索
    const input = screen.getByPlaceholderText(/搜索记忆/);
    fireEvent.change(input, { target: { value: 'query' } });
    fireEvent.click(screen.getByRole('button', { name: '搜索' }));

    await waitFor(() => {
      expect(mockSearch).toHaveBeenCalled();
    });

    // 重置
    const resetBtn = screen.getByRole('button', { name: '重置' });
    fireEvent.click(resetBtn);

    await waitFor(() => {
      expect(mockList).toHaveBeenCalledTimes(2); // 初始加载 + 重置后
    });
  });

  it('删除按钮触发 confirm 并调用删除 API', async () => {
    mockList.mockResolvedValueOnce({
      records: [
        {
          key: 'to_delete',
          value: { text: '待删除' },
          importance: 0.5,
          access_count: 0,
          has_embedding: true,
        },
      ],
      count: 1,
    });
    mockDelete.mockResolvedValueOnce(undefined);

    // 替换 confirm
    const originalConfirm = window.confirm;
    window.confirm = vi.fn(() => true);

    try {
      render(<MemoryViewer agentId="agent-del" />);

      await waitFor(() => {
        expect(screen.getByText('to_delete')).toBeTruthy();
      });

      const deleteBtn = screen.getByLabelText('删除记忆 to_delete');
      fireEvent.click(deleteBtn);

      await waitFor(() => {
        expect(window.confirm).toHaveBeenCalledWith(
          '确定要删除记忆 "to_delete" 吗？此操作不可恢复。',
        );
      });

      await waitFor(() => {
        expect(mockDelete).toHaveBeenCalledWith('agent-del', 'to_delete');
      });

      // 删除后从列表中移除
      expect(screen.queryByText('to_delete')).toBeNull();
    } finally {
      window.confirm = originalConfirm;
    }
  });

  it('删除时用户取消 confirm 不调用 API', async () => {
    mockList.mockResolvedValueOnce({
      records: [
        {
          key: 'keep_me',
          value: { text: '保留' },
          importance: 0.5,
          access_count: 0,
          has_embedding: true,
        },
      ],
      count: 1,
    });

    const originalConfirm = window.confirm;
    window.confirm = vi.fn(() => false);

    try {
      render(<MemoryViewer agentId="agent-keep" />);

      await waitFor(() => {
        expect(screen.getByText('keep_me')).toBeTruthy();
      });

      const deleteBtn = screen.getByLabelText('删除记忆 keep_me');
      fireEvent.click(deleteBtn);

      // 取消后不调用 delete API
      expect(mockDelete).not.toHaveBeenCalled();
      // 条目仍在
      expect(screen.getByText('keep_me')).toBeTruthy();
    } finally {
      window.confirm = originalConfirm;
    }
  });

  it('value 为对象时 JSON 序列化显示', async () => {
    mockList.mockResolvedValueOnce({
      records: [
        {
          key: 'complex_value',
          value: { lang: 'zh', level: 5 },
          importance: 0.5,
          access_count: 0,
          has_embedding: true,
        },
      ],
      count: 1,
    });

    render(<MemoryViewer agentId="agent-json" />);

    await waitFor(() => {
      expect(screen.getByText('complex_value')).toBeTruthy();
    });

    // JSON 序列化后的文本应包含字段
    const text = screen.getByText(/"lang"/).textContent;
    expect(text).toContain('"zh"');
    expect(text).toContain('"level"');
  });

  it('summary 存在时渲染为斜体文本', async () => {
    mockList.mockResolvedValueOnce({
      records: [
        {
          key: 'with_summary',
          value: { text: 'v' },
          importance: 0.5,
          access_count: 0,
          summary: '这是摘要',
          has_embedding: true,
        },
      ],
      count: 1,
    });

    render(<MemoryViewer agentId="agent-summary" />);

    await waitFor(() => {
      expect(screen.getByText('这是摘要')).toBeTruthy();
    });
  });

  it('agentId 变化时重新加载', async () => {
    mockList.mockResolvedValueOnce({ records: [{ key: 'a1_key', value: {}, importance: 0.5, access_count: 0, has_embedding: true }], count: 1 });
    mockList.mockResolvedValueOnce({ records: [{ key: 'a2_key', value: {}, importance: 0.5, access_count: 0, has_embedding: true }], count: 1 });

    const { rerender } = render(<MemoryViewer agentId="agent-a1" />);

    await waitFor(() => {
      expect(screen.getByText('a1_key')).toBeTruthy();
    });

    rerender(<MemoryViewer agentId="agent-a2" />);

    await waitFor(() => {
      expect(screen.getByText('a2_key')).toBeTruthy();
    });

    expect(mockList).toHaveBeenCalledTimes(2);
  });
});
