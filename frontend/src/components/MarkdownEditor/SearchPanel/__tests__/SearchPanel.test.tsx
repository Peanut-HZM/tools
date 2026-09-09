/**
 * SearchPanel 搜索结果高亮测试
 *
 * 验证：
 * - 文件名搜索结果中匹配文本被 <mark> 包裹
 * - 内容搜索结果中匹配文本被 <mark> 包裹
 * - 匹配计数、文件路径等信息正确显示
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup, waitFor } from '@testing-library/react';
import SearchPanel from '../SearchPanel';

/* Mock 搜索 API */
vi.mock('../../../../api/markdownEditorApi', () => ({
  searchFiles: vi.fn(),
  searchContent: vi.fn(),
}));

// 延迟 import 以便 mock 生效
import * as markdownEditorApi from '../../../../api/markdownEditorApi';

describe('SearchPanel 搜索结果高亮', () => {
  const mockOnClose = vi.fn();
  const mockOnFileSelect = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  it('文件名搜索结果中高亮匹配的文件名', async () => {
    vi.mocked(markdownEditorApi.searchFiles).mockResolvedValue([
      { name: 'README.md', path: '/docs/README.md', match: 'README' },
      { name: 'readme.txt', path: '/docs/readme.txt', match: 'readme' },
    ]);

    render(<SearchPanel onClose={mockOnClose} onFileSelect={mockOnFileSelect} />);

    // 输入查询
    const input = screen.getByPlaceholderText('输入文件名...');
    fireEvent.change(input, { target: { value: 'readme' } });

    // 点击搜索按钮
    const searchBtn = screen.getByRole('button', { name: /搜索/ });
    fireEvent.click(searchBtn);

    // 等待结果渲染并检查高亮
    await waitFor(() => {
      expect(markdownEditorApi.searchFiles).toHaveBeenCalledWith('readme');
    });

    // 查找所有 <mark> 标签
    const marks = screen.getAllByText(/readme/i);
    // 应该找到高亮后的结果
    expect(marks.length).toBeGreaterThan(0);

    // 验证至少有一个 <mark> 元素
    const markElements = document.querySelectorAll('mark.search-highlight');
    expect(markElements.length).toBeGreaterThan(0);
  });

  it('内容搜索结果中高亮匹配的文本内容', async () => {
    vi.mocked(markdownEditorApi.searchContent).mockResolvedValue([
      {
        file: 'query.sql',
        matches: [
          { line: 1, content: 'SELECT * FROM users', column: 15 },
          { line: 5, content: 'WHERE users.id = 1', column: 7 },
        ],
      },
    ]);

    render(<SearchPanel onClose={mockOnClose} onFileSelect={mockOnFileSelect} />);

    // 切换到内容搜索
    const contentTab = screen.getByRole('button', { name: '内容' });
    fireEvent.click(contentTab);

    // 输入查询
    const input = screen.getByPlaceholderText('输入搜索内容...');
    fireEvent.change(input, { target: { value: 'users' } });

    // 点击搜索按钮
    const searchBtn = screen.getByRole('button', { name: /搜索/ });
    fireEvent.click(searchBtn);

    // 等待结果渲染
    await waitFor(() => {
      expect(markdownEditorApi.searchContent).toHaveBeenCalledWith('users', false, false);
    });

    // 验证有高亮元素
    const markElements = document.querySelectorAll('mark.search-highlight');
    expect(markElements.length).toBeGreaterThan(0);

    // 验证高亮内容是 'users'
    const markContents = Array.from(markElements).map((el) => el.textContent);
    expect(markContents).toContain('users');
  });

  it('搜索结果中匹配数量正确显示', async () => {
    vi.mocked(markdownEditorApi.searchContent).mockResolvedValue([
      {
        file: 'test.py',
        matches: [
          { line: 1, content: 'def hello():', column: 5 },
          { line: 5, content: 'hello()', column: 1 },
          { line: 10, content: 'hello_world()', column: 1 },
        ],
      },
    ]);

    render(<SearchPanel onClose={mockOnClose} onFileSelect={mockOnFileSelect} />);

    const contentTab = screen.getByRole('button', { name: '内容' });
    fireEvent.click(contentTab);

    const input = screen.getByPlaceholderText('输入搜索内容...');
    fireEvent.change(input, { target: { value: 'hello' } });

    const searchBtn = screen.getByRole('button', { name: /搜索/ });
    fireEvent.click(searchBtn);

    await waitFor(() => {
      expect(screen.getByText('3 个匹配')).toBeTruthy();
    });
  });
});
